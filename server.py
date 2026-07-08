#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Screen Time - Web Dashboard v3 """
import os, sys, json, sqlite3, time, csv, io
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, request, Response, send_file
from flask_socketio import SocketIO, emit

DATA_DIR = Path(os.environ["APPDATA"]) / "ScreenTime"
DB_PATH = DATA_DIR / "screentime.db"
BASE_DIR = Path(__file__).parent
HTML_PATH = BASE_DIR / "index.html"
MANIFEST_PATH = BASE_DIR / "manifest.json"
SW_PATH = BASE_DIR / "sw.js"
ECHARTS_PATH = BASE_DIR / "echarts.min.js"

INDEX_HTML = ""
if HTML_PATH.exists():
    INDEX_HTML = HTML_PATH.read_text(encoding="utf-8")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'screentime-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS usage_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, time TEXT, process_name TEXT,
        window_title TEXT, duration_seconds INTEGER DEFAULT 60)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS app_daily_usage (
        date TEXT, process_name TEXT, foreground_seconds INTEGER DEFAULT 0,
        switch_count INTEGER DEFAULT 0, notification_count INTEGER DEFAULT 0,
        PRIMARY KEY (date, process_name))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS daily_summary (
        date TEXT PRIMARY KEY, total_active_seconds INTEGER DEFAULT 0,
        total_idle_seconds INTEGER DEFAULT 0, raw_data TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, time TEXT, app_name TEXT, title TEXT, body TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS browser_tabs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, time TEXT, process_name TEXT, window_title TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS system_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, cpu_percent REAL DEFAULT 0, mem_percent REAL DEFAULT 0,
        cpu_cores INTEGER DEFAULT 0, gpu_percent REAL DEFAULT 0, mem_used_gb REAL DEFAULT 0)""")
    # 迁移：为旧表补全 tracker 写入的列
    for col, col_def in [('gpu_percent', 'REAL DEFAULT 0'), ('mem_used_gb', 'REAL DEFAULT 0'), ('cpu_cores', 'INTEGER DEFAULT 0')]:
        try:
            cur.execute(f"ALTER TABLE system_metrics ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass  # 列已存在
    # 迁移：daily_summary 旧表补 raw_data
    try:
        cur.execute("ALTER TABLE daily_summary ADD COLUMN raw_data TEXT")
    except sqlite3.OperationalError:
        pass
    cur.execute("""CREATE TABLE IF NOT EXISTS app_categories (
        process_name TEXT PRIMARY KEY, category TEXT, category_zh TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS usage_limits (
        process_name TEXT PRIMARY KEY, daily_limit_minutes INTEGER DEFAULT 120, enabled INTEGER DEFAULT 1)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS browser_tab_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
        process_name TEXT NOT NULL, tab_title TEXT)""")
    cats = [
        ('chrome.exe','browser','\u6d4f\u89c8\u5668'),('msedge.exe','browser','\u6d4f\u89c8\u5668'),('firefox.exe','browser','\u6d4f\u89c8\u5668'),
        ('winword.exe','office','\u529e\u516c'),('excel.exe','office','\u529e\u516c'),('powerpnt.exe','office','\u529e\u516c'),
        ('outlook.exe','office','\u529e\u516c'),('onenote.exe','office','\u529e\u516c'),
        ('vscode.exe','dev','\u5f00\u53d1'),('devenv.exe','dev','\u5f00\u53d1'),('pycharm.exe','dev','\u5f00\u53d1'),
        ('wechat.exe','social','\u793e\u4ea4'),('qq.exe','social','\u793e\u4ea4'),('dingtalk.exe','social','\u793e\u4ea4'),
        ('telegram.exe','social','\u793e\u4ea4'),('discord.exe','social','\u793e\u4ea4'),
        ('steam.exe','entertainment','\u5a31\u4e50'),('spotify.exe','entertainment','\u5a31\u4e50'),
        ('qqmusic.exe','entertainment','\u5a31\u4e50'),('vlc.exe','entertainment','\u5a31\u4e50'),
        ('notepad.exe','tool','\u5de5\u5177'),('everything.exe','tool','\u5de5\u5177'),('7zg.exe','tool','\u5de5\u5177'),
        ('explorer.exe','tool','\u5de5\u5177'),('cmd.exe','tool','\u5de5\u5177'),('powershell.exe','tool','\u5de5\u5177'),
        ('taskmgr.exe','tool','\u5de5\u5177'),('marvis.exe','tool','\u5de5\u5177'),
    ]
    for cn, cat, cat_zh in cats:
        cur.execute("INSERT OR IGNORE INTO app_categories (process_name, category, category_zh) VALUES (?,?,?)", (cn, cat, cat_zh))
    conn.commit(); conn.close()

init_db()

def query_db(query, params=(), single=False):
    conn = get_db()
    cur = conn.cursor(); cur.execute(query, params)
    if single:
        row = cur.fetchone(); result = dict(row) if row else None
    else:
        result = [dict(r) for r in cur.fetchall()]
    conn.close(); return result

def today_str():
    return datetime.now().strftime("%Y-%m-%d")

@app.route("/")
def index():
    return INDEX_HTML

@app.route("/manifest.json")
def manifest():
    if MANIFEST_PATH.exists():
        return Response(MANIFEST_PATH.read_text(encoding="utf-8"), mimetype='application/json')
    return jsonify({"error": "manifest not found"}), 404

@app.route("/sw.js")
def service_worker():
    if SW_PATH.exists():
        return Response(SW_PATH.read_text(encoding="utf-8"), mimetype='application/javascript')
    return jsonify({"error": "sw not found"}), 404

@app.route("/echarts.min.js")
def echarts_js():
    if ECHARTS_PATH.exists():
        return Response(ECHARTS_PATH.read_bytes(), mimetype='application/javascript')
    return jsonify({"error": "echarts not found"}), 404

@app.route("/api/today")
def api_today():
    today = today_str()
    total_row = query_db("SELECT SUM(foreground_seconds) as total FROM app_daily_usage WHERE date=?", (today,), single=True)
    total_active = total_row['total'] if total_row and total_row['total'] else 0
    apps = query_db("SELECT * FROM app_daily_usage WHERE date=? ORDER BY foreground_seconds DESC", (today,))
    hourly = []
    for h in range(24):
        row = query_db("SELECT SUM(duration_seconds) as sec FROM usage_log WHERE date=? AND time LIKE ?", (today, f"{h:02d}:%"), single=True)
        hourly.append(row['sec'] if row and row['sec'] else 0)
    # 兜底：app_daily_usage 为空但 usage_log 有数据时，用 hourly 总和作为 fallback
    if total_active == 0 and sum(hourly) > 0:
        total_active = sum(hourly)
    notif_count = query_db("SELECT COUNT(*) as cnt FROM notifications WHERE date=?", (today,), single=True)
    ds = query_db("SELECT total_idle_seconds FROM daily_summary WHERE date=?", (today,), single=True)
    cats = query_db(
        "SELECT COALESCE(c.category,'other') as cat, COALESCE(c.category_zh,'\u5176\u4ed6') as cat_zh, SUM(a.foreground_seconds) as sec "
        "FROM app_daily_usage a LEFT JOIN app_categories c ON LOWER(a.process_name)=c.process_name "
        "WHERE a.date=? GROUP BY cat, cat_zh ORDER BY sec DESC", (today,))
    return jsonify({
        'date': today, 'total_active_seconds': total_active,
        'apps': apps, 'hourly': hourly,
        'notification_count': notif_count['cnt'] if notif_count else 0,
        'idle_seconds': ds['total_idle_seconds'] if ds else 0,
        'categories': cats
    })

@app.route("/api/range")
def api_range():
    start = request.args.get('start', ''); end = request.args.get('end', '')
    if not start or not end: return jsonify({'error': 'Missing start/end'}), 400
    daily = query_db("SELECT date, total_active_seconds, total_idle_seconds FROM daily_summary WHERE date BETWEEN ? AND ? ORDER BY date", (start, end))
    apps = query_db("SELECT process_name, SUM(foreground_seconds) as total_seconds, SUM(switch_count) as total_switches FROM app_daily_usage WHERE date BETWEEN ? AND ? GROUP BY process_name ORDER BY total_seconds DESC", (start, end))
    notifs = query_db("SELECT app_name, COUNT(*) as cnt FROM notifications WHERE date BETWEEN ? AND ? GROUP BY app_name ORDER BY cnt DESC", (start, end))
    return jsonify({'start': start, 'end': end, 'daily': daily, 'apps': apps, 'notifications': notifs})

@app.route("/api/custom-range")
def api_custom_range():
    start = request.args.get('start', today_str()); end = request.args.get('end', today_str())
    daily = query_db("SELECT date, total_active_seconds, total_idle_seconds FROM daily_summary WHERE date BETWEEN ? AND ? ORDER BY date", (start, end))
    apps = query_db("SELECT process_name, SUM(foreground_seconds) as total_seconds, SUM(switch_count) as total_switches FROM app_daily_usage WHERE date BETWEEN ? AND ? GROUP BY process_name ORDER BY total_seconds DESC", (start, end))
    cats = query_db(
        "SELECT COALESCE(c.category,'other') as cat, COALESCE(c.category_zh,'\u5176\u4ed6') as cat_zh, SUM(a.foreground_seconds) as sec "
        "FROM app_daily_usage a LEFT JOIN app_categories c ON LOWER(a.process_name)=c.process_name "
        "WHERE a.date BETWEEN ? AND ? GROUP BY cat, cat_zh ORDER BY sec DESC", (start, end))
    total_sec = sum(d['total_active_seconds'] or 0 for d in daily)
    return jsonify({'start': start, 'end': end, 'daily': daily, 'apps': apps, 'categories': cats, 'total_seconds': total_sec, 'days': len(daily)})

@app.route("/api/heatmap")
def api_heatmap():
    end = datetime.now(); start = end - timedelta(days=6)
    sstr, estr = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    rows = query_db("SELECT date, time, duration_seconds FROM usage_log WHERE date BETWEEN ? AND ?", (sstr, estr))
    grid = {}
    for r in rows:
        d = r['date']; h = int(r['time'].split(':')[0])
        grid.setdefault(d, [0]*24); grid[d][h] += (r['duration_seconds'] or 0)
    days = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    data = [{'date': d, 'hours': [min(3600, v) for v in grid.get(d, [0]*24)]} for d in days]
    return jsonify({'heatmap': data, 'days': days})

@app.route("/api/drilldown/<process_name>")
def api_drilldown(process_name):
    today = today_str(); hourly = []
    for h in range(24):
        r = query_db("SELECT SUM(duration_seconds) as sec FROM usage_log WHERE date=? AND time LIKE ? AND process_name=?", (today, f"{h:02d}:%", process_name), single=True)
        hourly.append(r['sec'] if r and r['sec'] else 0)
    tabs = []
    if process_name.upper() in {'CHROME.EXE','MSEDGE.EXE','FIREFOX.EXE','BRAVE.EXE','OPERA.EXE'}:
        tabs = query_db("SELECT DISTINCT window_title FROM browser_tabs WHERE date=? AND process_name=? ORDER BY id DESC LIMIT 20", (today, process_name))
    return jsonify({'process_name': process_name, 'hourly': hourly, 'tabs': [t['window_title'] for t in tabs]})

@app.route("/api/tabs")
def api_tabs():
    return jsonify(query_db("SELECT * FROM browser_tabs WHERE date=? ORDER BY id DESC LIMIT 100", (today_str(),)))

@app.route("/api/metrics")
def api_metrics():
    return jsonify(query_db("SELECT * FROM system_metrics ORDER BY id DESC LIMIT 50"))

@app.route("/api/categories")
def api_categories():
    return jsonify(query_db(
        "SELECT COALESCE(c.category,'other') as cat, COALESCE(c.category_zh,'\u5176\u4ed6') as cat_zh, SUM(a.foreground_seconds) as sec "
        "FROM app_daily_usage a LEFT JOIN app_categories c ON LOWER(a.process_name)=c.process_name "
        "WHERE a.date=? GROUP BY cat, cat_zh ORDER BY sec DESC", (today_str(),)))

@app.route("/api/export")
def api_export():
    start = request.args.get('start', today_str()); end = request.args.get('end', today_str())
    apps = query_db("SELECT process_name, SUM(foreground_seconds) as sec, SUM(switch_count) as switches FROM app_daily_usage WHERE date BETWEEN ? AND ? GROUP BY process_name ORDER BY sec DESC", (start, end))
    si = io.StringIO(); w = csv.writer(si)
    w.writerow(['App', 'Seconds', 'Duration', 'Switches'])
    for a in apps:
        s = a['sec'] or 0; h, m = divmod(s, 3600); m //= 60
        w.writerow([a['process_name'], s, f"{h}h {m}m", a['switches'] or 0])
    output = si.getvalue(); si.close()
    return Response(output, mimetype='text/csv', headers={'Content-Disposition': f'attachment;filename=screen_time_{start}_{end}.csv'})

@app.route("/api/score")
def api_score():
    today = today_str()
    # 获取今日使用数据
    cats = query_db(
        "SELECT COALESCE(c.category,'other') as cat, SUM(a.foreground_seconds) as sec "
        "FROM app_daily_usage a LEFT JOIN app_categories c ON LOWER(a.process_name)=c.process_name "
        "WHERE a.date=? GROUP BY cat", (today,))
    secs = {c['cat']: (c['sec'] or 0) for c in cats}
    total = sum(secs.values()) or 1
    
    # 新评分逻辑：考虑工作效率、专注度、平衡性
    # 权重：开发/办公高权重，浏览器/工具中等，社交/娱乐低权重
    w = {'dev': 1.0, 'office': 0.9, 'browser': 0.6, 'tool': 0.7, 'social': 0.3, 'entertainment': 0.2, 'other': 0.5}
    
    # 基础效率分
    efficiency = sum(secs.get(k, 0) * w.get(k, 0.5) for k in w) / total * 100
    
    # 专注度加分：高权重应用占比
    high_weight = sum(secs.get(k, 0) for k in ['dev', 'office', 'tool'])
    focus_bonus = (high_weight / total) * 20 if total > 0 else 0
    
    # 平衡性扣分：单一应用过度使用
    max_app = query_db(
        "SELECT MAX(foreground_seconds) as max_sec FROM app_daily_usage WHERE date=?", (today,), single=True)
    max_sec = max_app['max_sec'] if max_app else 0
    balance_penalty = 0
    if max_sec > total * 0.5:  # 单一应用超过50%
        balance_penalty = 15
    
    # 最终评分
    raw_score = efficiency + focus_bonus - balance_penalty
    score = min(100, max(0, round(raw_score)))
    
    # 根据评分设置颜色建议
    if score >= 80:
        color = "green"
    elif score >= 60:
        color = "amber"
    else:
        color = "red"
    
    return jsonify({
        'score': score,
        'total_seconds': total,
        'categories': secs,
        'color': color,
        'efficiency': round(efficiency, 1),
        'focus_bonus': round(focus_bonus, 1),
        'balance_penalty': balance_penalty
    })

@app.route("/api/insights")
def api_insights():
    today = today_str()
    dates = query_db("SELECT COUNT(DISTINCT date) as cnt FROM daily_summary")
    total_days = dates[0]['cnt'] if dates else 0
    if total_days < 3:
        return jsonify({'ready': False, 'message': f'\u6570\u636e\u4e0d\u8db33\u5929\uff0c\u76ee\u524d\u5df2\u6709 {total_days} \u5929\u6570\u636e\u3002', 'total_days': total_days})
    insights = []
    today_apps = query_db("SELECT * FROM app_daily_usage WHERE date=? ORDER BY foreground_seconds DESC LIMIT 10", (today,))
    past_start = (datetime.now() - timedelta(days=min(total_days, 14))).strftime("%Y-%m-%d")
    avg_apps = query_db("SELECT process_name, AVG(foreground_seconds) as avg_sec FROM app_daily_usage WHERE date BETWEEN ? AND ? GROUP BY process_name", (past_start, today))
    avg_map = {a['process_name']: a['avg_sec'] for a in avg_apps}
    for app in today_apps:
        proc = app['process_name']; today_sec = app['foreground_seconds']; avg_sec = avg_map.get(proc, 0)
        if avg_sec > 0 and today_sec > avg_sec * 1.5:
            pct = int((today_sec / avg_sec - 1) * 100)
            insights.append(f"\u4eca\u5929 {proc} \u6bd4\u5e73\u65f6\u591a\u7528\u4e86 {pct}%\uff0c\u6ce8\u610f\u5408\u7406\u5206\u914d\u65f6\u95f4\u3002")
    late_apps = query_db("SELECT process_name, SUM(duration_seconds) as sec FROM usage_log WHERE date=? AND time >= '22:00' GROUP BY process_name ORDER BY sec DESC", (today,))
    late_total = sum(a['sec'] for a in late_apps)
    if late_total > 1800:
        ent_kw = ['game','steam','chrome','edge','browser','bilibili','douyin','youtube','netflix','video','player','music','qqmusic','spotify','wechat','telegram','discord','qq']
        late_ent = [a for a in late_apps if any(kw in a['process_name'].lower() for kw in ent_kw)]
        if late_ent:
            names = ', '.join(a['process_name'] for a in late_ent[:3])
            insights.append(f"\u665a\u4e0a10\u70b9\u540e\u5a31\u4e50\u8f6f\u4ef6\u4f7f\u7528\u504f\u591a\uff08{names} \u7b49\uff09\uff0c\u5efa\u8bae\u65e9\u7761\u3002")
    today_total = query_db("SELECT total_active_seconds FROM daily_summary WHERE date=?", (today,), single=True)
    if today_total and today_total['total_active_seconds'] > 28800:
        insights.append(f"\u4eca\u5929\u5df2\u7ecf\u4f7f\u7528\u7535\u8111 {today_total['total_active_seconds']/3600:.1f} \u5c0f\u65f6\uff0c\u5efa\u8bae\u5b9a\u65f6\u8d77\u8eab\u6d3b\u52a8\u3002")
    return jsonify({'ready': True, 'total_days': total_days, 'insights': insights})

@app.route("/api/limits", methods=['GET','POST'])
def api_limits():
    if request.method == 'POST':
        data = request.get_json()
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO usage_limits (process_name, daily_limit_minutes, enabled) VALUES (?,?,?)",
                    (data.get('process_name',''), data.get('daily_limit_minutes',120), data.get('enabled',1)))
        conn.commit(); conn.close(); return jsonify({'ok': True})
    return jsonify(query_db("SELECT * FROM usage_limits"))

@app.route("/api/report")
def api_report():
    end = datetime.now(); start = end - timedelta(days=6)
    sstr, estr = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    daily = query_db("SELECT date, total_active_seconds FROM daily_summary WHERE date BETWEEN ? AND ? ORDER BY date", (sstr, estr))
    apps = query_db("SELECT process_name, SUM(foreground_seconds) as sec FROM app_daily_usage WHERE date BETWEEN ? AND ? GROUP BY process_name ORDER BY sec DESC LIMIT 5", (sstr, estr))
    cats = query_db(
        "SELECT COALESCE(c.category_zh,c.process_name) as name, SUM(a.foreground_seconds) as sec "
        "FROM app_daily_usage a LEFT JOIN app_categories c ON LOWER(a.process_name)=c.process_name "
        "WHERE a.date BETWEEN ? AND ? GROUP BY name ORDER BY sec DESC", (sstr, estr))
    total = sum(d['total_active_seconds'] or 0 for d in daily)
    return jsonify({'period': f"{sstr} ~ {estr}", 'total_seconds': total, 'avg_daily_seconds': round(total/max(len(daily),1)), 'days': len(daily), 'daily': daily, 'top_apps': apps, 'categories': cats})

@app.route("/api/history")
def api_history():
    return jsonify([d['date'] for d in query_db("SELECT DISTINCT date FROM daily_summary ORDER BY date DESC")])

@app.route("/api/system")
def api_system():
    today = today_str()
    latest = query_db("SELECT * FROM system_metrics ORDER BY id DESC LIMIT 1", single=True)
    recent = query_db("SELECT time, cpu_percent, mem_percent, gpu_percent, mem_used_gb, cpu_cores FROM system_metrics WHERE time >= datetime('now','-10 minutes') ORDER BY id DESC LIMIT 10")
    avg = query_db("SELECT AVG(cpu_percent) as cpu, AVG(mem_percent) as mem FROM system_metrics WHERE time >= datetime('now','-10 minutes')", single=True)
    return jsonify({
        'latest': latest,
        'recent': recent,
        'avg_cpu': round(avg['cpu'] if avg and avg['cpu'] else 0, 1),
        'avg_mem': round(avg['mem'] if avg and avg['mem'] else 0, 1)
    })

@app.route("/api/browser-tabs")
def api_browser_tabs():
    today = today_str()
    count = query_db("SELECT COUNT(*) as cnt FROM browser_tabs WHERE date=?", (today,), single=True)
    tabs = query_db("SELECT time, process_name, window_title FROM browser_tabs WHERE date=? ORDER BY time DESC LIMIT 20", (today,))
    return jsonify({'count': count['cnt'] if count else 0, 'tabs': tabs})

@app.route("/api/browser-tab-history")
def api_browser_tab_history():
    today = today_str()
    tabs = query_db(
        "SELECT id, timestamp, process_name, tab_title FROM browser_tab_log "
        "WHERE timestamp LIKE ? ORDER BY timestamp DESC LIMIT 50",
        (today + '%',)
    )
    return jsonify({'tabs': tabs, 'count': len(tabs)})

@app.route("/api/weekly-summary")
def api_weekly_summary():
    today = datetime.now()
    this_mon = today - timedelta(days=today.weekday())
    this_start = this_mon.strftime("%Y-%m-%d")
    this_end = today.strftime("%Y-%m-%d")
    last_start = (this_mon - timedelta(days=7)).strftime("%Y-%m-%d")
    last_end = (this_mon - timedelta(days=1)).strftime("%Y-%m-%d")
    
    this_week = query_db("SELECT SUM(total_active_seconds) as sec FROM daily_summary WHERE date BETWEEN ? AND ?", (this_start, this_end), single=True)
    last_week = query_db("SELECT SUM(total_active_seconds) as sec FROM daily_summary WHERE date BETWEEN ? AND ?", (last_start, last_end), single=True)
    
    this_sec = this_week['sec'] if this_week and this_week['sec'] else 0
    last_sec = last_week['sec'] if last_week and last_week['sec'] else 0
    
    return jsonify({
        'this_week_seconds': this_sec,
        'last_week_seconds': last_sec,
        'change_pct': round((this_sec - last_sec) / max(last_sec, 1) * 100, 0),
        'this_week_days': min((today - this_mon).days + 1, 7),
        'last_week_days': 7
    })

@app.route("/api/anomalies")
def api_anomalies():
    """Detect anomalies: CPU high, memory high, app overuse, late-night activity."""
    today = today_str()
    anomalies = []

    # 1. CPU consecutive 3 points > 80%
    cpu_rows = query_db(
        "SELECT cpu_percent FROM system_metrics WHERE time >= datetime('now','-30 minutes') ORDER BY id DESC LIMIT 20")
    high_cpu_streak = 0
    max_cpu_streak = 0
    for r in cpu_rows:
        v = r.get('cpu_percent') or 0
        if v > 80:
            high_cpu_streak += 1
            max_cpu_streak = max(max_cpu_streak, high_cpu_streak)
        else:
            high_cpu_streak = 0
    if max_cpu_streak >= 3:
        anomalies.append({'type': 'cpu_high', 'message': 'CPU连续3个采集点 > 80%'})

    # 2. Memory > 90%
    mem_row = query_db("SELECT mem_percent FROM system_metrics ORDER BY id DESC LIMIT 1", single=True)
    if mem_row and (mem_row.get('mem_percent') or 0) > 90:
        anomalies.append({'type': 'mem_high', 'message': '内存使用率 > 90%'})

    # 3. App single day > 6h
    overuse = query_db(
        "SELECT process_name, foreground_seconds FROM app_daily_usage WHERE date=? AND foreground_seconds > 21600",
        (today,))
    for r in overuse:
        anomalies.append({
            'type': 'app_overuse',
            'process_name': r['process_name'],
            'seconds': r['foreground_seconds'],
            'message': f"{r['process_name']} 单日使用 > 6h"
        })

    # 4. Late-night (0-6) activity > 30min
    late_secs = query_db(
        "SELECT SUM(duration_seconds) as sec FROM usage_log WHERE date=? AND time >= '00:00' AND time < '06:00'",
        (today,), single=True)
    if late_secs and (late_secs.get('sec') or 0) > 1800:
        anomalies.append({'type': 'late_active', 'seconds': late_secs['sec'], 'message': '深夜0-6点活跃 > 30min'})

    return jsonify({'anomalies': anomalies, 'count': len(anomalies)})

@app.route("/api/streaks")
def api_streaks():
    today = today_str()
    dates = query_db("SELECT date, total_active_seconds, total_idle_seconds FROM daily_summary ORDER BY date DESC LIMIT 30")
    
    streak = 0
    check_date = datetime.now()
    for d in dates:
        d_date = datetime.strptime(d['date'], "%Y-%m-%d")
        expected = check_date - timedelta(days=streak)
        if d_date.date() == expected.date() and (d['total_active_seconds'] or 0) > 600:
            streak += 1
        elif d_date.date() < expected.date():
            break
        check_date = d_date
    
    today_data = query_db("SELECT * FROM daily_summary WHERE date=?", (today,), single=True)
    if today_data and (today_data['total_active_seconds'] or 0) >= 600:
        pass
    elif streak > 0 and datetime.now().hour < 20:
        pass
    
    return jsonify({'current_streak': streak, 'min_active_seconds': 600, 'today_active': today_data['total_active_seconds'] if today_data else 0})

# ============ WebSocket Events ============
@socketio.on('connect')
def handle_connect():
    """Client connected - acknowledge"""
    emit('connected', {'status': 'ok', 'message': 'WebSocket connected'})

@socketio.on('request_refresh')
def handle_refresh(data=None):
    """A client or tracker requests that all clients refresh"""
    socketio.emit('data_update', {'timestamp': datetime.now().isoformat()})

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=19999, debug=False, allow_unsafe_werkzeug=True)
