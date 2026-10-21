import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from guitar_player.contracts import Note, Transcription


class UiTests(unittest.TestCase):
    def setUp(self):
        from guitar_player.app import App
        self.directory = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.app = App(self.root, testing=True, jobs_root=Path(self.directory.name))
        self.root.update()

    def tearDown(self):
        self.app.close()
        self.directory.cleanup()

    def test_starts_unarmed_and_cannot_send_input(self):
        self.assertIsNone(self.app.player)
        self.assertEqual(str(self.app.play_button['state']), 'disabled')
        self.assertEqual(str(self.app.preview_button['state']), 'disabled')

    def test_ready_keyboard_plan_and_preview_do_not_require_game(self):
        self.app.accept_transcription(Transcription(2.,(Note(0.,1.,60,90),),(),{}))
        self.assertIsNotNone(self.app.plan)
        self.assertEqual(str(self.app.preview_button['state']), 'normal')
        self.assertEqual(str(self.app.play_button['state']), 'disabled')

    def test_unverified_guitar_blocks_play_but_raw_preview_still_available(self):
        self.app.accept_transcription(Transcription(2.,(Note(0.,1.,60,90),),(),{}))
        self.app.mode.set('四页吉他')
        self.app.adapt()
        self.assertIsNone(self.app.plan)
        self.assertEqual(str(self.app.play_button['state']), 'disabled')
        self.app.preview_kind.set('原转谱')
        self.app.sync_controls()
        self.assertEqual(str(self.app.preview_button['state']), 'normal')

    def test_new_song_invalidates_result_and_preview(self):
        self.app.accept_transcription(Transcription(2.,(Note(0.,1.,60,90),),(),{}))
        self.app.select_source('新的歌曲.wav')
        self.assertIsNone(self.app.transcription)
        self.assertIsNone(self.app.plan)
        self.assertEqual(str(self.app.preview_button['state']), 'disabled')

    def test_stop_button_visible_at_all_supported_widths(self):
        for width in (760,960,1280):
            self.root.geometry(f'{width}x720')
            self.root.update()
            button = self.app.stop_button
            self.assertTrue(button.winfo_ismapped())
            self.assertLessEqual(button.winfo_x()+button.winfo_width(), button.master.winfo_width())


if __name__ == '__main__': unittest.main()
