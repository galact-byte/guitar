from pathlib import Path
import subprocess
import os
import ctypes as C
from ctypes import wintypes as W
import sys
import tempfile
import time
import unittest
import wave
try:
    from guitar_player.jobs import JobManager
    from guitar_player.transcription import decode_audio, verify_model
    from guitar_player.storage import sha256, read_json
except ImportError:
    JobManager = None


class AudioJobsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(JobManager, 'audio worker and generation manager missing')

    def test_decode_unicode_path_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            source, output = Path(d)/'音频 空格.wav', Path(d)/'out.wav'
            with wave.open(str(source), 'wb') as f:
                f.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                f.writeframes(b'\x00\x00'*16000)
            before = sha256(source)
            self.assertAlmostEqual(decode_audio(source, output), 1., places=3)
            self.assertEqual(before, sha256(source))
            with wave.open(str(output), 'rb') as f: self.assertEqual(f.getframerate(), 16000)

    def test_corrupt_empty_and_decoder_missing_report_failure(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)/'bad.mp3'
            source.write_bytes(b'')
            with self.assertRaises(ValueError): decode_audio(source, Path(d)/'x.wav')
            source.write_bytes(b'not music')
            with self.assertRaises(ValueError): decode_audio(source, Path(d)/'x.wav')
            with self.assertRaises((ValueError, OSError)): decode_audio(source, Path(d)/'x.wav', ffmpeg='does-not-exist')

    def test_model_missing_or_bad_hash_is_rejected_before_loading(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'model.pth'
            with self.assertRaises(ValueError): verify_model(path)
            path.write_bytes(b'not a model')
            with self.assertRaises(ValueError): verify_model(path)

    def test_cancel_reaps_only_owned_process_and_rejects_late_result(self):
        with tempfile.TemporaryDirectory() as d:
            jobs = JobManager(Path(d))
            outside = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(10)'])
            try:
                old = jobs.start_command([sys.executable, '-c', 'import time;time.sleep(10)'])
                own = jobs.process
                jobs.cancel()
                self.assertIsNotNone(own.poll())
                self.assertIsNone(outside.poll())
                self.assertFalse(jobs.accept(old))
                jobs.close()
            finally:
                outside.terminate(); outside.wait()

    @unittest.skipUnless(os.name=='nt','Windows process-tree contract')
    def test_cancel_also_reaps_owned_decoder_descendant(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            pidfile=root/'decoder.pid'
            code=f"import subprocess,sys,time,pathlib;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);pathlib.Path({str(pidfile)!r}).write_text(str(p.pid));time.sleep(60)"
            jobs=JobManager(root/'jobs')
            jobs.start_command([sys.executable,'-c',code])
            kernel=C.WinDLL('kernel32',use_last_error=True)
            kernel.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD]
            kernel.OpenProcess.restype=W.HANDLE
            kernel.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD]
            kernel.TerminateProcess.argtypes=[W.HANDLE,W.UINT]
            kernel.CloseHandle.argtypes=[W.HANDLE]
            handle=None
            try:
                deadline=time.monotonic()+5
                pid=None
                while time.monotonic()<deadline:
                    try:
                        value=pidfile.read_text().strip()
                        if value.isdecimal():
                            pid=int(value)
                            break
                    except FileNotFoundError:
                        pass
                    time.sleep(.01)
                self.assertIsNotNone(pid, 'decoder PID was not fully written')
                handle=kernel.OpenProcess(0x100001,False,pid)
                self.assertTrue(handle)
                jobs.cancel()
                self.assertEqual(kernel.WaitForSingleObject(handle,1000),0,'cancel left its decoder alive')
            finally:
                if handle:
                    if kernel.WaitForSingleObject(handle,0)!=0:
                        kernel.TerminateProcess(handle,1)
                        kernel.WaitForSingleObject(handle,3000)
                    kernel.CloseHandle(handle)
                jobs.close()

    def test_new_generation_cannot_commit_old_result(self):
        with tempfile.TemporaryDirectory() as d:
            jobs = JobManager(Path(d))
            old = jobs.start_command([sys.executable, '-c', 'pass'])
            jobs.cancel()
            new = jobs.start_command([sys.executable, '-c', 'pass'])
            self.assertNotEqual(old, new)
            self.assertFalse(jobs.accept(old))
            self.assertTrue(jobs.accept(new))
            jobs.close()

    def test_failed_worker_reports_nonzero_and_log(self):
        with tempfile.TemporaryDirectory() as d:
            jobs = JobManager(Path(d))
            jobs.start_command([sys.executable, '-c', "raise ValueError('broken input')"])
            while jobs.process.poll() is None: time.sleep(.01)
            result = jobs.poll()
            self.assertEqual(result['status'], 'error')
            self.assertIn('broken input', Path(result['log']).read_text())
            jobs.close()


if __name__ == '__main__': unittest.main()
