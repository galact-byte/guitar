import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from guitar_player import runtime


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.patches=[patch.object(runtime,'ROOT',self.root),patch.object(runtime,'DATA',self.root/'data')]
        for item in self.patches: item.start()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(lambda:[item.stop() for item in reversed(self.patches)])

    def test_reuse_existing_model_and_soundfont_without_download(self):
        model=runtime.model_path()
        model.parent.mkdir(parents=True,exist_ok=True)
        model.touch()
        soundfont=runtime.soundfont_path()
        soundfont.parent.mkdir(parents=True,exist_ok=True)
        soundfont.touch()
        self.assertEqual(runtime.model_path(),model)
        self.assertEqual(runtime.soundfont_path(),soundfont)

    def test_model_worker_and_preview_worker_use_separate_existing_envs(self):
        for env in ('.venv-piano-probe','.venv-transcription'):
            path=self.root/env/'Scripts/python.exe'
            path.parent.mkdir(parents=True)
            path.touch()
        self.assertIn('.venv-piano-probe', str(runtime.worker_python('transcribe')))
        self.assertIn('.venv-transcription', str(runtime.worker_python('preview')))

    def test_missing_worker_is_reported_not_silently_replaced(self):
        with self.assertRaises(OSError): runtime.worker_python('transcribe')
        with patch.object(runtime,'settings',return_value={'model_python':'Z:/missing/python.exe'}):
            with self.assertRaises(OSError): runtime.worker_python('transcribe')

    def test_invalid_config_does_not_silently_disappear(self):
        path=self.root/'data'
        path.mkdir()
        (path/'runtime.json').write_text('{bad',encoding='utf-8')
        with self.assertRaises(ValueError): runtime.settings()


if __name__ == '__main__': unittest.main()
