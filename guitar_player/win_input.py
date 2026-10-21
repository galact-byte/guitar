"""Narrow Win32 foreground boundary. Importing this module never sends input."""
import ctypes as C
from ctypes import wintypes as W
from dataclasses import dataclass
import os
import threading
from .profiles import KEYBOARD_KEYS

ULONG_PTR = C.c_size_t


class MOUSEINPUT(C.Structure):
    _fields_ = [('dx', C.c_int32), ('dy', C.c_int32), ('mouseData', C.c_uint32), ('dwFlags', C.c_uint32), ('time', C.c_uint32), ('dwExtraInfo', ULONG_PTR)]


class KEYBDINPUT(C.Structure):
    _fields_ = [('wVk', C.c_uint16), ('wScan', C.c_uint16), ('dwFlags', C.c_uint32), ('time', C.c_uint32), ('dwExtraInfo', ULONG_PTR)]


class HARDWAREINPUT(C.Structure):
    _fields_ = [('uMsg', C.c_uint32), ('wParamL', C.c_uint16), ('wParamH', C.c_uint16)]


class INPUTUNION(C.Union):
    _fields_ = [('mi', MOUSEINPUT), ('ki', KEYBDINPUT), ('hi', HARDWAREINPUT)]


class INPUT(C.Structure):
    _anonymous_ = ('u',)
    _fields_ = [('type', C.c_uint32), ('u', INPUTUNION)]


def input_size():
    return C.sizeof(INPUT)


def api():
    if os.name != 'nt':
        raise OSError('仅支持Windows')
    user = C.WinDLL('user32', use_last_error=True)
    kernel = C.WinDLL('kernel32', use_last_error=True)
    user.GetForegroundWindow.restype = W.HWND
    user.IsWindow.argtypes = [W.HWND]
    user.IsIconic.argtypes = [W.HWND]
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user.GetClientRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
    user.ClientToScreen.argtypes = [W.HWND, C.POINTER(W.POINT)]
    user.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
    user.GetWindowTextLengthW.argtypes = [W.HWND]
    user.IsWindowVisible.argtypes = [W.HWND]
    user.SendInput.argtypes = [W.UINT, C.POINTER(INPUT), C.c_int]
    user.SendInput.restype = W.UINT
    user.GetSystemMetrics.argtypes = [C.c_int]
    kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    kernel.OpenProcess.restype = W.HANDLE
    kernel.CloseHandle.argtypes = [W.HANDLE]
    kernel.QueryFullProcessImageNameW.argtypes = [W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)]
    kernel.GetProcessTimes.argtypes = [W.HANDLE] + [C.POINTER(W.FILETIME)]*4
    return user, kernel


@dataclass(frozen=True)
class WindowIdentity:
    hwnd: int
    pid: int
    created: int
    executable: str


def identity(hwnd):
    user, kernel = api()
    if not user.IsWindow(hwnd):
        raise ValueError('目标窗口已关闭')
    pid = W.DWORD()
    user.GetWindowThreadProcessId(hwnd, C.byref(pid))
    handle = kernel.OpenProcess(0x1000, False, pid.value)
    if not handle:
        raise OSError('无法读取目标进程身份；请勿自动提权')
    try:
        created, exited, kt, ut = W.FILETIME(), W.FILETIME(), W.FILETIME(), W.FILETIME()
        if not kernel.GetProcessTimes(handle, C.byref(created), C.byref(exited), C.byref(kt), C.byref(ut)):
            raise C.WinError(C.get_last_error())
        name, length = C.create_unicode_buffer(32768), W.DWORD(32768)
        if not kernel.QueryFullProcessImageNameW(handle, 0, name, C.byref(length)):
            raise C.WinError(C.get_last_error())
        return WindowIdentity(int(hwnd), pid.value, (created.dwHighDateTime << 32) | created.dwLowDateTime, name.value)
    finally:
        kernel.CloseHandle(handle)


def client_rect(hwnd):
    user, _ = api()
    rect, point = W.RECT(), W.POINT()
    if not user.GetClientRect(hwnd, C.byref(rect)) or not user.ClientToScreen(hwnd, C.byref(point)):
        raise OSError('无法读取目标客户区')
    return point.x, point.y, rect.right, rect.bottom


def foreground_matches(target, size=None):
    try:
        user, _ = api()
        return (user.GetForegroundWindow() == target.hwnd and not user.IsIconic(target.hwnd) and identity(target.hwnd) == target and (size is None or client_rect(target.hwnd)[2:] == tuple(size)))
    except (OSError, ValueError):
        return False


def windows():
    user, _ = api()
    result = []
    callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    def collect(hwnd, _):
        if user.IsWindowVisible(hwnd):
            title = C.create_unicode_buffer(user.GetWindowTextLengthW(hwnd)+1)
            user.GetWindowTextW(hwnd, title, len(title))
            if title.value:
                try:
                    target = identity(hwnd)
                    if target.pid != os.getpid():
                        result.append((title.value, target))
                except (OSError, ValueError):
                    pass
        return True
    callback = callback_type(collect)
    user.EnumWindows.argtypes = [callback_type, W.LPARAM]
    if not user.EnumWindows(callback, 0):
        raise OSError('读取窗口列表失败')
    return result


VK = {key: ord(key) for key in KEYBOARD_KEYS if len(key) == 1 and key.isalnum()}
VK.update({'ENTER': 0x0D, ';': 0xBA, "'": 0xDE, '[': 0xDB, ']': 0xDD, '-': 0xBD, '=': 0xBB})


class WinSender:
    def __init__(self, target, calibration=None, page_check=None):
        self.target, self.calibration, self.page_check = target, calibration, page_check
        self.user, _ = api()

    def send(self, action):
        if action.kind not in ('up', 'mouse_up') and not foreground_matches(self.target, (self.calibration.width, self.calibration.height) if self.calibration else None):
            raise OSError('发送前目标身份或前台校验失败')
        if action.kind == 'verify_page':
            if not self.page_check or not self.page_check(action.value):
                raise OSError('分页区域核对失败，停止演奏')
            return
        packet = INPUT()
        if action.kind in ('up', 'down'):
            packet.type = 1
            vk = VK.get(action.value)
            if vk is None:
                raise ValueError('不支持的键')
            scan = self.user.MapVirtualKeyW(vk, 0)
            if not scan:
                raise OSError('无法解析扫描码')
            packet.ki = KEYBDINPUT(0, scan, 0x0008 | (0x0002 if action.kind == 'up' else 0), 0, 0)
        else:
            packet.type = 0
            if action.kind == 'move':
                if not self.calibration:
                    raise ValueError('未校准鼠标')
                x, y = self.calibration.screen_point(action.value, client_rect(self.target.hwnd))
                left, top = self.user.GetSystemMetrics(76), self.user.GetSystemMetrics(77)
                width, height = self.user.GetSystemMetrics(78), self.user.GetSystemMetrics(79)
                if width <= 1 or height <= 1:
                    raise OSError('虚拟桌面尺寸无效')
                packet.mi = MOUSEINPUT(round((x-left)*65535/(width-1)), round((y-top)*65535/(height-1)), 0, 0x0001 | 0x8000 | 0x4000, 0, 0)
            elif action.kind in ('mouse_down', 'mouse_up') and action.value == 'left':
                packet.mi.dwFlags = 0x0002 if action.kind == 'mouse_down' else 0x0004
            else:
                raise ValueError('不支持的鼠标动作')
        # Send one event at a time: a partial batch is never replayed.
        if self.user.SendInput(1, C.byref(packet), C.sizeof(INPUT)) != 1:
            raise OSError(f'Windows拒绝输入({C.get_last_error()})，停止；不自动提权')


class Hotkeys:
    def __init__(self, stop, toggle):
        self.stop_callback, self.toggle_callback = stop, toggle
        self.ready, self.closing = threading.Event(), threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self._run, name='hotkeys', daemon=True)
        self.thread.start()
        if not self.ready.wait(3.):
            raise OSError('热键注册超时')
        if self.error:
            raise OSError(self.error)

    def _run(self):
        user, _ = api()
        registered = []
        try:
            for ident, key in ((1, 0x77), (2, 0x78)):
                if not user.RegisterHotKey(None, ident, 0x4000, key):
                    raise OSError('F8/F9热键冲突；请关闭占用程序后重新启动，演奏已禁用')
                registered.append(ident)
            self.ready.set()
            message = W.MSG()
            while not self.closing.wait(.005):
                while user.PeekMessageW(C.byref(message), None, 0, 0, 1):
                    if message.message == 0x0312:
                        (self.stop_callback if message.wParam == 1 else self.toggle_callback)()
        except Exception as exc:
            self.error = str(exc)
            self.ready.set()
            self.stop_callback()
        finally:
            for ident in registered:
                user.UnregisterHotKey(None, ident)

    def close(self):
        self.closing.set()
        self.thread.join(3.)
