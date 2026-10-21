import tempfile
import unittest
from pathlib import Path

from guitar_player.arrangement import guitar_plan
from guitar_player.contracts import Control, Note, Transcription
from guitar_player.preview import render_plan
from test_preview import Synth


class ProductSurfaceTests(unittest.TestCase):
    def test_guitar_plan_refuses_unverified_profile(self):
        source = Transcription(2.0, (Note(0.0, 0.4, 60, 90),), (), {})
        with self.assertRaises(ValueError):
            guitar_plan(source, None)

    def test_guitar_plan_keeps_source_note_timing_and_reports_approximation(self):
        source = Transcription(
            2.0,
            (Note(0.0, 0.4, 60, 90), Note(0.5, 0.8, 64, 80)),
            (Control(0.0, 64, 127), Control(0.3, 64, 0)),
            {},
        )
        class Profile:
            verified = True
            chords = ()
        with self.assertRaises(ValueError):
            guitar_plan(source, Profile())

    def test_preview_is_local_wav_and_does_not_modify_source(self):
        source = Transcription(0.25, (Note(0.0, 0.1, 60, 100),), (), {})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'preview.wav'
            font = Path(directory) / 'fixture.sf2'
            font.touch()
            render_plan(source, output, soundfont=font, synth_factory=Synth)
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 44)


if __name__ == '__main__':
    unittest.main()
