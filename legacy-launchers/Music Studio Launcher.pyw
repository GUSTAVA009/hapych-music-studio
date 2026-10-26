# Music Studio desktop launcher for Windows. Double-click the desktop shortcut.
import os
import subprocess
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
PROGRAM = APP / "studio_server.py"
PYW = ROOT / "ACE-Step-1.5" / ".venv" / "Scripts" / "pythonw.exe"
LOG = APP / "launcher-errors.log"
URL = "http://127.0.0.1:7870"

def responding():
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(URL + "/api/health", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False

def alert(text):
    try:
        import tkinter as tk
        from tkinter import messagebox
        window = tk.Tk()
        window.withdraw()
        messagebox.showerror("Music Studio", text)
        window.destroy()
    except Exception:
        pass

if not responding():
    if not PYW.is_file() or not PROGRAM.is_file():
        alert("Не найдены файлы студии. Проверь папку Music Studio.")
    else:
        with LOG.open("a", encoding="utf-8") as log:
            subprocess.Popen(
                [str(PYW), str(PROGRAM)], cwd=str(APP),
                stdout=log, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        for _ in range(110):
            if responding():
                break
            time.sleep(0.3)
if responding():
    webbrowser.open(URL)
else:
    alert("Интерфейс не запустился. Журнал: Music Studio\\app\\launcher-errors.log")
