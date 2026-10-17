# -*- coding: utf-8 -*-
"""一次调用内：启动 app.exe → 等待窗口 → 截图 → 保持窗口（不杀）。
vite 假定已在 1420 端口运行。"""
import ctypes, os, subprocess, sys, time
from ctypes import wintypes

APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TEMP = os.path.join(APP, ".temp")
EXE = os.path.join(APP, "src-tauri", "target", "debug", "app.exe")
TITLE_KEY = "红楼梦阅读分析"

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]

class RGBQUAD(ctypes.Structure):
    _fields_ = [("rgbBlue", ctypes.c_byte), ("rgbGreen", ctypes.c_byte),
                ("rgbRed", ctypes.c_byte), ("rgbReserved", ctypes.c_byte)]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", RGBQUAD * 1)]

def find_hwnd(key, timeout=30):
    def cb(h, r):
        buf = ctypes.create_unicode_buffer(512)
        u32.GetWindowTextW(h, buf, 512)
        if key in buf.value and u32.IsWindowVisible(h):
            r.append(h)
        return True
    P = wintypes.LPARAM
    H = wintypes.HWND
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, H, P)
    t0 = time.time()
    while time.time() - t0 < timeout:
        found = []
        u32.EnumWindows(WNDENUMPROC(lambda h, p: cb(h, found)), 0)
        if found:
            return found[0]
        time.sleep(0.5)
    return None

def shot(hwnd, path):
    rect = wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    hdc = u32.GetWindowDC(hwnd)
    mem = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    old = g32.SelectObject(mem, bmp)
    ok = u32.PrintWindow(hwnd, mem, 2)
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bmi), 0)
    data_size = w * h * 4
    file_size = 54 + data_size
    with open(path, "wb") as f:
        f.write(b"BM")
        f.write(file_size.to_bytes(4, "little"))
        f.write((0).to_bytes(4, "little"))
        f.write((54).to_bytes(4, "little"))
        f.write((40).to_bytes(4, "little"))
        f.write(w.to_bytes(4, "little") + h.to_bytes(4, "little", signed=True))
        f.write((1).to_bytes(2, "little") + (32).to_bytes(2, "little"))
        f.write((0).to_bytes(4, "little") + data_size.to_bytes(4, "little"))
        f.write((2835).to_bytes(4, "little") * 2)
        f.write((0).to_bytes(4, "little") * 2)
        f.write(buf.raw)
    g32.SelectObject(mem, old)
    g32.DeleteObject(bmp)
    g32.DeleteDC(mem)
    u32.ReleaseDC(hwnd, hdc)
    return ok

os.makedirs(TEMP, exist_ok=True)
# 启动 app.exe（不等待退出）
proc = subprocess.Popen([EXE])
print(f"app.exe 已启动 PID={proc.pid}，等待窗口...")
hwnd = find_hwnd(TITLE_KEY, timeout=30)
if not hwnd:
    print("窗口未找到")
    sys.exit(1)
# 窗口置前
u32.ShowWindow(hwnd, 9)  # SW_RESTORE
u32.SetForegroundWindow(hwnd)
time.sleep(8)  # 等页面 + Monaco 加载大文本
for name in ["beauty"]:
    rect = wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(rect))
    print(f"窗口: {rect.right-rect.left}x{rect.bottom-rect.top}")
    p = os.path.join(TEMP, f"gui_{name}.bmp")
    ok = shot(hwnd, p)
    print(f"截图: PrintWindow={ok}, saved={p}")
print("DONE")
