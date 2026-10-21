from dataclasses import dataclass
from .contracts import number

KEYBOARD_KEYS = tuple("A S D F G H J K L ; ' ENTER Q W E R T Y U I O P [ ] 1 2 3 4 5 6 7 8 9 0 - =".split())
KEYBOARD_VERSION = 'nte-e3-36-v1-unverified'
KNOWN_CHORDS = ('G', 'Am', 'Bm', 'C', 'D', 'Em')


@dataclass(frozen=True)
class Calibration:
    width: int
    height: int
    points: tuple

    def __post_init__(self):
        if type(self.width) is not int or type(self.height) is not int or min(self.width, self.height) <= 0:
            raise ValueError('无效客户区大小')
        for x, y in self.points:
            number(x, '横坐标')
            number(y, '纵坐标')
            if x > 1 or y > 1:
                raise ValueError('坐标超出客户区')

    def screen_point(self, index, rect):
        left, top, width, height = rect
        if (width, height) != (self.width, self.height):
            raise ValueError('客户区大小已改变，请重新校准')
        x, y = self.points[index]
        return left + round(x * (width-1)), top + round(y * (height-1))


@dataclass(frozen=True)
class Chord:
    name: str
    pitches: tuple
    page: int
    slot: int

    def __post_init__(self):
        if not self.name or not 0 <= self.page < 4 or not 0 <= self.slot < 6 or not self.pitches or any(type(p) is not int or not 0 <= p <= 127 for p in self.pitches):
            raise ValueError('无效和弦槽')


@dataclass(frozen=True)
class GuitarProfile:
    chords: tuple
    calibration: Calibration
    verified: bool = False
    page_seconds: float = 0.
    select_seconds: float = 0.
    strum_seconds: float = 0.
    next_key: str = 'T'

    def validate_ready(self):
        if not self.verified or len(self.chords) != 24 or {(c.page, c.slot) for c in self.chords} != {(p, s) for p in range(4) for s in range(6)}:
            raise ValueError('吉他四页24和弦和动作尚未全部验证，暂不能演奏')
        if len(self.calibration.points) < 12 or min(self.page_seconds, self.select_seconds, self.strum_seconds) <= 0 or self.next_key not in ('R', 'T'):
            raise ValueError('分页、选区和扫弦校准不完整')
