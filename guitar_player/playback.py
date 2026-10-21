import threading
import time
from .contracts import Action


class InputFailure(RuntimeError):
    pass


class Player:
    def __init__(self, sender, guard, clock=time.perf_counter, late_budget=.1):
        self.sender, self.guard, self.clock = sender, guard, clock
        self.late_budget = late_budget
        self.state, self.reason = 'STOPPED', ''
        self.held = set()
        self.lock = threading.RLock()
        self.plan, self.index, self.position, self.origin = None, 0, 0., 0.

    def start(self, plan, countdown=3., page_verified=False):
        with self.lock:
            if self.state in ('PLAYING', 'ARMED', 'PAUSED') or self.held:
                raise RuntimeError('演奏未停止或仍有输入未释放')
            if plan.mode == 'guitar' and not page_verified:
                raise ValueError('当前吉他页未知，请核对页面')
            self.plan, self.index, self.position = plan, 0, 0.
            self.rebuild = False
            self.origin = self.clock() + countdown
            self.reason, self.state = '', 'ARMED'

    def _send(self, action):
        self.sender.send(action)
        if action.kind in ('down', 'mouse_down'):
            self.held.add((action.kind, action.value))
        elif action.kind in ('up', 'mouse_up'):
            self.held.discard(('down' if action.kind == 'up' else 'mouse_down', action.value))

    def _release(self):
        failures = []
        for kind, value in list(self.held):
            try:
                self._send(Action(0., 'up' if kind == 'down' else 'mouse_up', value))
            except Exception as exc:
                failures.append(str(exc))
        if failures:
            self.reason = '输入释放失败，请手动松键后关闭：' + '; '.join(failures)
            self.state = 'ERROR'

    def stop(self, reason='已停止'):
        with self.lock:
            self.state, self.reason = 'STOPPED', reason
            self._release()

    def pause(self, reason='已暂停；尾音已释放'):
        with self.lock:
            if self.state not in ('PLAYING', 'ARMED'):
                return
            self.position = max(0., min(self.plan.duration, self.clock()-self.origin))
            self.state, self.reason = 'PAUSED', reason
            self._release()

    def resume(self, countdown=3., page_verified=False):
        with self.lock:
            if self.state != 'PAUSED' or self.held:
                raise RuntimeError('当前不能恢复')
            if self.plan.mode == 'guitar' and not page_verified:
                raise ValueError('暂停后页码失效，请重新核对')
            self.origin = self.clock() + countdown - self.position
            self.state = 'ARMED'
            self.rebuild = True

    def tick(self):
        with self.lock:
            if self.state not in ('ARMED', 'PLAYING'):
                return
            try:
                elapsed = self.clock() - self.origin
                if elapsed < self.position:
                    return
                if not self.guard():
                    self.pause('目标窗口失焦、身份或客户区变化；请确认后手动恢复')
                    return
                self.state = 'PLAYING'
                if getattr(self, 'rebuild', False):
                    self.rebuild = False
                    if self.plan.mode == 'keyboard':
                        from .profiles import KEYBOARD_KEYS
                        for n in self.plan.notes:
                            if n.start < self.position < n.end:
                                if not self.guard():
                                    self.pause('恢复过程中失焦')
                                    return
                                self._send(Action(self.position, 'down', KEYBOARD_KEYS[n.pitch-52]))
                while self.index < len(self.plan.actions):
                    elapsed = self.clock() - self.origin
                    a = self.plan.actions[self.index]
                    if a.time > elapsed:
                        break
                    if a.time < self.position:
                        self.index += 1
                        continue
                    if elapsed - a.time > self.late_budget:
                        raise InputFailure(f'调度迟到{elapsed-a.time:.3f}秒，已停止，未补发')
                    if not self.guard():
                        self.pause('发送前目标窗口校验失败')
                        return
                    elapsed = self.clock() - self.origin
                    if elapsed - a.time > self.late_budget:
                        raise InputFailure(f'窗口校验后迟到{elapsed-a.time:.3f}秒，已停止，未补发')
                    self._send(a)
                    self.index += 1
                if self.clock() - self.origin >= self.plan.duration:
                    self.stop('演奏结束')
            except Exception as exc:
                self.state, self.reason = 'ERROR', str(exc)
                self._release()

    def run(self, shutdown):
        while not shutdown.wait(.003):
            self.tick()
            if self.state in ('STOPPED','ERROR'):
                return
        self.stop('程序关闭')
