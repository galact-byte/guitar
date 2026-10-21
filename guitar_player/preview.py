"""离线采样试听；使用模型事件，不混入原音频，不访问音频设备。"""
from array import array
from collections import defaultdict
import math
import os
from pathlib import Path
import tempfile
import wave
from .contracts import Plan, Transcription
from .runtime import soundfont_path

SAMPLE_RATE = 22050


def render_plan(transcription, output, plan=None, *, soundfont=None, synth_factory=None):
    output = Path(output)
    if output.exists():
        raise ValueError('试听文件已存在，拒绝覆盖')
    font = Path(soundfont) if soundfont is not None else soundfont_path()
    if not font.is_file():
        raise ValueError('缺少采样音色，请在环境设置中选择现有SF2文件；不会改用电子合成音')
    if synth_factory is None:
        import tinysoundfont
        synth_factory = tinysoundfont.Synth
    notes = plan.notes if plan is not None else transcription.notes
    controls = () if plan is not None else transcription.controls
    seconds = plan.duration if plan is not None else transcription.duration
    program = 24 if plan is not None and plan.mode == 'guitar' else 0
    frames = round(seconds * SAMPLE_RATE)
    by_pitch, events = defaultdict(list), []
    for note in notes:
        by_pitch[note.pitch].append(note)
        events.extend(((round(note.start*SAMPLE_RATE), 1, note.pitch, note.velocity),
                       (round(note.end*SAMPLE_RATE), 0, note.pitch, 0)))
    for group in by_pitch.values():
        group.sort(key=lambda note: note.start)
        if any(b.start < a.end for a, b in zip(group, group[1:])):
            raise ValueError('同音高重叠尚未分配独立声部，不能静默提前松键')
    events.extend((round(c.time*SAMPLE_RATE), -1, 64, c.value) for c in controls)
    synth = synth_factory(samplerate=SAMPLE_RATE)
    sfid = synth.sfload(str(font))
    samples = array('f')
    cursor, pedal = 0, False
    pressed, deferred = set(), set()
    def generate(count):
        while count:
            size = min(count, 22050)
            stereo = array('f')
            stereo.frombytes(synth.generate_simple(size))
            samples.extend((stereo[i]+stereo[i+1])*.5 for i in range(0, len(stereo), 2))
            count -= size
    try:
        synth.program_select(0, sfid, 0, program)
        for position, kind, pitch, velocity in sorted(events):
            if position > cursor:
                generate(position-cursor)
                cursor = position
            if kind == -1:
                pedal = velocity >= 64
                if not pedal:
                    for key in sorted(deferred - pressed):
                        synth.noteoff(0, key)
                    deferred.clear()
            elif kind == 1:
                if not synth.noteon(0, pitch, velocity):
                    raise RuntimeError('采样器拒绝音符')
                pressed.add(pitch)
                deferred.discard(pitch)
            else:
                pressed.discard(pitch)
                if pedal:
                    deferred.add(pitch)
                else:
                    synth.noteoff(0, pitch)
        if cursor < frames:
            generate(frames-cursor)
    finally:
        synth.sfunload(sfid)
    if len(samples) != frames or any(not math.isfinite(x) for x in samples):
        raise ValueError('采样合成长度或数值异常')
    peak = max(map(abs, samples), default=0.)
    gain = min(4.0094, 10**(-1/20)/peak) if peak else 1.
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(suffix='.wav', dir=output.parent)
    os.close(fd)
    try:
        with wave.open(temporary, 'wb') as stream:
            stream.setparams((1, 2, SAMPLE_RATE, 0, 'NONE', 'not compressed'))
            for start in range(0, frames, SAMPLE_RATE):
                pcm = array('h', (max(-32768, min(32767, round(x*gain*32767))) for x in samples[start:start+SAMPLE_RATE]))
                stream.writeframes(pcm.tobytes())
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    return output


def render_request(request, workdir, progress=lambda message: None):
    transcription = Transcription.from_dict(request['transcription'])
    plan = Plan.from_dict(request['plan']) if request.get('plan') else None
    output = Path(workdir) / 'preview.wav'
    progress('生成本地采样试听（不是游戏实音）…')
    render_plan(transcription, output, plan, soundfont=request.get('soundfont'))
    return {'preview': str(output), 'duration': plan.duration if plan else transcription.duration,
            'reference_audio': True, 'adapted': plan is not None, 'source_audio_mixed': False}
