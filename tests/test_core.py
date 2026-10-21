import json
import math
from pathlib import Path
import tempfile
import unittest

try:
    from guitar_player.contracts import Note, Control, Transcription, Action, Plan
    from guitar_player.arrangement import keyboard_plan
    from guitar_player.storage import atomic_json, read_json, sha256
    from guitar_player.profiles import KEYBOARD_KEYS, Calibration, GuitarProfile, Chord
except ImportError:
    Note = None


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(Note, 'product contracts and arrangement are not implemented')

    def test_reject_invalid_notes_and_non_native_numbers(self):
        for args in [(0., 1., True, 80), (float('nan'), 1., 60, 80), (1., 0., 60, 80), (0., 1., 128, 80)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                Note(*args)

    def test_normalize_padding_only_at_end_and_keep_attacks(self):
        r = Transcription.from_model(5., [dict(onset_time=4.47, offset_time=6., midi_note=69, velocity=80), dict(onset_time=4.87, offset_time=4.99, midi_note=69, velocity=70), dict(onset_time=5.2, offset_time=6., midi_note=60, velocity=80)], [], {'device': 'cuda'})
        self.assertEqual([(n.start, n.end) for n in r.notes], [(4.47, 5.), (4.87, 4.99)])
        self.assertEqual(r.diagnostics['padding_notes_removed'], 1)
        json.dumps(r.to_dict(), allow_nan=False)

    def test_round_trip_rejects_nan_control_and_bounds(self):
        r = Transcription(2., (Note(0., 1., 60, 80),), (Control(0., 64, 127),), {})
        self.assertEqual(Transcription.from_dict(r.to_dict()), r)
        for control in [(float('nan'), 64, 0), (0., 1, 0), (0., 64, 128)]:
            with self.assertRaises(ValueError):
                Control(*control)
        with self.assertRaises(ValueError):
            Transcription(0.5, r.notes, (), {})

    def test_keyboard_all_36_keys_unique_and_range_edges(self):
        r = Transcription(40., tuple(Note(float(i), float(i)+.2, 52+i, 80) for i in range(36)), (), {})
        p = keyboard_plan(r)
        downs = [a for a in p.actions if a.kind == 'down']
        self.assertEqual(len({a.value for a in downs}), 36)
        self.assertEqual([downs[0].value, downs[11].value, downs[12].value, downs[-1].value], ['A', 'ENTER', 'Q', '='])
        self.assertEqual([n.pitch for n in p.notes], list(range(52, 88)))

    def test_octave_folding_preserves_pitch_class_attacks_and_rests(self):
        r = Transcription(8., (Note(0., 1., 20, 80), Note(4.47, 4.7, 69, 70), Note(4.87, 5.1, 100, 80)), (), {})
        before = r.to_dict()
        p = keyboard_plan(r)
        self.assertEqual([n.start for n in p.notes], [0., 4.47, 4.87])
        self.assertEqual([n.pitch % 12 for n in p.notes], [8, 9, 4])
        self.assertTrue(all(52 <= n.pitch <= 87 for n in p.notes))
        self.assertEqual(before, r.to_dict())
        self.assertTrue(p.report['pitch_changes'])

    def test_same_key_retrigger_never_releases_new_note_at_old_end(self):
        r = Transcription(4., (Note(0., 2., 60, 80), Note(1., 3., 60, 90)), (), {})
        p = keyboard_plan(r)
        self.assertEqual([(round(a.time, 4), a.kind) for a in p.actions], [(0., 'down'), (1., 'up'), (1., 'down'), (3., 'up')])
        self.assertEqual(p.notes[0].end, 1.)
        self.assertTrue(p.report['retriggered'])

    def test_no_notes_rejected_and_polyphony_limit_is_explicit(self):
        with self.assertRaises(ValueError):
            keyboard_plan(Transcription(1., (), (), {}))
        r = Transcription(2., (Note(0., 1., 60, 80), Note(0., 1., 64, 80)), (), {})
        with self.assertRaises(ValueError):
            keyboard_plan(r, max_polyphony=1)
        self.assertEqual(len(keyboard_plan(r).notes), 2)

    def test_atomic_storage_failure_does_not_replace_valid_result(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'中文 空格.json'
            atomic_json(p, {'v': 1})
            with self.assertRaises(ValueError):
                atomic_json(p, {'v': math.nan})
            self.assertEqual(read_json(p), {'v': 1})
            self.assertEqual(len(sha256(p)), 64)
            self.assertFalse(list(Path(d).glob('*.tmp')))

    def test_calibration_rejects_outside_coordinates_and_resize(self):
        with self.assertRaises(ValueError):
            Calibration(800, 600, ((1.1, .5),))
        c = Calibration(800, 600, ((.5, .5),))
        self.assertEqual(c.screen_point(0, (100, 200, 800, 600)), (500, 500))
        with self.assertRaises(ValueError):
            c.screen_point(0, (0, 0, 1024, 768))


if __name__ == '__main__':
    unittest.main()
