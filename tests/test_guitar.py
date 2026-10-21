import unittest
from guitar_player.arrangement import guitar_plan
from guitar_player.contracts import Note, Transcription
from guitar_player.profiles import Calibration, Chord, GuitarProfile


def fixture():
    # Fictitious test slots, not real game chord labels or calibrated timing.
    return GuitarProfile(tuple(Chord(f'fixture-{p}-{s}', (48+p*3+s%3, 60+p*3+s%3), p, s) for p in range(4) for s in range(6)),
                         Calibration(800, 600, ((.1,.1),)*12), True, .2, .05, .03)


class GuitarTests(unittest.TestCase):
    def test_four_pages_are_reachable_with_checked_intermediate_pages(self):
        profile = fixture()
        source = Transcription(5., (Note(1.,1.2,60,80), Note(3.,3.2,69,80)), (), {})
        plan = guitar_plan(source, profile)
        checks = [a.value for a in plan.actions if a.kind == 'verify_page']
        self.assertIn(3, checks)
        self.assertEqual(sum(a.kind == 'down' and a.value == 'T' for a in plan.actions), 3)
        self.assertTrue(all(0 <= a.value < 8 for a in plan.actions if a.kind == 'move'))
        self.assertNotEqual(plan.notes, source.notes)
        self.assertTrue(plan.report['approximated'])

    def test_required_setup_cannot_overlap_previous_strum(self):
        source = Transcription(2., (Note(.1,.2,60,80),Note(.11,.2,69,80)), (), {})
        with self.assertRaisesRegex(ValueError, '准备|过密'):
            guitar_plan(source, fixture())

    def test_missing_pages_never_become_verified_by_guessing(self):
        with self.assertRaises(ValueError):
            guitar_plan(Transcription(1.,(Note(0.,.5,60,80),),(),{}), GuitarProfile((), Calibration(800,600,())))


if __name__ == '__main__': unittest.main()
