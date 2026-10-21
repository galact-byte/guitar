"""仅打开工具自己的测试窗口并截图，不绑定或操作游戏。"""
import argparse
import ctypes
from pathlib import Path
import sys
import tkinter as tk

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from guitar_player.app import App
from guitar_player.contracts import Note, Transcription
from guitar_player.storage import DATA, atomic_json, read_json


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--transcription',type=Path)
    parser.add_argument('--output',type=Path,default=DATA/'verification/ui')
    args=parser.parse_args()
    from PIL import ImageGrab
    ctypes.windll.user32.SetProcessDPIAware()
    args.output.mkdir(parents=True,exist_ok=True)
    source=Transcription.from_dict(read_json(args.transcription)) if args.transcription else Transcription(10.,(Note(0.,1.,60,80),),(),{})
    records=[]
    for width,height,scaling in ((760,720,None),(960,720,4/3),(960,800,5/3),(1100,900,2.)):
        root=tk.Tk()
        if scaling: root.tk.call('tk','scaling',scaling)
        app=App(root,testing=True)
        try:
            root.geometry(f'{width}x{height}')
            root.attributes('-topmost',True)
            app.accept_transcription(source)
            app.song.set('潮鸣 · 整曲验证')
            root.update()
            root.after(150,root.quit)
            root.mainloop()
            x,y=root.winfo_rootx(),root.winfo_rooty()
            path=args.output/f'keyboard-{width}x{height}.png'
            ImageGrab.grab(bbox=(x,y,x+root.winfo_width(),y+root.winfo_height()),all_screens=True).save(path)
            controls={}
            for name in ('select_button','process_button','preview_button','play_button','pause_button','stop_button','status_label','detail_label','footer','log_button'):
                widget=getattr(app,name)
                bounds=(widget.winfo_rootx()-x,widget.winfo_rooty()-y,widget.winfo_width(),widget.winfo_height())
                assert widget.winfo_ismapped() and bounds[0]>=0 and bounds[1]>=0
                assert bounds[0]+bounds[2]<=root.winfo_width() and bounds[1]+bounds[3]<=root.winfo_height(),(name,bounds)
                controls[name]=bounds
            records.append({'image':str(path),'size':(root.winfo_width(),root.winfo_height()),
                            'tk_scaling':float(root.tk.call('tk','scaling')),'controls':controls,'synthetic_game_input':False})
        finally: app.close()
    atomic_json(args.output/'report.json',records)
    print(f'{len(records)} UI captures and bounds checks passed; no game input')


if __name__=='__main__': main()
