from pathlib import Path
import shutil
from .storage import DATA, ROOT, read_json

MODEL_SHA256 = 'c3fa9730725bf4a762f1c14bc80cd5986eacda01b026f5a4a2525cd607876141'
MODEL_BYTES = 171966578


def settings():
    path = DATA / 'runtime.json'
    value = read_json(path) if path.exists() else {}
    if not isinstance(value, dict):
        raise ValueError('本地环境配置损坏，请打开环境设置重新选择')
    return value


def ffmpeg_path():
    configured = settings().get('ffmpeg')
    found = configured or shutil.which('ffmpeg')
    if not found:
        raise OSError('找不到FFmpeg，请在环境准备中选择现有ffmpeg.exe')
    return str(found)


def model_path():
    configured = settings().get('model')
    if configured:
        return Path(configured)
    local = ROOT / '.trellis/tasks/10-21-guitar-player-research/research/audio-sample/classic-piano-checkpoint.pth'
    return local if local.is_file() else DATA / 'assets' / 'piano.pth'


def soundfont_path():
    configured = settings().get('soundfont')
    if configured:
        return Path(configured)
    local = ROOT / '.venv-transcription/Lib/site-packages/pretty_midi/TimGM6mb.sf2'
    return local if local.is_file() else DATA / 'assets' / 'reference.sf2'


def worker_python(kind):
    configured = settings().get('preview_python' if kind == 'preview' else 'model_python')
    env = '.venv-transcription' if kind == 'preview' else '.venv-piano-probe'
    candidate = Path(configured) if configured else ROOT / env / 'Scripts' / 'python.exe'
    if not candidate.is_file():
        name = '试听' if kind == 'preview' else 'GPU模型'
        raise OSError(f'{name}环境未配置：{candidate}；请在环境设置中选择已有Python，不会自动安装或替换环境')
    return str(candidate)
