"""用户主动采集选定窗口；不发按键，不切换游戏页面。"""
from dataclasses import asdict
from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk
from .storage import DATA, atomic_json, sha256
from .win_input import client_rect, foreground_matches

POINT_NAMES = ('和弦选区1','和弦选区2','和弦选区3','和弦选区4','和弦选区5','和弦选区6',
               '扫弦起点','扫弦终点','分页点1','分页点2','分页点3','分页点4')


class CalibrationWizard:
    def __init__(self, parent, target):
        self.target, self.points, self.pages = target, [], {}
        self.image = self.photo = None
        self.size = None
        self.closed, self.timer = False,None
        self.directory = DATA/'calibration'/time.strftime('%Y%m%d-%H%M%S')
        self.window = tk.Toplevel(parent)
        self.window.title('四页校准取证 · 不发送游戏输入')
        self.window.geometry('900x720')
        self.window.minsize(760,600)
        self.window.transient(parent)
        self.page = tk.StringVar(value='第1页')
        self.status = tk.StringVar(value='等待目标窗口截图 · 四页标签与动作尚待确认')
        row = ttk.Frame(self.window,padding=12)
        row.pack(fill='x')
        ttk.Combobox(row,textvariable=self.page,values=('第1页','第2页','第3页','第4页'),state='readonly',width=10).pack(side='left')
        self.capture_button = ttk.Button(row,text='3秒后采集目标窗口',command=self.schedule_capture)
        self.capture_button.pack(side='left',padx=8)
        ttk.Button(row,text='撤回上一个点',command=self.undo).pack(side='right')
        self.canvas = tk.Canvas(self.window,background='#e2e8f0',highlightthickness=0)
        self.canvas.pack(fill='both',expand=True,padx=12)
        self.canvas.bind('<Button-1>',self.point)
        self.canvas.bind('<Configure>',lambda event:self.draw())
        ttk.Label(self.window,textvariable=self.status,wraplength=850).pack(fill='x',padx=12,pady=8)
        ttk.Button(self.window,text='保存本地证据',command=self.save).pack(side='right',padx=12,pady=12)
        self.window.protocol('WM_DELETE_WINDOW',self.close)

    def schedule_capture(self):
        self.capture_button.configure(state='disabled')
        self.status.set('3秒后采集：请自行切回选定窗口并显示对应页面')
        self.timer = self.window.after(3000,self.capture)

    def capture(self):
        self.timer = None
        try:
            if not foreground_matches(self.target):
                raise ValueError('目标未在前台或身份变化，未采集任何画面')
            from PIL import ImageGrab
            rect = client_rect(self.target.hwnd)
            x,y,width,height = rect
            if self.size and self.size!=(width,height):
                raise ValueError('窗口客户区尺寸改变，请关闭向导后重新校准')
            image = ImageGrab.grab(bbox=(x,y,x+width,y+height),all_screens=True)
            if not foreground_matches(self.target,(width,height)):
                raise ValueError('采集期间目标失焦，画面已丢弃')
            self.size, self.image = (width,height),image
            self.directory.mkdir(parents=True,exist_ok=True)
            page = int(self.page.get()[1])-1
            path = self.directory/f'page-{page+1}-{time.time_ns()}.png'
            image.save(path)
            self.pages[page]={'image':str(path),'sha256':sha256(path),'labels_verified':False}
            self.status.set(f'已采集第{page+1}页 · 下一点：{POINT_NAMES[len(self.points)] if len(self.points)<12 else "坐标已齐，尚未验证动作"}')
            self.draw()
        except Exception as exc:
            self.status.set(str(exc))
        finally:
            if not self.closed: self.capture_button.configure(state='normal')

    def draw(self):
        if self.closed or self.image is None: return
        from PIL import ImageTk
        width,height=max(1,self.canvas.winfo_width()),max(1,self.canvas.winfo_height())
        self.scale=min(width/self.image.width,height/self.image.height)
        size=(max(1,int(self.image.width*self.scale)),max(1,int(self.image.height*self.scale)))
        self.photo=ImageTk.PhotoImage(self.image.resize(size),master=self.window)
        self.canvas.delete('all')
        self.canvas.create_image(0,0,image=self.photo,anchor='nw')
        for index,(x,y) in enumerate(self.points):
            px,py=x*size[0],y*size[1]
            self.canvas.create_oval(px-5,py-5,px+5,py+5,fill='#0f766e',outline='white')
            self.canvas.create_text(px+10,py-10,text=str(index+1),fill='#b91c1c',font=('Arial',12,'bold'))

    def point(self,event):
        if self.image is None or len(self.points)>=12: return
        x,y=event.x/(self.image.width*self.scale),event.y/(self.image.height*self.scale)
        if 0<=x<=1 and 0<=y<=1:
            self.points.append((x,y))
            self.status.set(f'坐标 {len(self.points)}/12 · '+(f'下一点：{POINT_NAMES[len(self.points)]}' if len(self.points)<12 else '尚未验证页码规则与选区/扫弦动作'))
            self.draw()

    def undo(self):
        if self.points: self.points.pop()
        self.draw()
        self.status.set(f'坐标 {len(self.points)}/12 · 下一点：{POINT_NAMES[len(self.points)]}')

    def save(self):
        if not self.pages:
            self.status.set('没有目标截图，未保存')
            return
        atomic_json(self.directory/'evidence.json',{'schema':1,'target':asdict(self.target),'client_size':self.size,
                    'points':self.points,'point_order':POINT_NAMES,'pages':self.pages,
                    'verified':False,'evidence_only':True,'missing_pages':[p+1 for p in range(4) if p not in self.pages]})
        self.status.set('本地证据已保存。四页标签/动作未验收，吉他自动演奏保持禁用。')

    def close(self):
        self.closed=True
        if self.timer: self.window.after_cancel(self.timer)
        self.window.destroy()
