from dataclasses import asdict, dataclass
import math


def number(value, name, minimum=0.):
    if type(value) not in (float, int) or not math.isfinite(value) or value < minimum:
        raise ValueError(f'{name}必须为有效数字')


@dataclass(frozen=True)
class Note:
    start: float
    end: float
    pitch: int
    velocity: int

    def __post_init__(self):
        number(self.start, '起音')
        number(self.end, '尾音')
        if self.end <= self.start or type(self.pitch) is not int or not 0 <= self.pitch <= 127 or type(self.velocity) is not int or not 1 <= self.velocity <= 127:
            raise ValueError('无效音符时间、音高或力度')


@dataclass(frozen=True)
class Control:
    time: float
    number: int
    value: int

    def __post_init__(self):
        number(self.time, '控制时间')
        if type(self.number) is not int or self.number != 64 or type(self.value) is not int or not 0 <= self.value <= 127:
            raise ValueError('只支持有效二值CC64踏板控制')


@dataclass(frozen=True)
class Transcription:
    duration: float
    notes: tuple
    controls: tuple
    diagnostics: dict

    def __post_init__(self):
        number(self.duration, '时长', .000001)
        if any(not isinstance(n, Note) or n.end > self.duration for n in self.notes):
            raise ValueError('音符超出歌曲时长')
        if any(not isinstance(c, Control) or c.time > self.duration for c in self.controls):
            raise ValueError('控制超出歌曲时长')

    def to_dict(self):
        return {'schema': 1, 'duration': self.duration, 'notes': [asdict(n) for n in self.notes], 'controls': [asdict(c) for c in self.controls], 'diagnostics': self.diagnostics}

    @classmethod
    def from_dict(cls, value):
        if value.get('schema') != 1:
            raise ValueError('转谱缓存版本不受支持，请重新处理')
        return cls(value['duration'], tuple(Note(**n) for n in value['notes']), tuple(Control(**c) for c in value['controls']), value['diagnostics'])

    @classmethod
    def from_model(cls, duration, notes, pedals, diagnostics):
        result, controls, removed, clipped = [], [], 0, 0
        for item in notes:
            start, end = float(item['onset_time']), float(item['offset_time'])
            note = Note(start, end, int(item['midi_note']), int(item['velocity']))
            if start >= duration:
                removed += 1
                continue
            clipped += end > duration
            result.append(Note(start, min(end, duration), note.pitch, note.velocity))
        for item in pedals:
            start, end = float(item['onset_time']), float(item['offset_time'])
            number(start, '踏板起点')
            number(end, '踏板终点')
            if start >= end:
                raise ValueError('无效踏板区间')
            if start < duration:
                controls.extend((Control(start, 64, 127), Control(min(end, duration), 64, 0)))
        return cls(float(duration), tuple(result), tuple(sorted(controls, key=lambda c: c.time)), {**diagnostics, 'padding_notes_removed': removed, 'tail_notes_clipped': clipped})


@dataclass(frozen=True)
class Action:
    time: float
    kind: str
    value: object

    def __post_init__(self):
        number(self.time, '动作时间')
        if self.kind not in ('up', 'down', 'move', 'mouse_down', 'mouse_up', 'verify_page'):
            raise ValueError('未知动作')


@dataclass(frozen=True)
class Plan:
    duration: float
    mode: str
    actions: tuple
    notes: tuple
    report: dict

    def __post_init__(self):
        number(self.duration, '计划时长', .000001)
        if self.mode not in ('keyboard', 'guitar') or not self.actions:
            raise ValueError('计划为空或模式不支持')
        if any(a.time > self.duration for a in self.actions) or any(a.time > b.time for a, b in zip(self.actions, self.actions[1:])):
            raise ValueError('计划时间无效')

    def to_dict(self):
        return {'schema': 1, 'duration': self.duration, 'mode': self.mode, 'actions': [asdict(a) for a in self.actions], 'notes': [asdict(n) for n in self.notes], 'report': self.report}

    @classmethod
    def from_dict(cls, value):
        if value.get('schema') != 1:
            raise ValueError('计划版本不支持')
        return cls(value['duration'], value['mode'], tuple(Action(**a) for a in value['actions']), tuple(Note(**n) for n in value['notes']), value['report'])
