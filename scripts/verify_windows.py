"""只向本脚本创建的窗口验证输入；不选择或操作游戏。"""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import os
import sys
import threading
import time
import tkinter as tk

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from guitar_player.contracts import Action
from guitar_player.profiles import KEYBOARD_KEYS
from guitar_player.storage import DATA, atomic_json
from guitar_player.win_input import Hotkeys, WinSender, api, foreground_matches, identity, input_size


def main():
    user,_=api()
    user.SetProcessDPIAware()
    user.GetAncestor.argtypes=[W.HWND,W.UINT]
    user.GetAncestor.restype=W.HWND
    user.SetForegroundWindow.argtypes=[W.HWND]
    user.PostThreadMessageW.argtypes=[W.DWORD,W.UINT,W.WPARAM,W.LPARAM]
    root=tk.Tk()
    root.title('演奏工具输入自检 · 仅本窗口')
    root.geometry('640x240')
    entry=tk.Entry(root,font=('Segoe UI',16))
    entry.pack(fill='x',padx=20,pady=30)
    events=[]
    entry.bind('<KeyPress>',lambda event:events.append(('down',event.keysym)))
    entry.bind('<KeyRelease>',lambda event:events.append(('up',event.keysym)))
    sender=None
    held=set()
    hotkeys=None
    report={'game_input':False,'pid':os.getpid(),'input_bytes':input_size()}
    try:
        root.update()
        hwnd=user.GetAncestor(root.winfo_id(),2)
        target=identity(hwnd)
        assert target.pid==os.getpid()
        user.SetForegroundWindow(hwnd)
        entry.focus_force()
        root.update()
        if not foreground_matches(target):
            raise RuntimeError('测试窗口未获前台；未发任何输入')
        sender=WinSender(target)
        stop,toggle=threading.Event(),threading.Event()
        hotkeys=Hotkeys(stop.set,toggle.set)
        for ident,event in ((1,stop),(2,toggle)):
            assert user.PostThreadMessageW(hotkeys.thread.native_id,0x0312,ident,0)
            assert event.wait(1.),'hotkey callback timeout'
        for key in KEYBOARD_KEYS:
            if any(user.GetAsyncKeyState(vk)&0x8000 for vk in (0x10,0x11,0x12,0x5B,0x5C)):
                raise RuntimeError('检测到物理修饰键，停止自检')
            sender.send(Action(0.,'down',key))
            held.add(key)
            root.update()
            sender.send(Action(0.,'up',key))
            held.remove(key)
            root.update()
        assert len([e for e in events if e[0]=='down'])==36,events
        assert len([e for e in events if e[0]=='up'])==36,events
        hotkeys.close()
        hotkeys=Hotkeys(stop.set,toggle.set)
        report.update({'keys_down':36,'keys_up':36,'hotkey_callbacks':['F8','F9'],
                       'hotkey_unregister_and_reregister':True,'events':events,'status':'passed'})
        atomic_json(DATA/'verification/windows-input.json',report)
        print('36 key-down/up pairs, F8/F9 callbacks and unregister/reregister passed; own window only')
    finally:
        if sender:
            for key in held: sender.send(Action(0.,'up',key))
        if hotkeys: hotkeys.close()
        root.destroy()


if __name__=='__main__': main()
