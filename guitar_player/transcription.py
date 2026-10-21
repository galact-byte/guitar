"""Local decoder and strict CUDA model interface. Heavy imports stay in the worker."""
from pathlib import Path
import subprocess
import time
import wave
from .contracts import Transcription
from .runtime import MODEL_BYTES, MODEL_SHA256, ffmpeg_path
from .storage import sha256

MAX_SECONDS = 20 * 60
MAX_BYTES = 512 * 1024 * 1024


def verify_model(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size != MODEL_BYTES or sha256(path) != MODEL_SHA256:
        raise ValueError('模型缺失或校验失败，请在环境准备中选择已验证的官方模型；不会自动下载')


def decode_audio(source, output, ffmpeg=None):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output:
        raise ValueError('不能覆盖原歌曲')
    if not source.is_file() or not 0 < source.stat().st_size <= MAX_BYTES:
        raise ValueError('歌曲为空、不存在或超过512MiB')
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [ffmpeg or ffmpeg_path(), '-nostdin', '-v', 'error', '-xerror', '-i', str(source), '-map', '0:a:0', '-vn', '-t', str(MAX_SECONDS+1), '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', '-n', str(output)]
    result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, timeout=180, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise ValueError('音频无法解码：' + result.stderr.decode('utf-8', errors='replace')[-1500:])
    try:
        with wave.open(str(output), 'rb') as stream:
            duration = stream.getnframes()/stream.getframerate()
    except (wave.Error, EOFError) as exc:
        raise ValueError('解码输出不是有效音频') from exc
    if not 0 < duration <= MAX_SECONDS:
        raise ValueError('歌曲时长须在0–20分钟内')
    return duration


def transcribe(source, directory, model_path, progress=lambda message: None):
    import numpy as np
    import soundfile as sf
    import torch
    from piano_transcription_inference import PianoTranscription
    from piano_transcription_inference.models import Note_pedal
    from piano_transcription_inference import config

    directory = Path(directory)
    verify_model(model_path)
    if not torch.cuda.is_available():
        raise ValueError('CUDA GPU不可用；未回退CPU，请检查原有GPU环境')
    before = sha256(source)
    mtime = Path(source).stat().st_mtime_ns
    progress('正在本地解码歌曲（上限20分钟/512MiB）…')
    duration = decode_audio(source, directory/'decoded.wav')
    audio, rate = sf.read(directory/'decoded.wav', dtype='float32')
    if rate != 16000 or audio.ndim != 1 or not np.isfinite(audio).all():
        raise ValueError('解码结果包含无效采样')
    progress('正在校验并加载GPU模型…')
    torch.set_num_threads(4)
    torch.cuda.reset_peak_memory_stats()
    init_time = time.perf_counter()
    # Configure the upstream inference engine without its implicit download/eval/strict=False loader.
    engine = PianoTranscription.__new__(PianoTranscription)
    engine.segment_samples = 16000*10
    engine.frames_per_second, engine.classes_num = config.frames_per_second, config.classes_num
    engine.onset_threshold, engine.offset_threshod = .3, .3
    engine.frame_threshold, engine.pedal_offset_threshold = .1, .2
    model = Note_pedal(frames_per_second=config.frames_per_second, classes_num=config.classes_num)
    checkpoint = torch.load(model_path, map_location='cpu', weights_only=True)
    model.load_state_dict(checkpoint['model'], strict=True)
    del checkpoint
    model.to('cuda')
    engine.model = torch.nn.DataParallel(model)
    if not all(p.is_cuda for p in engine.model.parameters()):
        raise ValueError('模型未全部运行在CUDA上，停止处理')
    torch.cuda.synchronize()
    initialization_seconds = time.perf_counter()-init_time
    progress('正在GPU识别整首歌曲；可随时取消…')
    started = time.perf_counter()
    raw = engine.transcribe(audio, str(directory/'raw.mid'))
    torch.cuda.synchronize()
    seconds = time.perf_counter()-started
    if any(not np.isfinite(a).all() for a in raw['output_dict'].values()):
        raise ValueError('模型输出含NaN/无限值')
    result = Transcription.from_model(duration, raw['est_note_events'], raw['est_pedal_events'], {'source_sha256': before, 'model_sha256': MODEL_SHA256, 'engine': 'piano-transcription-inference-0.0.6', 'device': 'cuda', 'gpu': torch.cuda.get_device_name(), 'torch': str(torch.__version__), 'initialization_seconds': initialization_seconds, 'inference_seconds': seconds, 'peak_cuda_allocated_bytes': int(torch.cuda.max_memory_allocated()), 'strict_weights': True, 'source_is_piano_specialist_model': True})
    if not result.notes:
        raise ValueError('没有识别出可演奏音符，请选择其他歌曲')
    if before != sha256(source) or Path(source).stat().st_mtime_ns != mtime:
        raise ValueError('原文件在处理期间改变，请重新导入')
    return result
