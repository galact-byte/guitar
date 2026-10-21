"""原生桌面界面。主线程只管理状态，模型与试听合成在独立作业中。"""
from pathlib import Path
import logging
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import winsound
from .arrangement import guitar_plan, keyboard_plan
from .contracts import Transcription
from .jobs import JobManager
from .playback import Player
from .runtime import model_path, settings, soundfont_path, worker_python
from .storage import DATA, atomic_json, content_hash, read_json
from .win_input import Hotkeys, WinSender, client_rect, foreground_matches, windows


class App:
    def __init__(self, root, testing=False, jobs_root=None):
        self.root, self.testing = root, testing
        self.closed, self.busy = False, False
        self.transcription = self.plan = self.player = self.target = None
        self.worker_id = self.job_kind = None
        self.source = None
        self.preview_until, self.preview_files = 0., {}
        self.targets, self.hotkeys, self.player_thread = [], None, None
        self.shutdown, self.events = threading.Event(), queue.Queue()
        self.jobs = JobManager(jobs_root or DATA/'jobs')
        self.mode = tk.StringVar(value='36键键盘')
        self.preview_kind = tk.StringVar(value='游戏适配')
        self.status = tk.StringVar(value='请选择一首歌曲，开始本地处理')
        self.song = tk.StringVar(value='尚未选择歌曲')
        self.window_name = tk.StringVar(value='未绑定目标窗口')
        self.detail = tk.StringVar(value='钢琴识别模型用于普通音频，但复杂混音可能出现误音。请先试听。')
        self.progress = tk.DoubleVar(value=0.)
        self._build()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.report_callback_exception = self.callback_error
        if not testing:
            try:
                self.hotkeys = Hotkeys(self.emergency_stop, lambda: self.events.put('toggle'))
            except OSError as exc:
                self.status.set(str(exc))
        self.sync_controls()
        self.poll_id = root.after(80, self.poll)

    def _build(self):
        root = self.root
        root.title('异环 · 本地演奏')
        scale=max(1.,float(root.tk.call('tk','scaling'))/(5/3))
        min_width,min_height=round(760*scale),round(720*scale)
        root.geometry(f'{max(960,min_width)}x{min_height}')
        root.minsize(min_width,min_height)
        root.configure(background='#f1f5f9')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('Microsoft YaHei UI', 11), background='#f1f5f9', foreground='#0f172a')
        style.configure('TButton', padding=(12,8))
        style.configure('Accent.TButton', background='#0f766e', foreground='white')
        style.map('Accent.TButton', background=[('disabled','#cbd5e1'),('active','#115e59')])
        style.configure('Stop.TButton', background='#b91c1c', foreground='white')
        style.map('Stop.TButton', background=[('active','#991b1b')])
        style.configure('Title.TLabel', font=('等线',20,'bold'))
        style.configure('Section.TLabel', font=('Microsoft YaHei UI',12,'bold'))
        style.configure('Hint.TLabel', foreground='#475569', font=('Microsoft YaHei UI',10))
        outer = ttk.Frame(root, padding=20)
        outer.pack(fill='both', expand=True)
        outer.columnconfigure(0, weight=1)
        ttk.Label(outer,text='异环 · 本地演奏',style='Title.TLabel').grid(row=0,column=0,sticky='w')
        ttk.Label(outer,text='音频只在本机处理 · F8 随时停止',style='Hint.TLabel').grid(row=1,column=0,sticky='w',pady=(6,10))
        ttk.Separator(outer).grid(row=2,column=0,sticky='ew')
        songrow = ttk.Frame(outer)
        songrow.grid(row=3,column=0,sticky='ew',pady=(10,8))
        songrow.columnconfigure(0,weight=1)
        ttk.Label(songrow,text='01  选择歌曲',style='Section.TLabel').grid(row=0,column=0,sticky='w')
        self.select_button = ttk.Button(songrow,text='选择音频…',command=self.choose_source)
        self.select_button.grid(row=0,column=1,padx=(8,0))
        ttk.Entry(outer,textvariable=self.song,state='readonly').grid(row=4,column=0,sticky='ew')
        processrow = ttk.Frame(outer)
        processrow.grid(row=5,column=0,sticky='ew',pady=(8,10))
        self.process_button = ttk.Button(processrow,text='自动转谱',command=self.process,style='Accent.TButton')
        self.process_button.pack(side='left')
        self.cancel_button = ttk.Button(processrow,text='取消处理',command=self.cancel)
        self.cancel_button.pack(side='left',padx=8)
        ttk.Button(processrow,text='环境设置…',command=self.environment).pack(side='right')
        ttk.Separator(outer).grid(row=6,column=0,sticky='ew')
        ttk.Label(outer,text='02  演奏模式与窗口',style='Section.TLabel').grid(row=7,column=0,sticky='w',pady=(10,8))
        modes = ttk.Frame(outer)
        modes.grid(row=8,column=0,sticky='ew')
        self.mode_box = ttk.Combobox(modes,textvariable=self.mode,values=('36键键盘','四页吉他'),state='readonly',width=13)
        self.mode_box.pack(side='left')
        self.mode_box.bind('<<ComboboxSelected>>',lambda event:self.change_mode())
        self.calibrate_button = ttk.Button(modes,text='校准与四页取证…',command=self.calibrate)
        self.calibrate_button.pack(side='left',padx=8)
        ttk.Button(modes,text='刷新窗口',command=self.refresh_windows).pack(side='right')
        self.window_box = ttk.Combobox(outer,textvariable=self.window_name,state='readonly')
        self.window_box.grid(row=9,column=0,sticky='ew',pady=(8,10))
        self.window_box.bind('<<ComboboxSelected>>',self.bind_target)
        ttk.Separator(outer).grid(row=10,column=0,sticky='ew')
        ttk.Label(outer,text='03  试听与演奏',style='Section.TLabel').grid(row=11,column=0,sticky='w',pady=(10,8))
        listen = ttk.Frame(outer)
        listen.grid(row=12,column=0,sticky='ew')
        for value in ('游戏适配','原转谱'):
            ttk.Radiobutton(listen,text=value,variable=self.preview_kind,value=value,command=self.sync_controls).pack(side='left',padx=(0,16))
        ttk.Label(listen,text='采样参考音色，非游戏实音',style='Hint.TLabel').pack(side='right')
        actions = ttk.Frame(outer)
        actions.grid(row=13,column=0,sticky='ew',pady=(8,10))
        for col in range(4): actions.columnconfigure(col,weight=1,uniform='actions')
        self.preview_button = ttk.Button(actions,text='试听',command=self.preview)
        self.play_button = ttk.Button(actions,text='开始演奏',command=self.play,style='Accent.TButton')
        self.pause_button = ttk.Button(actions,text='暂停 / 恢复',command=self.toggle)
        self.stop_button = ttk.Button(actions,text='停止  F8',command=self.stop,style='Stop.TButton')
        for index, button in enumerate((self.preview_button,self.play_button,self.pause_button,self.stop_button)):
            button.grid(row=0,column=index,sticky='ew',padx=(0,8) if index<3 else 0)
        ttk.Progressbar(outer,variable=self.progress,maximum=100).grid(row=14,column=0,sticky='ew')
        self.status_label = ttk.Label(outer,textvariable=self.status,wraplength=680)
        self.status_label.grid(row=15,column=0,sticky='ew',pady=(10,0))
        self.detail_label = ttk.Label(outer,textvariable=self.detail,style='Hint.TLabel',wraplength=680)
        self.detail_label.grid(row=16,column=0,sticky='ew',pady=(8,0))
        outer.rowconfigure(17,weight=1)
        footer = self.footer = ttk.Frame(outer)
        footer.grid(row=18,column=0,sticky='ew',pady=(12,0))
        ttk.Label(footer,text='失焦后停止发声，不自动恢复 · F9 暂停 / 恢复',style='Hint.TLabel').pack(side='left')
        self.log_button = ttk.Button(footer,text='打开日志',command=self.open_logs)
        self.log_button.pack(side='right')
        root.bind('<Configure>',self.resize)

    def resize(self, event):
        if event.widget is self.root:
            width = max(560,event.width-80)
            self.status_label.configure(wraplength=width)
            self.detail_label.configure(wraplength=width)

    def callback_error(self, kind, exc, trace):
        logging.error('UI callback failed',exc_info=(kind,exc,trace))
        self.stop()
        self.status.set(f'操作失败：{exc}')

    def choose_source(self):
        path = filedialog.askopenfilename(parent=self.root,title='选择MP3或WAV歌曲',filetypes=[('音频','*.mp3 *.wav'),('全部文件','*.*')])
        if path: self.select_source(path)

    def select_source(self, path):
        self.stop()
        self.source = Path(path)
        self.transcription = self.plan = None
        self.preview_files.clear()
        self.song.set(self.source.name)
        self.status.set('已选择歌曲，点击“自动转谱”')
        self.progress.set(0.)
        self.sync_controls()

    def process(self):
        if not self.source or self.busy or self.active_player(): return
        try:
            self.worker_id = self.jobs.start(worker_python('transcribe'),'transcribe',{'source':str(self.source.resolve()),'model':str(model_path())})
            self.job_kind, self.busy = 'transcribe', True
            self.transcription = self.plan = None
            self.preview_files.clear()
            self.status.set('正在启动本地GPU作业…')
        except (OSError,ValueError,RuntimeError) as exc:
            self.status.set(str(exc))
        self.sync_controls()

    def accept_transcription(self, result):
        self.transcription = result
        self.preview_files.clear()
        self.status.set(f'整曲转谱已生成 · {result.duration:.1f}秒 · {len(result.notes)}个音符 · 请先试听')
        self.adapt()

    def change_mode(self):
        self.stop()
        self.adapt()

    def adapt(self):
        self.plan = None
        if self.transcription:
            try:
                self.plan = keyboard_plan(self.transcription) if self.mode.get()=='36键键盘' else guitar_plan(self.transcription,None)
                self.detail.set(f'适配 {len(self.plan.notes)} 音 · 音域调整 {len(self.plan.report.get("pitch_changes",[]))} 音 · 峰值复音 {self.plan.report.get("peak_polyphony","—")}。键位、复音与时序尚待游戏验证。')
            except ValueError as exc:
                self.detail.set(str(exc)+'；目前可试听原转谱，四页取证完成前不会盲点。')
        self.sync_controls()

    def active_player(self):
        return self.player is not None and self.player.state in ('ARMED','PLAYING','PAUSED')

    def sync_controls(self):
        idle = not self.busy and not self.active_player() and time.monotonic()>=self.preview_until
        playable = bool(idle and self.plan and self.target and self.hotkeys and not self.testing and self.mode.get()=='36键键盘')
        self.play_button.configure(state='normal' if playable else 'disabled')
        available = self.transcription is not None and (self.preview_kind.get()=='原转谱' or self.plan is not None)
        self.preview_button.configure(state='normal' if idle and available else 'disabled')
        self.process_button.configure(state='normal' if idle and self.source else 'disabled')
        self.cancel_button.configure(state='normal' if self.busy else 'disabled')
        self.pause_button.configure(state='normal' if self.active_player() else 'disabled')
        self.mode_box.configure(state='readonly' if idle else 'disabled')
        self.window_box.configure(state='readonly' if idle else 'disabled')
        self.calibrate_button.configure(state='normal' if idle and self.target else 'disabled')

    def preview_key(self):
        return content_hash({'transcription':self.transcription.to_dict(),'plan':self.plan.to_dict() if self.preview_kind.get()=='游戏适配' and self.plan else None})

    def preview(self):
        if self.busy or self.active_player() or not self.transcription: return
        adapted = self.preview_kind.get()=='游戏适配'
        if adapted and not self.plan: return
        try:
            key = self.preview_key()
            if key in self.preview_files:
                path,duration = self.preview_files[key]
                winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
                self.preview_until = time.monotonic()+duration
                self.status.set('正在试听'+('游戏适配' if adapted else '原转谱')+' · 仅采样音色，不含原曲')
            else:
                self.worker_id = self.jobs.start(worker_python('preview'),'preview',{'transcription':self.transcription.to_dict(),'plan':self.plan.to_dict() if adapted else None,'soundfont':str(soundfont_path())})
                self.job_kind, self.preview_job_key, self.busy = 'preview',key,True
                self.status.set('正在生成采样试听…')
        except (OSError,ValueError,RuntimeError) as exc:
            self.status.set(str(exc))
        self.sync_controls()

    def refresh_windows(self):
        if self.active_player(): return
        try:
            self.targets = windows()
            self.window_box.configure(values=[title for title,_ in self.targets])
            self.target = None
            self.window_name.set('请从列表选择游戏窗口')
        except OSError as exc: self.status.set(str(exc))
        self.sync_controls()

    def bind_target(self, event=None):
        self.stop()
        index = self.window_box.current()
        self.target = self.targets[index][1] if 0<=index<len(self.targets) else None
        self.sync_controls()

    def play(self):
        if self.testing or self.busy or not self.plan or not self.target or not self.hotkeys: return
        if self.mode.get()!='36键键盘': return
        if not messagebox.askokcancel('前台演奏风险','普通模拟输入仍可能有账号风险。\n请确认目标窗口是《异环》，并已进入36键键盘界面。\n确认后有5秒切回游戏；F8停止，失焦后不会自动恢复。',parent=self.root): return
        winsound.PlaySound(None,0)
        self.preview_until = 0.
        try:
            self.bound_size = client_rect(self.target.hwnd)[2:]
            self.player = Player(WinSender(self.target),lambda:foreground_matches(self.target,self.bound_size))
            self.player.start(self.plan,countdown=5.)
            self.shutdown.clear()
            self.player_thread = threading.Thread(target=self.player.run,args=(self.shutdown,),name='performance',daemon=True)
            self.player_thread.start()
            self.status.set('5秒倒计时，请切回选定的游戏窗口；F8立即停止')
        except (ValueError,OSError,RuntimeError) as exc: self.status.set(str(exc))
        self.sync_controls()

    def toggle(self):
        if not self.player: return
        try:
            if self.player.state in ('ARMED','PLAYING'):
                self.player.pause()
            elif self.player.state=='PAUSED':
                self.player.resume(countdown=3.)
        except (ValueError,RuntimeError) as exc: self.status.set(str(exc))
        self.sync_controls()

    def emergency_stop(self):
        if self.player: self.player.stop('F8紧急停止')
        self.events.put('stop')

    def cancel(self):
        self.jobs.cancel()
        self.worker_id, self.busy = None,False
        self.status.set('已取消；旧作业结果不会覆盖当前歌曲')
        self.sync_controls()

    def stop(self):
        if self.player: self.player.stop()
        self.shutdown.set()
        if self.player_thread and self.player_thread.is_alive(): self.player_thread.join(1.)
        if self.busy: self.cancel()
        winsound.PlaySound(None,0)
        self.preview_until = 0.
        self.status.set(self.player.reason if self.player else '已停止')
        self.sync_controls()

    def poll(self):
        if self.closed: return
        try:
            while not self.events.empty():
                event = self.events.get_nowait()
                self.stop() if event=='stop' else self.toggle()
            if self.busy:
                state = self.jobs.poll()
                if state and self.jobs.accept(state['job_id']) and state['job_id']==self.worker_id:
                    if state['status']=='running': self.status.set(state['message'])
                    else:
                        self.busy, self.worker_id = False,None
                        if state['status']=='error': self.status.set(state['message'])
                        elif self.job_kind=='transcribe':
                            self.accept_transcription(Transcription.from_dict(read_json(state['result']['transcription'])))
                        else:
                            result = state['result']
                            self.preview_files[self.preview_job_key] = (result['preview'],result['duration'])
                            self.preview()
            if self.player and self.player.state in ('PLAYING','ARMED','PAUSED','ERROR'):
                if self.player.state=='PLAYING':
                    position = max(0.,time.perf_counter()-self.player.origin)
                    self.progress.set(min(100,position/self.player.plan.duration*100))
                    self.status.set(f'正在演奏 {position:.1f} / {self.player.plan.duration:.1f}秒 · F8停止')
                elif self.player.state in ('PAUSED','ERROR'): self.status.set(self.player.reason)
            self.sync_controls()
        except Exception as exc:
            logging.exception('poll failed')
            self.busy=False
            self.stop()
            self.status.set(f'处理失败：{exc}；详情见日志')
        self.poll_id = self.root.after(80,self.poll)

    def calibrate(self):
        from .calibration_ui import CalibrationWizard
        if self.target and not self.active_player() and not self.busy:
            CalibrationWizard(self.root,self.target)

    def environment(self):
        if self.busy or self.active_player(): return
        dialog = tk.Toplevel(self.root)
        dialog.title('本地环境设置')
        dialog.transient(self.root)
        dialog.grab_set()
        try: value = settings()
        except ValueError: value = {}
        fields = (('模型权重','model',str(model_path())),('采样音色 SF2','soundfont',str(soundfont_path())),('FFmpeg','ffmpeg',value.get('ffmpeg','')))
        variables = {}
        for row,(title,key,default) in enumerate(fields):
            ttk.Label(dialog,text=title).grid(row=row,column=0,padx=12,pady=12)
            variable=tk.StringVar(value=default)
            variables[key]=variable
            ttk.Entry(dialog,textvariable=variable,width=50).grid(row=row,column=1)
            ttk.Button(dialog,text='选择…',command=lambda v=variable:v.set(filedialog.askopenfilename(parent=dialog) or v.get())).grid(row=row,column=2,padx=8)
        def save():
            update={k:v.get() for k,v in variables.items() if v.get()}
            atomic_json(DATA/'runtime.json',{**value,**update})
            dialog.destroy()
        ttk.Button(dialog,text='保存',command=save).grid(row=4,column=2,padx=12,pady=12)

    def open_logs(self):
        (DATA/'logs').mkdir(parents=True,exist_ok=True)
        os.startfile(str(self.jobs.directory if self.jobs.directory else DATA/'logs'))

    def close(self):
        if self.closed: return
        self.stop()
        self.jobs.close()
        if self.hotkeys: self.hotkeys.close()
        self.closed=True
        self.root.after_cancel(self.poll_id)
        self.root.destroy()


def main():
    DATA.mkdir(exist_ok=True)
    (DATA/'logs').mkdir(exist_ok=True)
    logging.basicConfig(filename=DATA/'logs/app.log',encoding='utf-8',level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    import ctypes
    ctypes.windll.user32.SetProcessDPIAware()
    root = tk.Tk()
    App(root)
    root.mainloop()
