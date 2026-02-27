import ctypes
import ctypes.wintypes
import win32gui
import win32con
import win32api
import win32process
import time
import threading
import math
import webbrowser
import keyboard
import pyautogui
import pydirectinput
import tkinter as tk
from tkinter import Canvas
import ctypes
import os, sys
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("moris.macro")

def _resource_path(filename):
    """Works for both .py script and PyInstaller exe."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

state = {
    "running": False,
    "stop": False,
    "minigame": False,
    "holding": False,
    "debug": True,
    "cycles": 0,
}

SCAN_GREEN_X = 23
SCAN_GREEN_Y = 282
SCAN_RED_X = 479
SCAN_RED_Y = 75

FISH_BAR_LEFT = 260
FISH_BAR_RIGHT = 695
FISH_BAR_Y = 492
FISH_COLOR_TOLERANCE = 10
CONTROL_BAR_WIDTH = 55

OVERLAY_OFFSET_Y = 30
OVERLAY_HEIGHT = 12

MINIGAME_TIMEOUT_X = 701
MINIGAME_TIMEOUT_Y = 509
MINIGAME_TIMEOUT_COLOR = (11, 12, 12)

overlay_win = None
overlay_canvas = None
bar_rect_id = None
fish_rect_id = None
_tk_root = None

_gui_instance = None

C = {
    "accent":        "#89dfff",
    "bg":            "#121212",
    "panel_bg":      "#1c1c1c",
    "title_bg":      "#1a1a1a",
    "border":        "#2a2a2a",
    "running":       "#4ade80",
    "stopped":       "#f87171",
    "text_dim":      "#555555",
    "text_mid":      "#888888",
    "text_bright":   "#cccccc",
    "btn_blue_bg":   "#0d1e2a",
    "btn_blue_fg":   "#89dfff",
    "btn_blue_brd":  "#1a3a4a",
    "btn_dark_bg":   "#202020",
    "btn_dark_fg":   "#777777",
    "btn_dark_brd":  "#2e2e2e",
    "btn_disc_bg":   "#1e2040",
    "btn_disc_fg":   "#7289da",
    "btn_disc_brd":  "#2a2e55",
    "btn_green_bg":  "#0f2a1c",
    "btn_green_fg":  "#4ade80",
    "btn_green_brd": "#1e4830",
}

FONT      = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_SM   = ("Segoe UI", 7, "bold")
RADIUS    = 8

WIN_W = 510
WIN_H = 225
WIN_R = 12   # window corner radius



def resize_roblox_window():
    titles = ["Roblox", "RobloxPlayerBeta.exe", "RobloxPlayer.exe"]
    hwnd = None
    for title in titles:
        if title.endswith(".exe"):
            found = []
            def callback(h, extra):
                _, pid = win32process.GetWindowThreadProcessId(h)
                try:
                    proc = win32api.OpenProcess(0x0410, False, pid)
                    name = win32process.GetModuleFileNameEx(proc, 0)
                    if title in name and win32gui.IsWindowVisible(h):
                        extra.append(h)
                except Exception:
                    pass
            win32gui.EnumWindows(callback, found)
            if found:
                hwnd = found[0]
                break
        else:
            hwnd = win32gui.FindWindow(None, title)
            if hwnd:
                break
    if not hwnd:
        return
    try:
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.1)
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        WS_CAPTION = 0x00C00000
        if not (style & WS_CAPTION):
            pyautogui.press('f11')
            time.sleep(0.3)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        new_style = (style | win32con.WS_CAPTION | win32con.WS_SYSMENU
                     | win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX
                     | win32con.WS_THICKFRAME)
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, new_style)
        win32gui.SetWindowPos(hwnd, None, -7, 0, 974, 630,
                              win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED)
    except Exception:
        pass
    return hwnd



def scroll_down():
    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120, 0)

def scroll_up():
    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120, 0)



def is_light_green_scan(r, g, b):
    return g > 150 and g > r * 1.4 and g > b * 1.4

def is_light_red(r, g, b):
    return r > 150 and r > g * 1.4 and r > b * 1.4

def is_fish(r, g, b):
    return b > 130 and b > r * 1.3 and b >= g and g > r

def is_control_bar_grey(r, g, b):
    return abs(r-g) < 25 and abs(g-b) < 25 and abs(r-b) < 25 and r > 150

def is_control_bar_green(r, g, b):
    return g > 150 and g > r * 1.4 and g > b * 1.4 and b < 160

def is_control_bar(r, g, b):
    return is_control_bar_grey(r, g, b) or is_control_bar_green(r, g, b)

def scan_row():
    screenshot = pyautogui.screenshot(region=(
        FISH_BAR_LEFT, FISH_BAR_Y, FISH_BAR_RIGHT - FISH_BAR_LEFT, 1))
    pixels = screenshot.load()
    width = FISH_BAR_RIGHT - FISH_BAR_LEFT
    fish_left = fish_right = bar_left = bar_right = None
    for i in range(width):
        r, g, b = pixels[i, 0]
        if fish_left is None and is_fish(r, g, b):
            fish_left = FISH_BAR_LEFT + i
        if bar_left is None and not is_fish(r, g, b) and is_control_bar(r, g, b):
            bar_left = FISH_BAR_LEFT + i
    for i in range(width - 1, -1, -1):
        r, g, b = pixels[i, 0]
        if fish_right is None and is_fish(r, g, b):
            fish_right = FISH_BAR_LEFT + i
        if bar_right is None and not is_fish(r, g, b) and is_control_bar(r, g, b):
            bar_right = FISH_BAR_LEFT + i
    if bar_left is not None and bar_right is not None:
        if bar_right - bar_left > CONTROL_BAR_WIDTH * 1.5:
            bar_right = bar_left + CONTROL_BAR_WIDTH
    return bar_left, bar_right, fish_left, fish_right



def mouse_down():
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    state["holding"] = True

def mouse_up():
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    state["holding"] = False



def create_overlay():
    global overlay_win, overlay_canvas, bar_rect_id, fish_rect_id, _tk_root
    screen_w = pyautogui.size()[0]
    screen_h = pyautogui.size()[1]
    ready = threading.Event()
    def _tk_thread():
        global overlay_win, overlay_canvas, bar_rect_id, fish_rect_id, _tk_root
        _tk_root = tk.Tk()
        _tk_root.withdraw()
        overlay_win = tk.Toplevel(_tk_root)
        overlay_win.overrideredirect(True)
        overlay_win.attributes("-topmost", True)
        overlay_win.attributes("-transparentcolor", "black")
        overlay_win.geometry(f"{screen_w}x{screen_h}+0+0")
        overlay_win.configure(bg="black")
        overlay_win.wm_attributes("-alpha", 1.0)
        overlay_canvas = Canvas(overlay_win, bg="black", highlightthickness=0,
                                width=screen_w, height=screen_h)
        overlay_canvas.pack()
        bar_rect_id  = overlay_canvas.create_rectangle(0,0,0,0, outline="#00ff00", width=2, fill="")
        fish_rect_id = overlay_canvas.create_rectangle(0,0,0,0, outline="#00aaff", width=2, fill="")
        ready.set()
        try:
            _tk_root.mainloop()
        except Exception:
            pass
    threading.Thread(target=_tk_thread, daemon=True).start()
    ready.wait(timeout=3)

def destroy_overlay():
    global overlay_win, overlay_canvas, bar_rect_id, fish_rect_id, _tk_root
    root_ref = _tk_root
    if root_ref:
        try:
            root_ref.after(0, root_ref.destroy)
        except Exception:
            pass
    overlay_win = overlay_canvas = bar_rect_id = fish_rect_id = _tk_root = None

def update_overlay(bar_l, bar_r, fish_l, fish_r):
    if overlay_canvas is None or _tk_root is None:
        return
    oy = FISH_BAR_Y - OVERLAY_OFFSET_Y
    canvas, bid, fid = overlay_canvas, bar_rect_id, fish_rect_id
    def _update():
        try:
            canvas.coords(bid,
                bar_l or 0, oy if bar_l else 0,
                bar_r or 0, (oy + OVERLAY_HEIGHT) if bar_l else 0)
            canvas.coords(fid,
                fish_l or 0, oy if fish_l else 0,
                fish_r or 0, (oy + OVERLAY_HEIGHT) if fish_l else 0)
        except Exception:
            pass
    try:
        _tk_root.after(0, _update)
    except Exception:
        pass



def is_timeout_color_present():
    r, g, b = pyautogui.pixel(MINIGAME_TIMEOUT_X, MINIGAME_TIMEOUT_Y)
    tr, tg, tb = MINIGAME_TIMEOUT_COLOR
    return abs(r-tr) <= 5 and abs(g-tg) <= 5 and abs(b-tb) <= 5



def minigame_loop():
    while state["minigame"] and not state["stop"]:
        bar_l, bar_r, fish_l, fish_r = scan_row()
        update_overlay(bar_l, bar_r, fish_l, fish_r)
        if all(v is not None for v in (bar_l, bar_r, fish_l, fish_r)):
            if (bar_l + bar_r) / 2 < (fish_l + fish_r) / 2:
                if not state["holding"]: mouse_down()
            else:
                if state["holding"]: mouse_up()
        time.sleep(0.008)
    if state["holding"]: mouse_up()
    destroy_overlay()

def minigame_timeout_watcher(restart_callback):
    time.sleep(2)
    while state["minigame"] and not state["stop"]:
        if not is_timeout_color_present():
            state["minigame"] = False
            state["cycles"] += 1
            push_state_to_gui()
            destroy_overlay()
            pydirectinput.press('1'); time.sleep(0.1)
            pydirectinput.press('4'); time.sleep(0.2)
            threading.Thread(target=restart_callback, daemon=True).start()
            return
        time.sleep(0.5)

def start_minigame(restart_callback):
    state["minigame"] = True
    create_overlay()
    threading.Thread(target=minigame_loop, daemon=True).start()
    threading.Thread(target=minigame_timeout_watcher, args=(restart_callback,), daemon=True).start()



def run_from_green_scan():
    if not state["stop"]:
        time.sleep(0.3); pydirectinput.click()
        while not state["stop"]:
            r, g, b = pyautogui.pixel(SCAN_GREEN_X, SCAN_GREEN_Y)
            if is_light_green_scan(r, g, b):
                pydirectinput.click(); break
    if not state["stop"]: time.sleep(2)
    if not state["stop"]: time.sleep(1)
    if not state["stop"]:
        while not state["stop"]:
            r, g, b = pyautogui.pixel(SCAN_RED_X, SCAN_RED_Y)
            if is_light_red(r, g, b):
                time.sleep(0.1); pydirectinput.click(); break
    if not state["stop"]:
        time.sleep(2)
        start_minigame(run_from_green_scan)

def run_macro():
    if state["running"]: return
    state["running"] = True
    state["stop"] = False
    push_state_to_gui()
    resize_roblox_window()
    time.sleep(1.5)
    pyautogui.moveTo(479, 299); time.sleep(0.1)
    for _ in range(17):
        if state["stop"]: break
        scroll_up(); time.sleep(0.05)
    for _ in range(6):
        if state["stop"]: break
        scroll_down(); time.sleep(0.05)
    if not state["stop"]: pydirectinput.press('1'); time.sleep(0.1)
    if not state["stop"]: pydirectinput.press('4'); time.sleep(0.2)
    run_from_green_scan()



def on_f1():
    if state["running"] or state["minigame"]: on_f2()
    else: threading.Thread(target=run_macro, daemon=True).start()

def on_f2():
    state["stop"] = True
    state["running"] = False
    state["minigame"] = False
    if state["holding"]: mouse_up()
    push_state_to_gui()
    destroy_overlay()
    resize_roblox_window()



def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return '#{:02x}{:02x}{:02x}'.format(int(r), int(g), int(b))



class RoundedFrame(tk.Canvas):
    def __init__(self, parent, bg=None, border_color=None, radius=RADIUS, **kwargs):
        self._bg     = bg           or C["panel_bg"]
        self._brd    = border_color or C["border"]
        self._radius = radius
        super().__init__(parent, bg=C["bg"], highlightthickness=0, bd=0, **kwargs)
        self._frame = tk.Frame(self, bg=self._bg, highlightthickness=0, bd=0)
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, e):
        self.delete("all")
        w, h, r = e.width, e.height, self._radius
        self._rrect(0, 0, w, h, r, fill=self._brd, outline="")
        self._rrect(1, 1, w-1, h-1, max(r-1, 1), fill=self._bg, outline="")
        self._frame.place(x=1, y=1, width=w-2, height=h-2)

    def _rrect(self, x1, y1, x2, y2, r, **kw):
        r = max(r, 1)
        self.create_arc(x1,     y1,     x1+r*2, y1+r*2, start=90,  extent=90,  style="pieslice", **kw)
        self.create_arc(x2-r*2, y1,     x2,     y1+r*2, start=0,   extent=90,  style="pieslice", **kw)
        self.create_arc(x1,     y2-r*2, x1+r*2, y2,     start=180, extent=90,  style="pieslice", **kw)
        self.create_arc(x2-r*2, y2-r*2, x2,     y2,     start=270, extent=90,  style="pieslice", **kw)
        self.create_rectangle(x1+r, y1,   x2-r, y2,   **kw)
        self.create_rectangle(x1,   y1+r, x2,   y2-r, **kw)

    @property
    def inner(self):
        return self._frame



BTN_RADIUS = 6

class FlatButton(tk.Canvas):
    def __init__(self, parent, text="",
                 bg=None, fg=None, border_color=None,
                 hover_bg=None, hover_fg=None, hover_border=None,
                 command=None, **kwargs):
        self._norm_bg  = bg           or C["btn_dark_bg"]
        self._norm_fg  = fg           or C["btn_dark_fg"]
        self._norm_brd = border_color or C["btn_dark_brd"]
        self._hov_bg   = hover_bg     or self._norm_bg
        self._hov_fg   = hover_fg     or "#bbbbbb"
        self._hov_brd  = hover_border or "#3a3a3a"
        self._cmd      = command
        self._hovered  = False
        self._pressed  = False
        self._text     = text

        kwargs.pop("highlightthickness", None)
        kwargs.pop("bd", None)
        super().__init__(parent, highlightthickness=0, bd=0,
                         bg=C["panel_bg"], cursor="hand2", **kwargs)

        self.bind("<Configure>",        self._draw)
        self.bind("<Enter>",            self._enter)
        self.bind("<Leave>",            self._leave)
        self.bind("<ButtonPress-1>",    self._press)
        self.bind("<ButtonRelease-1>",  self._release)

    def _draw(self, e=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 2:
            return
        bg  = self._hov_bg  if self._hovered else self._norm_bg
        fg  = self._hov_fg  if self._hovered else self._norm_fg
        brd = self._hov_brd if self._hovered else self._norm_brd
        r   = BTN_RADIUS
        self._rrect_filled(0, 0, w, h, r, bg, brd)
        self.create_text(w//2, h//2, text=self._text, fill=fg,
                         font=FONT_BOLD, anchor="center")

    def _rrect_filled(self, x1, y1, x2, y2, r, fill, outline):
        r = max(r, 1)
        bx1, by1, bx2, by2 = x1+1, y1+1, x2-1, y2-1
        self.create_arc(bx1,      by1,      bx1+r*2, by1+r*2, start=90,  extent=90,  style="pieslice", fill=fill, outline=fill)
        self.create_arc(bx2-r*2,  by1,      bx2,     by1+r*2, start=0,   extent=90,  style="pieslice", fill=fill, outline=fill)
        self.create_arc(bx1,      by2-r*2,  bx1+r*2, by2,     start=180, extent=90,  style="pieslice", fill=fill, outline=fill)
        self.create_arc(bx2-r*2,  by2-r*2,  bx2,     by2,     start=270, extent=90,  style="pieslice", fill=fill, outline=fill)
        self.create_rectangle(bx1+r-1, by1, bx2-r+1, by2, fill=fill, outline=fill)
        self.create_rectangle(bx1, by1+r-1, bx2, by2-r+1, fill=fill, outline=fill)
        self.create_arc(bx1,      by1,      bx1+r*2, by1+r*2, start=90,  extent=90,  style="arc", outline=outline)
        self.create_arc(bx2-r*2,  by1,      bx2,     by1+r*2, start=0,   extent=90,  style="arc", outline=outline)
        self.create_arc(bx1,      by2-r*2,  bx1+r*2, by2,     start=180, extent=90,  style="arc", outline=outline)
        self.create_arc(bx2-r*2,  by2-r*2,  bx2,     by2,     start=270, extent=90,  style="arc", outline=outline)
        self.create_line(bx1+r, by1,  bx2-r, by1,  fill=outline)
        self.create_line(bx1+r, by2,  bx2-r, by2,  fill=outline)
        self.create_line(bx1,   by1+r, bx1,  by2-r, fill=outline)
        self.create_line(bx2,   by1+r, bx2,  by2-r, fill=outline)

    def _rrect(self, x1, y1, x2, y2, r, **kw):
        pass

    def _refresh(self):
        self._draw()

    def _enter(self, e):  self._hovered = True;  self._draw()
    def _leave(self, e):  self._hovered = False; self._pressed = False; self._draw()
    def _press(self, e):  self._pressed = True
    def _release(self, e):
        if self._pressed and self._cmd: self._cmd()
        self._pressed = False

    def set_text(self, text):
        self._text = text
        self._draw()

    def set_active(self, active):
        if active:
            self._norm_bg  = C["btn_green_bg"]
            self._norm_fg  = C["btn_green_fg"]
            self._norm_brd = C["btn_green_brd"]
            self._hov_bg   = "#163a28"
            self._hov_fg   = "#6ef0a0"
            self._hov_brd  = C["btn_green_fg"]
        else:
            self._norm_bg  = C["btn_blue_bg"]
            self._norm_fg  = C["btn_blue_fg"]
            self._norm_brd = C["btn_blue_brd"]
            self._hov_bg   = "#0f2535"
            self._hov_fg   = "#aaeeff"
            self._hov_brd  = C["btn_blue_fg"]
        self._hovered = False
        self._draw()



class MacroGUI:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("moris bloxfruit fishing macro")
        _ico = _resource_path("icon.ico")
        if os.path.exists(_ico):
            self.root.iconbitmap(_ico)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.after(10, self._fix_taskbar)
        self.root.configure(bg=C["bg"])
        self.root.resizable(False, False)

        self.root.geometry(f"{WIN_W}x{WIN_H}+0+630")

        self._drag_ox    = 0
        self._drag_oy    = 0
        self._start_time = None
        self._timer_job  = None

        self._build()
        self._apply_rounded_corners()
        self._start_sync_loop()

    def _fix_taskbar(self):
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            # Hide and show to force taskbar refresh
            self.root.withdraw()
            self.root.after(10, self.root.deiconify)
        except Exception:
            pass

    def _apply_rounded_corners(self):
        self.root.update_idletasks()
        try:
            hwnd = ctypes.windll.user32.GetParent(
                self.root.winfo_id()
            )
            if not hwnd:
                hwnd = self.root.winfo_id()
            rgn = ctypes.windll.gdi32.CreateRoundRectRgn(
                0, 0, WIN_W + 1, WIN_H + 1, WIN_R * 2, WIN_R * 2
            )
            ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)
        except Exception:
            pass


    def _build(self):
        self._build_titlebar()
        body = tk.Frame(self.root, bg=C["bg"])
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        dash_rf = RoundedFrame(body, bg=C["panel_bg"], border_color=C["border"], radius=RADIUS)
        dash_rf.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=(6, 8))
        self._build_dashboard(dash_rf.inner)

        info_rf = RoundedFrame(body, bg=C["panel_bg"], border_color=C["border"], radius=RADIUS)
        info_rf.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=(6, 8))
        self._build_info(info_rf.inner)


    def _build_titlebar(self):
        tb = tk.Frame(self.root, bg=C["title_bg"], height=30)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        left = tk.Frame(tb, bg=C["title_bg"])
        left.pack(side="left", padx=11, fill="y")

        try:
            import base64, io
            from PIL import Image, ImageTk
            _LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAABCGlDQ1BJQ0MgUHJvZmlsZQAAeJxjYGA8wQAELAYMDLl5JUVB7k4KEZFRCuwPGBiBEAwSk4sLGHADoKpv1yBqL+viUYcLcKakFicD6Q9ArFIEtBxopAiQLZIOYWuA2EkQtg2IXV5SUAJkB4DYRSFBzkB2CpCtkY7ETkJiJxcUgdT3ANk2uTmlyQh3M/Ck5oUGA2kOIJZhKGYIYnBncAL5H6IkfxEDg8VXBgbmCQixpJkMDNtbGRgkbiHEVBYwMPC3MDBsO48QQ4RJQWJRIliIBYiZ0tIYGD4tZ2DgjWRgEL7AwMAVDQsIHG5TALvNnSEfCNMZchhSgSKeDHkMyQx6QJYRgwGDIYMZAKbWPz9HbOBQAAABYklEQVR4nM2TvS5EURSF174zg2kkIpSTKDQEGZVIiEY9/mW8hIfQ6oVW1GoeQEnwBkIjMc2IgoxPcdflZEyhILGTm52z9lr77rPOOdJ/i+gGgJLxTkRgLJOUSepIKkkiIjp/OxoQzg3gCJhOagvAPjAPHAKrqSZtkjnPkMclMJvg58ADUAeuzKmn2qJRCQhgBegAY8UfgSrwAuwZGzdnzfWSlBsoSbKxLWPDQBhblFSVdOqtDJnTKg5DkjIXAWqSdiTd+yuiKelR0rXXd643rQEIAeXE5DfgxCNnQBl4Ag7Mqbh2bG7DePnTI+dNGznl9ZzXS4mfE8a2U+2X43m0lV+6IrYkPUu6SI4ac9qpsLtRpvzmjnncDUlnEfEqqQL0SRo3p1v7ecwBjAC3wCuw6y2sJ5xle3MDjBa6b82cB+xDDZgEKgln0Fh/quk5Wc/CD7i9Xn8YR1JExHuvWnoZfzU+AGdsctqaAmbZAAAAAElFTkSuQmCC"
            img = Image.open(io.BytesIO(base64.b64decode(_LOGO_B64))).convert("RGBA")
            self._logo_img = ImageTk.PhotoImage(img)
            tk.Label(left, image=self._logo_img, bg=C["title_bg"]).pack(side="left", padx=(0, 5))
        except Exception:
            pass

        for text, color in [
            ("moris",            C["text_mid"]),
            ("bloxfruit fishing", C["accent"]),
            ("macro",            C["text_mid"]),
        ]:
            tk.Label(left, text=text, bg=C["title_bg"], fg=color,
                     font=FONT_BOLD).pack(side="left")

        right = tk.Frame(tb, bg=C["title_bg"])
        right.pack(side="right", padx=10)

        x_btn = tk.Label(right, text="x", bg=C["title_bg"], fg=C["text_dim"],
                         font=("Segoe UI", 12, "bold"), cursor="hand2", padx=6)
        x_btn.pack(side="right")
        x_btn.bind("<Enter>",    lambda e: x_btn.config(fg="#f87171", bg=C["title_bg"]))
        x_btn.bind("<Leave>",    lambda e: x_btn.config(fg=C["text_dim"], bg=C["title_bg"]))
        x_btn.bind("<Button-1>", lambda e: self._on_close())

        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x")

        for w in [tb, left] + list(left.winfo_children()):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_motion)

    def _drag_start(self, e):
        self._drag_ox = e.x_root - self.root.winfo_x()
        self._drag_oy = e.y_root - self.root.winfo_y()

    def _drag_motion(self, e):
        self.root.geometry(f"+{e.x_root-self._drag_ox}+{e.y_root-self._drag_oy}")


    def _section_header(self, parent, title):
        hdr = tk.Frame(parent, bg=C["panel_bg"])
        hdr.pack(fill="x", padx=10, pady=(8, 0))
        tk.Label(hdr, text=title.upper(), bg=C["panel_bg"],
                 fg=C["text_dim"], font=FONT_SM).pack(side="left")
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=10, pady=(4, 0))

    def _build_dashboard(self, parent):
        self._section_header(parent, "Dashboard")

        rows = tk.Frame(parent, bg=C["panel_bg"])
        rows.pack(fill="both", expand=True, padx=10, pady=6)

        self._status_val = self._stat_row(rows, "Status",       "Stopped",  C["stopped"])
        self._time_val   = self._stat_row(rows, "Time Elapsed", "00:00:00", C["text_bright"])
        self._cycles_val = self._stat_row(rows, "Cycles",       "0",        C["text_bright"])

        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=10)

        btn_row = tk.Frame(parent, bg=C["panel_bg"])
        btn_row.pack(fill="x", padx=10, pady=8)

        self._start_btn = FlatButton(
            btn_row, text="Start (F1)",
            bg=C["btn_blue_bg"], fg=C["btn_blue_fg"], border_color=C["btn_blue_brd"],
            hover_bg="#0f2535", hover_fg="#aaeeff", hover_border=C["btn_blue_fg"],
            command=self._toggle_start, height=36, width=1,
        )
        self._start_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        FlatButton(
            btn_row, text="Reload (F2)",
            bg=C["btn_dark_bg"], fg=C["btn_dark_fg"], border_color=C["btn_dark_brd"],
            hover_bg="#282828", hover_fg="#bbbbbb", hover_border="#3a3a3a",
            command=self._reload, height=36, width=1,
        ).pack(side="left", fill="x", expand=True)

    def _stat_row(self, parent, label, value, val_color):
        row = tk.Frame(parent, bg=C["panel_bg"])
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, bg=C["panel_bg"], fg=C["text_dim"],
                 font=FONT).pack(side="left")
        val = tk.Label(row, text=value, bg=C["panel_bg"], fg=val_color,
                       font=FONT_BOLD)
        val.pack(side="right")
        return val

    def _build_info(self, parent):
        self._section_header(parent, "Info")

        mid = tk.Frame(parent, bg=C["panel_bg"])
        mid.pack(fill="both", expand=True)

        tk.Label(mid, text="made by", bg=C["panel_bg"], fg=C["text_dim"],
                 font=FONT).pack(pady=(10, 2))

        names = tk.Frame(mid, bg=C["panel_bg"])
        names.pack()
        tk.Label(names, text="moris", bg=C["panel_bg"], fg=C["accent"],
                 font=FONT_BOLD).pack(side="left")
        tk.Label(names, text="and", bg=C["panel_bg"], fg=C["text_dim"],
                 font=FONT).pack(side="left")
        tk.Label(names, text="tim", bg=C["panel_bg"], fg=C["accent"],
                 font=FONT_BOLD).pack(side="left")

        badge_text = "Version 1.0"
        badge = tk.Canvas(mid, bg=C["panel_bg"], highlightthickness=0, bd=0)
        badge.pack(pady=(6, 0))

        def _draw_badge(canvas=badge, text=badge_text):
            canvas.delete("all")
            tmp = canvas.create_text(0, 0, text=text, font=FONT_SM, anchor="nw")
            bbox = canvas.bbox(tmp)
            canvas.delete(tmp)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            pad_x, pad_y = 10, 3
            bw = tw + pad_x * 2 + 2
            bh = th + pad_y * 2 + 2
            canvas.config(width=bw, height=bh)
            x1, y1, x2, y2 = 0, 0, bw - 1, bh - 1
            r = RADIUS
            fill = "#162030"
            brd  = C["btn_blue_brd"]
            def _arc(ax1, ay1, ax2, ay2, start):
                canvas.create_arc(ax1, ay1, ax2, ay2, start=start, extent=90,
                                  style="pieslice", fill=fill, outline=fill)
            _arc(x1,        y1,        x1+r*2, y1+r*2, 90)
            _arc(x2-r*2,    y1,        x2,     y1+r*2, 0)
            _arc(x1,        y2-r*2,    x1+r*2, y2,     180)
            _arc(x2-r*2,    y2-r*2,    x2,     y2,     270)
            canvas.create_rectangle(x1+r, y1,    x2-r, y2,    fill=fill, outline=fill)
            canvas.create_rectangle(x1,   y1+r,  x2,   y2-r,  fill=fill, outline=fill)
            def _arc_brd(ax1, ay1, ax2, ay2, start):
                canvas.create_arc(ax1, ay1, ax2, ay2, start=start, extent=90,
                                  style="arc", outline=brd)
            _arc_brd(x1,        y1,        x1+r*2, y1+r*2, 90)
            _arc_brd(x2-r*2,    y1,        x2,     y1+r*2, 0)
            _arc_brd(x1,        y2-r*2,    x1+r*2, y2,     180)
            _arc_brd(x2-r*2,    y2-r*2,    x2,     y2,     270)
            canvas.create_line(x1+r, y1,   x2-r, y1,   fill=brd)
            canvas.create_line(x1+r, y2,   x2-r, y2,   fill=brd)
            canvas.create_line(x1,   y1+r, x1,   y2-r, fill=brd)
            canvas.create_line(x2,   y1+r, x2,   y2-r, fill=brd)
            canvas.create_text(bw//2, bh//2, text=text, fill=C["accent"], font=FONT_SM)

        badge.bind("<Configure>", lambda e: _draw_badge())
        badge.after(10, _draw_badge)

        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=10)

        btn_row = tk.Frame(parent, bg=C["panel_bg"])
        btn_row.pack(fill="x", padx=10, pady=8)

        FlatButton(
            btn_row, text="Discord",
            bg=C["btn_disc_bg"], fg=C["btn_disc_fg"], border_color=C["btn_disc_brd"],
            hover_bg="#242550", hover_fg="#8fa0ff", hover_border=C["btn_disc_fg"],
            command=lambda: webbrowser.open("https://discord.com/invite/2fraBuhe3m"),
            height=36,
        ).pack(fill="x")


    def _toggle_start(self):
        if state["running"] or state["minigame"]: on_f2()
        else: threading.Thread(target=run_macro, daemon=True).start()

    def _reload(self):
        on_f2()
        state["cycles"] = 0
        self.push_state()

    def _on_close(self):
        on_f2()
        self.root.destroy()


    def push_state(self):
        running = state["running"] or state["minigame"]
        if running:
            self._status_val.config(text="Running", fg=C["running"])
            self._start_btn.set_text("Stop (F1)")
            self._start_btn.set_active(True)
            if self._start_time is None:
                self._start_time = time.time()
                self._tick_timer()
        else:
            self._status_val.config(text="Stopped", fg=C["stopped"])
            self._start_btn.set_text("Start (F1)")
            self._start_btn.set_active(False)
            self._start_time = None
            if self._timer_job:
                self.root.after_cancel(self._timer_job)
                self._timer_job = None
            self._time_val.config(text="00:00:00")
        self._cycles_val.config(text=str(state["cycles"]))

    def _tick_timer(self):
        if self._start_time is None: return
        elapsed = int(time.time() - self._start_time)
        h, m, s = elapsed//3600, (elapsed%3600)//60, elapsed%60
        self._time_val.config(text=f"{h:02d}:{m:02d}:{s:02d}")
        self._timer_job = self.root.after(1000, self._tick_timer)

    def _start_sync_loop(self):
        def loop():
            while True:
                time.sleep(1)
                try: self.root.after(0, self.push_state)
                except Exception: break
        threading.Thread(target=loop, daemon=True).start()

    def run(self):
        self.root.mainloop()



def push_state_to_gui():
    global _gui_instance
    if _gui_instance is not None:
        try: _gui_instance.root.after(0, _gui_instance.push_state)
        except Exception: pass



if __name__ == "__main__":
    resize_roblox_window()

    keyboard.add_hotkey('f1', on_f1)
    keyboard.add_hotkey('f2', on_f2)

    _gui_instance = MacroGUI()
    _gui_instance.run()
