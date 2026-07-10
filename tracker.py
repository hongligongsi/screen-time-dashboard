#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
屏幕使用时间 - 后台采集程序
静默运行，每5秒采集一次当前活跃窗口数据，记录到SQLite。
"""

import os
import sys
import time
import json
import sqlite3
import threading
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# 隐藏控制台窗口（用pythonw运行时不弹黑窗）
import ctypes
try:
    ctypes.windll.kernel32.SetConsoleTitleW("ScreenTimeTracker")
except:
    pass

DATA_DIR = Path(os.environ["APPDATA"]) / "ScreenTime"
DB_PATH = DATA_DIR / "screentime.db"

# ============ 浏览器标题清洗 ============
import re

BROWSER_SUFFIX_PATTERNS = [
    re.compile(r"\s*[-–—]\s*Google\s*Chrome$", re.IGNORECASE),
]

def clean_browser_title(title):
    """移除浏览器标题中的浏览器名称后缀"""
    if not title:
        return title
    for pat in BROWSER_SUFFIX_PATTERNS:
        title = pat.sub("", title).strip()
    # 移除可能残留的前后空白和破折号
    title = re.sub(r"\s*[-–—]\s*$", "", title).strip()
    return title

# ============ 空闲检测 ============
class IdleDetector:
    """通过 pynput 监听键盘鼠标，判断用户是否离开"""
    def __init__(self, idle_threshold=300):  # 5分钟=300秒
        self.idle_threshold = idle_threshold
        self.last_activity = time.time()
        self._lock = threading.Lock()
        self._running = False
        
    def _on_input(self, *args):
        with self._lock:
            self.last_activity = time.time()
    
    def start(self):
        self._running = True
        try:
            from pynput import keyboard, mouse
            k_listener = keyboard.Listener(on_press=self._on_input, on_release=self._on_input)
            m_listener = mouse.Listener(on_move=self._on_input, on_click=self._on_input, on_scroll=self._on_input)
            k_listener.daemon = True
            m_listener.daemon = True
            k_listener.start()
            m_listener.start()
        except Exception:
            # pynput 不可用，使用 Win32 GetLastInputInfo 作为 fallback
            import ctypes
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]
            self._lii = LASTINPUTINFO()
            self._lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            self._user32 = ctypes.windll.user32
            self._kernel32 = ctypes.windll.kernel32
            self._fallback = True
    
    def _poll_last_input(self):
        """Win32 fallback: 每秒轮询 GetLastInputInfo"""
        while self._running:
            if hasattr(self, '_user32'):
                self._user32.GetLastInputInfo(ctypes.byref(self._lii))
                tick = self._kernel32.GetTickCount()
                with self._lock:
                    self.last_activity = time.time() - (tick - self._lii.dwTime) / 1000.0
            time.sleep(1)
    
    def start_fallback_poll(self):
        """启动 fallback 轮询线程（在 main 中调用）"""
        if self._fallback:
            t = threading.Thread(target=self._poll_last_input, daemon=True)
            t.start()
    
    @property
    def is_idle(self):
        with self._lock:
            return (time.time() - self.last_activity) > self.idle_threshold
    
    @property
    def idle_seconds(self):
        with self._lock:
            return time.time() - self.last_activity


# ============ 窗口追踪 ============
BROWSER_PROCS = {'CHROME.EXE'}
NON_CHROME_BROWSERS = {'MSEDGE.EXE', 'FIREFOX.EXE', 'BRAVE.EXE', 'OPERA.EXE'}

class WindowTracker:
    """检测前台活跃窗口的进程名和窗口标题"""
    def __init__(self):
        self._fallback = False
        try:
            import win32gui
            import win32process
            import psutil
            self.win32gui = win32gui
            self.win32process = win32process
            self.psutil = psutil
        except ImportError:
            self._fallback = True
    
    def get_active_info(self):
        """返回 (process_name, window_title, pid)"""
        try:
            hwnd = self.win32gui.GetForegroundWindow()
            title = self.win32gui.GetWindowText(hwnd)
            _, pid = self.win32process.GetWindowThreadProcessId(hwnd)
            proc = self.psutil.Process(pid)
            return proc.name().upper(), title.strip(), pid
        except Exception:
            return None, "", None


class SystemMetricsCollector:
    """采集系统 CPU / 内存 / GPU / 核心数"""
    def __init__(self):
        try:
            import psutil
            self.psutil = psutil
            # 建立 CPU 基准（第一次调用会阻塞一小段时间）
            self.psutil.cpu_percent(interval=0.1)
            self._cpu_cores = psutil.cpu_count(logical=True)
            self._gpu_ok = False
            # 尝试导入 GPU 库
            try:
                import GPUtil
                self.GPUtil = GPUtil
                self._gpu_ok = True
            except ImportError:
                self._gpu_ok = False
            self._ok = True
        except ImportError:
            self._ok = False
    
    def get_metrics(self):
        if not self._ok:
            return 0, 0, 0, 0, 0
        try:
            # CPU 使用率
            cpu = self.psutil.cpu_percent(interval=None)
            # 内存使用率 + 已用 GB
            mem = self.psutil.virtual_memory()
            mem_percent = mem.percent
            mem_used_gb = mem.used / (1024**3)
            # GPU 占用
            gpu_percent = 0
            if self._gpu_ok:
                try:
                    gpus = self.GPUtil.getGPUs()
                    if gpus:
                        gpu_percent = sum(g.load for g in gpus) / len(gpus) * 100
                except:
                    pass
            return round(cpu, 1), round(mem_percent, 1), round(mem_used_gb, 2), round(gpu_percent, 1), self._cpu_cores
        except Exception:
            return 0, 0, 0, 0, 0


class AudioDetector:
    """检测是否有进程在播放音频"""
    def __init__(self):
        self._ok = False
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
            self.AudioUtilities = AudioUtilities
            self._ok = True
        except Exception:
            self._ok = False
    
    def get_playing_sessions(self):
        """返回正在播放音频的进程名列表"""
        if not self._ok:
            return []
        playing = []
        try:
            sessions = self.AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.State == 1:  # Active
                    try:
                        vol = session.SimpleAudioVolume
                        meter = session._ctl.QueryInterface(
                            self.AudioUtilities._IAudioMeterInformation)
                        if hasattr(meter, 'GetPeakValue'):
                            peak = meter.GetPeakValue()
                            if peak > 0.01 and session.Process:
                                playing.append(session.Process.name().upper())
                    except:
                        continue
        except:
            pass
        return list(set(playing))


# ============ 通知读取 ============
class NotificationReader:
    """读取 Windows 通知数据库 wpndatabase.db"""
    def __init__(self):
        self.wpn_paths = [
            Path(os.environ["LOCALAPPDATA"]) / "Microsoft/Windows/Notifications/wpndatabase.db",
            Path(os.environ["APPDATA"]) / "Microsoft/Windows/Notifications/wpndatabase.db",
        ]
        self._last_count = 0
        self._last_check = None
    
    def get_new_notifications(self, since_date):
        """获取自某日期以来的通知"""
        notifications = []
        for wpn_path in self.wpn_paths:
            if not wpn_path.exists():
                continue
            try:
                # 复制数据库后再读取（避免被锁定）
                import shutil
                tmp_db = DATA_DIR / "_wpn_tmp.db"
                shutil.copy2(str(wpn_path), str(tmp_db))
                
                conn = sqlite3.connect(str(tmp_db))
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                
                # 查询通知表
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in cur.fetchall()]
                
                for table in tables:
                    try:
                        cur.execute(f"SELECT * FROM [{table}] WHERE ArrivalTime > ?", 
                                   (since_date.timestamp() * 10000000 - 116444736000000000,))
                        rows = cur.fetchall()
                        for row in rows:
                            d = dict(row)
                            app_name = d.get('AppId', '')
                            # 从 AppId 提取应用名
                            if '!' in str(app_name):
                                app_name = str(app_name).split('!')[0]
                            elif '.' in str(app_name):
                                parts = str(app_name).split('.')
                                app_name = parts[-1] if parts else str(app_name)
                            notifications.append({
                                'app': str(app_name),
                                'time': d.get('ArrivalTime', 0)
                            })
                    except:
                        continue
                conn.close()
                if tmp_db.exists():
                    tmp_db.unlink()
            except Exception:
                continue
        
        # 按日期过滤
        today_start = since_date.replace(hour=0, minute=0, second=0, microsecond=0)
        result = []
        for n in notifications:
            try:
                t = n['time']
                if isinstance(t, int) and t > 0:
                    ts = (t / 10000000) - 11644473600
                    dt = datetime.fromtimestamp(ts)
                    if dt >= today_start:
                        result.append({'app': n['app'], 'time': dt.strftime("%Y-%m-%d %H:%M")})
            except:
                continue
        return result


# ============ 数据存储 ============
class DataStore:
    """SQLite 数据存储"""
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        
        # 按分钟粒度记录前台窗口
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,          -- YYYY-MM-DD
                time TEXT NOT NULL,          -- HH:MM
                process_name TEXT NOT NULL,  -- 进程名
                duration_seconds INTEGER DEFAULT 0,  -- 该分钟内使用秒数
                switch_count INTEGER DEFAULT 0       -- 切换到该进程的次数
            )
        """)
        
        # 每日汇总
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,       -- YYYY-MM-DD
                total_active_seconds INTEGER DEFAULT 0,
                total_idle_seconds INTEGER DEFAULT 0,
                raw_data TEXT                -- JSON 备份
            )
        """)
        
        # 通知记录
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                app_name TEXT NOT NULL
            )
        """)
        
        # 每日应用使用汇总
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_daily_usage (
                date TEXT NOT NULL,
                process_name TEXT NOT NULL,
                foreground_seconds INTEGER DEFAULT 0,
                background_seconds INTEGER DEFAULT 0,
                switch_count INTEGER DEFAULT 0,
                notification_count INTEGER DEFAULT 0,
                PRIMARY KEY (date, process_name)
            )
        """)
        
        # v2: 浏览器标签页记录
        cur.execute("CREATE TABLE IF NOT EXISTS browser_tabs (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, time TEXT NOT NULL, process_name TEXT NOT NULL, window_title TEXT)")

        # v3: 浏览器标签页标题采集
        cur.execute("CREATE TABLE IF NOT EXISTS browser_tab_log (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, process_name TEXT NOT NULL, tab_title TEXT)")

        # v2: 系统指标记录
        cur.execute("CREATE TABLE IF NOT EXISTS system_metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, cpu_percent REAL DEFAULT 0, mem_percent REAL DEFAULT 0, cpu_cores INTEGER DEFAULT 0, gpu_percent REAL DEFAULT 0, mem_used_gb REAL DEFAULT 0)")

        conn.commit()
        conn.close()
    
    def log_minute(self, date_str, time_str, process_name, duration_seconds, switch_count):
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO usage_log (date, time, process_name, duration_seconds, switch_count) VALUES (?,?,?,?,?)",
            (date_str, time_str, process_name, duration_seconds, switch_count)
        )
        conn.commit()
        conn.close()
    
    def save_daily_app_usage(self, date_str, app_data):
        """app_data: {process_name: {foreground_seconds, background_seconds, switch_count, notification_count}}
        使用 INSERT OR REPLACE 原地更新，避免 DELETE 导致重启时数据丢失。"""
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        for proc, data in app_data.items():
            cur.execute(
                "INSERT OR REPLACE INTO app_daily_usage (date, process_name, foreground_seconds, background_seconds, switch_count, notification_count) VALUES (?,?,?,?,?,?)",
                (date_str, proc, data['foreground_seconds'], data['background_seconds'], data['switch_count'], data['notification_count'])
            )
        conn.commit()
        conn.close()

    def load_today_app_usage(self, date_str):
        """加载当天已有的 app_daily_usage 数据，用于重启后接续累积数据。"""
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute(
            "SELECT process_name, foreground_seconds, background_seconds, switch_count, notification_count FROM app_daily_usage WHERE date=?",
            (date_str,)
        )
        rows = cur.fetchall()
        conn.close()
        data = {}
        for row in rows:
            data[row[0]] = {
                'foreground_seconds': row[1] or 0,
                'background_seconds': row[2] or 0,
                'switch_count': row[3] or 0,
                'notification_count': row[4] or 0,
            }
        return data
    
    def save_notifications(self, notifications):
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        for n in notifications:
            parts = n['time'].split(' ')
            date_str = parts[0]
            time_str = parts[1] if len(parts) > 1 else '00:00'
            cur.execute(
                "INSERT INTO notifications (date, time, app_name) VALUES (?,?,?)",
                (date_str, time_str, n['app'])
            )
        conn.commit()
        conn.close()
    
    def update_daily_summary(self, date_str, active_seconds, idle_seconds):
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO daily_summary (date, total_active_seconds, total_idle_seconds) VALUES (?,?,?)",
            (date_str, active_seconds, idle_seconds)
        )
        conn.commit()
        conn.close()
    
    def save_browser_tab(self, date_str, time_str, process_name, title):
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO browser_tabs (date, time, process_name, window_title) VALUES (?,?,?,?)",
            (date_str, time_str, process_name, title[:200])
        )
        conn.commit()
        conn.close()
    
    def save_browser_tab_log(self, timestamp, process_name, title):
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO browser_tab_log (timestamp, process_name, tab_title) VALUES (?,?,?)",
            (timestamp, process_name, title[:300])
        )
        conn.commit()
        conn.close()
    
    def notify_websocket(self):
        """通知 WebSocket 服务器有新数据"""
        try:
            import urllib.request
            import json
            data = json.dumps({"event": "data_update"}).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:19999/api/today",
                method="GET"
            )
            urllib.request.urlopen(req, timeout=2)
        except:
            pass
    
    def save_system_metrics(self, cpu, mem, mem_gb, gpu, cores):
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO system_metrics (time, cpu_percent, mem_percent, cpu_cores, gpu_percent, mem_used_gb) VALUES (?,?,?,?,?,?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), round(cpu, 1), round(mem, 1), int(cores), round(gpu, 1), round(mem_gb, 2))
        )
        conn.commit()
        conn.close()
    
    def save_audio_session(self, date_str, process_name, duration=60):
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO audio_sessions (date, process_name, total_duration) VALUES (?,?,0)",
            (date_str, process_name)
        )
        cur.execute(
            "UPDATE audio_sessions SET total_duration = total_duration + ? WHERE date=? AND process_name=?",
            (duration, date_str, process_name)
        )
        conn.commit()
        conn.close()


# ============ 后台进程管理 ============
def is_already_running():
    """检查是否已有 tracker 在运行"""
    import ctypes
    hMutex = ctypes.windll.kernel32.CreateMutexW(None, False, "ScreenTimeTracker_Mutex")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        return True
    return False


# ============ 主循环 ============
def main():
    if is_already_running():
        print("[ScreenTime] 采集程序已在后台运行，无需重复启动。")
        return
    
    print(f"[ScreenTime] 采集程序启动，数据目录: {DATA_DIR}")
    
    idle_detector = IdleDetector()
    idle_detector.start()
    idle_detector.start_fallback_poll()
    
    window_tracker = WindowTracker()
    metrics_collector = SystemMetricsCollector()
    audio_detector = AudioDetector()
    notification_reader = NotificationReader()
    data_store = DataStore()
    
    # 分钟级状态（每分钟重置）
    current_minute = None
    last_process = None
    minute_active = 0
    minute_switches = defaultdict(int)
    
    # 天级状态
    last_tick = time.time()
    idle_accumulated = 0
    active_accumulated = 0
    daily_app_data = defaultdict(lambda: {
        'foreground_seconds': 0, 'background_seconds': 0,
        'switch_count': 0, 'notification_count': 0
    })
    today_str = datetime.now().strftime("%Y-%m-%d")
    # 启动时加载当天已有数据，避免重启后 INSERT OR REPLACE 覆盖掉之前的累积值
    existing = data_store.load_today_app_usage(today_str)
    for proc, d in existing.items():
        daily_app_data[proc].update(d)
    notifications_collected = False
    
    # 新功能计数器
    last_tab_capture = 0       # 浏览器标签采集周期
    last_metrics_capture = 0   # 系统指标采集周期  
    last_audio_capture = 0     # 音频检测周期
    tab_minute_tracker = defaultdict(set)  # 每分钟已记录过的标签
    
    INTERVAL = 5  # 采集间隔（秒）
    
    while True:
        now = datetime.now()
        now_date = now.strftime("%Y-%m-%d")
        now_minute = now.strftime("%H:%M")
        now_hour = now.hour
        
        # 跨天时保存前一天数据
        if now_date != today_str:
            data_store.save_daily_app_usage(today_str, dict(daily_app_data))
            data_store.update_daily_summary(today_str, active_accumulated, idle_accumulated)
            daily_app_data = defaultdict(lambda: {
                'foreground_seconds': 0, 'background_seconds': 0,
                'switch_count': 0, 'notification_count': 0
            })
            active_accumulated = 0
            idle_accumulated = 0
            today_str = now_date
            notifications_collected = False
            tab_minute_tracker = defaultdict(set)
        
        tick = time.time()
        elapsed = tick - last_tick
        last_tick = tick
        
        if idle_detector.is_idle:
            idle_accumulated += elapsed
        else:
            active_accumulated += elapsed
            minute_active += elapsed
            proc, title, pid = window_tracker.get_active_info()
            if proc and proc.strip():
                daily_app_data[proc]['foreground_seconds'] += elapsed
                if proc != last_process:
                    minute_switches[proc] += 1
                    daily_app_data[proc]['switch_count'] += 1
                    last_process = proc
                
                # 浏览器标签页采集（每 30 秒一次）
                if proc in BROWSER_PROCS and title and (tick - last_tab_capture > 30):
                    tab_key = proc + title
                    if tab_key not in tab_minute_tracker.get(now_minute, set()):
                        data_store.save_browser_tab(now_date, now.strftime("%H:%M:%S"), proc, clean_browser_title(title))
                        tab_minute_tracker.setdefault(now_minute, set()).add(tab_key)
                    # 写入新的 browser_tab_log 表
                    data_store.save_browser_tab_log(now.strftime("%Y-%m-%d %H:%M:%S"), proc, clean_browser_title(title))
                    last_tab_capture = tick
                elif proc in NON_CHROME_BROWSERS:
                    log_message(f"⚠ 检测到非Chrome浏览器: {proc}，当前仅支持Chrome标签追踪")
        
        # 系统指标采集（每 30 秒一次，不受空闲影响）
        if tick - last_metrics_capture > 30:
            cpu, mem, mem_gb, gpu, cores = metrics_collector.get_metrics()
            if cpu > 0 or mem > 0:
                data_store.save_system_metrics(cpu, mem, mem_gb, gpu, cores)
            last_metrics_capture = tick
        
        # 音频检测（每 60 秒一次）
        if tick - last_audio_capture > 60:
            playing = audio_detector.get_playing_sessions()
            for p in playing:
                data_store.save_audio_session(now_date, p, 60)
            last_audio_capture = tick
        
        # 每分钟落盘
        if now_minute != current_minute:
            if current_minute:
                log_proc = last_process or "IDLE"
                data_store.log_minute(today_str, current_minute, log_proc,
                                      min(60, int(minute_active)), 
                                      minute_switches.get(last_process, 0))
            minute_active = 0
            minute_switches = defaultdict(int)
            current_minute = now_minute
            # 清理旧的标签追踪
            tab_minute_tracker.pop(current_minute, None)
        
        # 通知采集
        if not notifications_collected:
            try:
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                notifs = notification_reader.get_new_notifications(today_start)
                if notifs:
                    data_store.save_notifications(notifs)
                    for n in notifs:
                        daily_app_data[n['app']]['notification_count'] += 1
                notifications_collected = True
            except:
                pass
        
        # 每 30 秒保存一次当日汇总
        if int(tick) % 30 < INTERVAL:
            try:
                data_store.save_daily_app_usage(today_str, dict(daily_app_data))
                data_store.update_daily_summary(today_str, active_accumulated, idle_accumulated)
            except:
                pass
        
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
