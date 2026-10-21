import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from guitar_player.contracts import Control, Note, Transcription
from guitar_player.arrangement import keyboard_plan
from guitar_player.preview import render_plan


class Synth:
    instances = []
    def __init__(self, samplerate):
        self.calls = []
        self.instances.append(self)
    def sfload(self, path): return 1
    def program_select(self, *args): self.calls.append(('program', args[-1]))
    def noteon(self, channel, pitch, velocity):
        self.calls.append(('on', pitch))
        return True
    def noteoff(self, channel, pitch): self.calls.append(('off', pitch))
    def generate_simple(self, frames): return array('f', [.1, .1] * frames).tobytes()
    def sfunload(self, ident): pass


class PreviewTests(unittest.TestCase):
    def render(self, source, plan=None):
        with tempfile.TemporaryDirectory() as directory:
            sf = Path(directory) / 'test.sf2'
            sf.touch()
            output = Path(directory) / '试听.wav'
            render_plan(source, output, plan, soundfont=sf, synth_factory=Synth)
            with wave.open(str(output)) as stream:
                self.assertEqual(stream.getnframes(), round(source.duration * 22050))
            return Synth.instances[-1].calls

    def test_reference_preview_defers_release_until_explicit_pedal_up(self):
        source = Transcription(.4, (Note(0., .1, 60, 90),), (Control(0., 64, 127), Control(.3, 64, 0)), {})
        self.assertEqual(self.render(source), [('program', 0), ('on', 60), ('off', 60)])

    def test_adapted_preview_uses_plan_notes_and_no_source_pedal(self):
        source = Transcription(.4, (Note(0., .1, 20, 90),), (Control(0., 64, 127),), {})
        calls = self.render(source, keyboard_plan(source))
        self.assertNotIn(('on', 20), calls)
        self.assertEqual(sum(c[0] == 'off' for c in calls), 1)

    def test_pedal_release_does_not_cut_repressed_key(self):
        source = Transcription(.5, (Note(0., .1, 60, 90), Note(.2, .4, 60, 90)), (Control(0., 64, 127), Control(.3, 64, 0)), {})
        self.assertEqual(self.render(source)[1:], [('on', 60), ('on', 60), ('off', 60)])

    def test_missing_soundfont_does_not_generate_sine_fallback(self):
        source = Transcription(.1, (Note(0., .05, 60, 90),), (), {})
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                render_plan(source, Path(directory) / 'out.wav', soundfont=Path(directory) / 'missing.sf2', synth_factory=Synth)


if __name__ == '__main__': unittest.main()
