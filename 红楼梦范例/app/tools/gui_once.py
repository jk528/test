# -*- coding: utf-8 -*-
"""一次调用内完成：起 vite + app.exe → 等待窗口 → 按步骤截图/点击 → 退栈。

步骤语法（按顺序执行）：
  wait:N          等待 N 秒
  shot:NAME       截图到 .temp/gui_NAME.png
  click:X,Y       在物理坐标 (X,Y) 点击（相对屏幕）
  cssclick:X,Y    在 CSS 像素坐标 (X,Y) 点击（自动换算物理坐标）
报告：.temp/gui_once_report.txt
"""
import ctypes, io, os, socket, subprocess, sys, time
from ctypes import wintypes

APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TEMP = os.path.join(APP, ".temp")
NODE = r"C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2-3\node.exe"
VITE = os.path.join(APP, "node_modules", "vite", "bin", "vite.js")
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
CREATE_NEW_PROCESS_GROUP = 0x00000200

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

L = []
def log(s):
    L.append(s)


def port_open(port):
    for fam, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            s = socket.socket(fam, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((host, port))
            s.close()
            return True
        except Exception:
            try:
                s.close()
            except Exception:
                pass
    return False


def find_window():
    hits = []
    def cb(hwnd, lparam):
        if not u32.IsWindowVisible(hwnd):
            return True
        n = u32.GetWindowTextLengthW(hwnd)
        if n <= 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        u32.GetWindowTextW(hwnd, buf, n + 1)
        if TITLE_KEY in buf.value:
            hits.append(hwnd)
        return True
    u32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(cb), 0)
    return hits[0] if hits else None


def grab(hwnd, w, h):
    hdc = u32.GetWindowDC(hwnd)
    mem = g32.CreateCompatibleDC(hdc)
    bm = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mem, bm)
    u32.PrintWindow(hwnd, mem, 2)
    bi = BITMAPINFO()
    bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.bmiHeader.biWidth = w
    bi.bmiHeader.biHeight = -h
    bi.bmiHeader.biPlanes = 1
    bi.bmiHeader.biBitCount = 32
    bi.bmiHeader.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mem, bm, 0, h, buf, ctypes.byref(bi), 0)
    g32.DeleteObject(bm)
    g32.DeleteDC(mem)
    u32.ReleaseDC(hwnd, hdc)
    return buf.raw


def grab_screen(x, y, w, h):
    sd = u32.GetDC(0)
    mem = g32.CreateCompatibleDC(sd)
    bm = g32.CreateCompatibleBitmap(sd, w, h)
    g32.SelectObject(mem, bm)
    g32.BitBlt(mem, 0, 0, w, h, sd, x, y, 0x00CC0020)
    bi = BITMAPINFO()
    bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.bmiHeader.biWidth = w
    bi.bmiHeader.biHeight = -h
    bi.bmiHeader.biPlanes = 1
    bi.bmiHeader.biBitCount = 32
    bi.bmiHeader.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mem, bm, 0, h, buf, ctypes.byref(bi), 0)
    g32.DeleteObject(bm)
    g32.DeleteDC(mem)
    u32.ReleaseDC(0, sd)
    return buf.raw


def to_img(raw, w, h):
    from PIL import Image
    return Image.frombuffer("RGBA", (w, h), raw, "raw", "BGRA", 0, 1).convert("RGB")


def geometry(hwnd):
    dpi = 96
    try:
        dpi = u32.GetDpiForWindow(hwnd) or 96
    except Exception:
        pass
    s = dpi / 96.0
    pt = wintypes.POINT(0, 0)
    u32.ClientToScreen(hwnd, ctypes.byref(pt))
    cr = wintypes.RECT()
    u32.GetClientRect(hwnd, ctypes.byref(cr))
    wr = wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(wr))
    return (dpi, s, pt.x, pt.y, cr.right, cr.bottom,
            wr.left, wr.top, wr.right - wr.left, wr.bottom - wr.top)


HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040


def focus_window(hwnd):
    """强制把窗口提到前台（绕开前台锁）。返回 (前台hwnd, 是否成功)。"""
    u32.ShowWindow(hwnd, 9)  # SW_RESTORE
    flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
    u32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
    time.sleep(0.25)
    u32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags)

    fg = u32.GetForegroundWindow()
    if fg != hwnd:
        # AttachThreadInput 解锁前台切换
        tid_fg = u32.GetWindowThreadProcessId(fg, None)
        tid_me = ctypes.windll.kernel32.GetCurrentThreadId()
        u32.AttachThreadInput(tid_fg, tid_me, True)
        u32.BringWindowToTop(hwnd)
        u32.SetForegroundWindow(hwnd)
        u32.SetFocus(hwnd)
        u32.AttachThreadInput(tid_fg, tid_me, False)
        time.sleep(0.35)
    fg2 = u32.GetForegroundWindow()
    return fg2, (fg2 == hwnd)


def click(px, py):
    u32.SetCursorPos(int(px), int(py))
    time.sleep(0.2)
    # 诊断：该屏幕坐标最顶层的窗口
    pt = wintypes.POINT(int(px), int(py))
    top = u32.WindowFromPoint(pt)
    root = u32.GetAncestor(top, 2)  # GA_ROOT
    log(f"    point=({int(px)},{int(py)}) top_hwnd={top} root_hwnd={root}")
    u32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.08)
    u32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.8)


def main():
    steps = sys.argv[1:]
    procs = []
    try:
        # 1) vite
        fv = io.open(os.path.join(TEMP, "vite_dev.log"), "wb", buffering=0)
        pv = subprocess.Popen([NODE, VITE, "--port", "1420", "--strictPort"], cwd=APP,
                              stdout=fv, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                              creationflags=CREATE_NEW_PROCESS_GROUP)
        procs.append(pv)
        t0 = time.time()
        while time.time() - t0 < 45:
            if port_open(1420):
                break
            if pv.poll() is not None:
                break
            time.sleep(0.7)
        log(f"vite up={port_open(1420)} pid={pv.pid} in {time.time()-t0:.1f}s")

        # 2) app.exe
        fa = io.open(os.path.join(TEMP, "app_run.log"), "wb", buffering=0)
        pa = subprocess.Popen([EXE], cwd=os.path.dirname(EXE),
                              stdout=fa, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                              creationflags=CREATE_NEW_PROCESS_GROUP)
        procs.append(pa)
        log(f"app.exe pid={pa.pid}")

        hwnd = None
        t0 = time.time()
        while time.time() - t0 < 60:
            hwnd = find_window()
            if hwnd:
                break
            time.sleep(0.8)
        log(f"hwnd={hwnd} after {time.time()-t0:.1f}s")
        if not hwnd:
            log("窗口未出现，放弃")
            return

        dpi, s, ox, oy, cw, ch, wl, wt, ww, wh = geometry(hwnd)
        log(f"dpi={dpi} scale={s:.4f}")
        log(f"client origin(phys)=({ox},{oy}) client size(phys)={cw}x{ch}")
        log(f"css viewport = {cw/s:.1f} x {ch/s:.1f}")
        log(f"window rect(phys)=({wl},{wt},{ww},{wh})")

        fg, ok = focus_window(hwnd)
        log(f"focus: foreground={fg} ok={ok}")
        time.sleep(1.0)

        for st in steps:
            kind, _, arg = st.partition(":")
            if kind == "wait":
                time.sleep(float(arg))
                log(f"wait {arg}s")
            elif kind == "shot":
                raw = grab(hwnd, ww, wh)
                img = to_img(raw, ww, wh)
                small = img.resize((80, 50))
                ncol = len(small.getcolors(80 * 50) or [])
                path = os.path.join(TEMP, f"gui_{arg}.png")
                img.save(path)
                log(f"shot {arg}: {ww}x{wh} colors={ncol}")
                if ncol <= 3:
                    log("  PrintWindow 空白 → 屏幕抓取")
                    img = to_img(grab_screen(wl, wt, ww, wh), ww, wh)
                    img.save(path)
                    log(f"  screen colors={len(img.resize((80,50)).getcolors(4000) or [])}")
                px = img.load()
                for k, (a, b) in {"topbar": (240, 26), "tab_row": (46, 72 + 26),
                                  "mid_sidebar": (140, 300), "content": (700, 300)}.items():
                    if a < ww and b < wh:
                        log(f"  px {k}({a},{b}) = {px[a, b]}")
            elif kind == "click":
                x, y = (int(v) for v in arg.split(","))
                f2, ok2 = focus_window(hwnd)
                click(x, y)
                log(f"click phys=({x},{y}) refocus_ok={ok2}")
            elif kind == "cssclick":
                cx, cy = (float(v) for v in arg.split(","))
                x, y = ox + cx * s, oy + cy * s
                f2, ok2 = focus_window(hwnd)
                click(x, y)
                log(f"cssclick css=({cx},{cy}) -> phys=({x:.0f},{y:.0f}) refocus_ok={ok2}")
            elif kind == "wheel":
                n = int(arg)
                for _ in range(abs(n)):
                    u32.mouse_event(0x0800, 0, 0, 120 if n > 0 else -120, 0)
                    time.sleep(0.05)
                time.sleep(0.5)
                log(f"wheel {n}")
            else:
                log(f"未知步骤 {st}")
    finally:
        for p in procs:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                           capture_output=True)
        log("stack killed")
        io.open(os.path.join(TEMP, "gui_once_report.txt"), "w", encoding="utf-8",
                newline="").write("\n".join(L))


main()
