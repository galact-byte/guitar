from pathlib import Path
import os
import subprocess
import threading
import uuid
from .storage import ROOT, atomic_json, read_json


class JobManager:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.process, self.job_id, self.directory, self.log = None, None, None, None
        self.generation, self.reported = 0, False
        self.lock = threading.RLock()

    def start_command(self, command, directory=None):
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                raise RuntimeError('已有作业进行中')
            self._close_log()
            self.generation += 1
            self.job_id = f'{self.generation}-{uuid.uuid4().hex}'
            self.directory = Path(directory) if directory else self.root / self.job_id
            self.directory.mkdir(parents=True, exist_ok=True)
            self.log = open(self.directory/'worker.log', 'w', encoding='utf-8')
            self.reported = False
            try:
                self.process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=self.log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except Exception:
                self._close_log()
                self.job_id = None
                raise
            return self.job_id

    def start(self, python, kind, request):
        directory = self.root / uuid.uuid4().hex
        directory.mkdir()
        atomic_json(directory/'request.json', request)
        ident = self.start_command([str(python), '-m', 'guitar_player.worker', kind, str(directory)], directory)
        return ident

    def accept(self, job_id):
        with self.lock:
            return self.job_id is not None and job_id == self.job_id

    def poll(self):
        with self.lock:
            if self.process is None or self.reported:
                return None
            code = self.process.poll()
            if code is None:
                progress = self.directory/'progress.json'
                try:
                    stage = read_json(progress) if progress.exists() else {'message': '正在启动独立作业…'}
                except (OSError, ValueError):
                    stage = {'message': '正在处理…'}
                return {'status': 'running', 'job_id': self.job_id, **stage}
            self.reported = True
            self._close_log()
            path = self.directory/'result.json'
            if code or not path.exists():
                return {'status': 'error', 'job_id': self.job_id, 'log': str(self.directory/'worker.log'), 'message': f'处理失败（退出码{code}），请打开日志查看原因'}
            return {'status': 'success', 'job_id': self.job_id, 'directory': str(self.directory), 'result': read_json(path)}

    def _close_log(self):
        if self.log is not None:
            self.log.close()
            self.log = None

    def cancel(self):
        with self.lock:
            self.job_id = None
            self.generation += 1
            if self.process is not None and self.process.poll() is None:
                if os.name == 'nt':
                    killer = Path(os.environ['SystemRoot'])/'System32/taskkill.exe'
                    result = subprocess.run([str(killer),'/PID',str(self.process.pid),'/T','/F'],
                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5.,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    if result.returncode and self.process.poll() is None:
                        raise RuntimeError('无法结束本工具的作业进程树，请先查看worker.log；未操作其他进程')
                else:
                    self.process.terminate()
                try:
                    self.process.wait(timeout=3.)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3.)
            self._close_log()
            self.process = None

    def close(self):
        self.cancel()
