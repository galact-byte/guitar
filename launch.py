"""本地桌面入口；错误同时写入日志并弹窗，不隐式安装或提权。"""
from pathlib import Path
import os
import sys
import traceback

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))


def main():
    try:
        from guitar_player.app import main as run
        run()
        return 0
    except Exception:
        text = traceback.format_exc()
        path = ROOT/'data/logs/startup.log'
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('a',encoding='utf-8') as stream: stream.write(text+'\n')
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,f'工具未能启动，请检查现有本地环境。\n日志：{path}\n\n{text[-1200:]}','启动失败',0x10)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
