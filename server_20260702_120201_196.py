#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Screen Time - Web Dashboard v2 """
import os, sys, json, sqlite3, time, csv, io
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from flask import Flask, jsonify, request, Response

DATA_DIR = Path(os.environ["APPDATA"]) / "ScreenTime"
DB_PATH = DATA_DIR / "screentime.db"
HTML_PATH = Path(__file__).parent / "index.html"

INDEX_HTML = ""
if HTML_PATH.exists():
    INDEX_HTML = HTML_PATH.read_text(encoding="utf-8")

app = Flask(__name__)

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
        total_idle_seconds INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, time TEXT, app_name TEXT, title TEXT, body TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS browser_tabs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, time TEXT, process_name TEXT, window_title TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS system_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, cpu_percent REAL, mem_percent REAL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS app_categories (
        process_name TEXT PRIMARY KEY, category TEXT, category_zh TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS usage_limits (
        process_name TEXT PRIMARY KEY, daily_limit_minutes INTEGER DEFAULT 120, enabled INTEGER DEFAULT 1)""")
    # Seed default categories
    cats = [
        ('chrome.exe','browser','浏览器'),('msedge.exe','browser','浏览器'),('firefox.exe','browser','浏览器'),
        ('winword.exe','office','办公'),('excel.exe','office','办公'),('powerpnt.exe','office','办公'),
        ('outlook.exe','office','办公'),('onenote.exe','office','办公'),
        ('vscode.exe','dev','开发'),('devenv.exe','dev','开发'),('pycharm.exe','dev','开发'),
        ('wechat.exe','social','社交'),('qq.exe','social','社交'),('dingtalk.exe','social','社交'),
        ('telegram.exe','social','社交'),('discord.exe','social','社交'),
        ('steam.exe','entertainment','娱乐'),('spotify.exe','entertainment','娱乐'),
        ('qqmusic.exe','entertainment','娱乐'),('vlc.exe','entertainment','娱乐'),
        ('notepad.exe','tool','工具'),('everything.exe','tool','工具'),('7zg.exe','tool','工具'),
        ('explorer.exe','tool','工具'),('cmd.exe','tool','工具'),('powershell.exe','tool','工具'),
        ('taskmgr.exe','tool','工具'),('marvis.exe','tool','工具'),
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

# ============ Routes ============

@app.route("/")
def index():
    return INDEX_HTML

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
    notif_count = query_db("SELECT COUNT(*) as cnt FROM notifications WHERE date=?", (today,), single=True)
    ds = query_db("SELECT total_idle_seconds FROM daily_summary WHERE date=?", (today,), single=True)
    cats = query_db(
        "SELECT COALESCE(c.category,'other') as cat, COALESCE(c.category_zh,'其他') as cat_zh, SUM(a.foreground_seconds) as sec "
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
        "SELECT COALESCE(c.category,'other') as cat, COALESCE(c.category_zh,'其他') as cat_zh, SUM(a.foreground_seconds) as sec "
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
    today = today_str()
    return jsonify(query_db("SELECT * FROM browser_tabs WHERE date=? ORDER BY id DESC LIMIT 100", (today,)))

@app.route("/api/metrics")
def api_metrics():
    return jsonify(query_db("SELECT * FROM system_metrics ORDER BY id DESC LIMIT 50"))

@app.route("/api/categories")
def api_categories():
    today = today_str()
    return jsonify(query_db(
        "SELECT COALESCE(c.category,'other') as cat, COALESCE(c.category_zh,'其他') as cat_zh, SUM(a.foreground_seconds) as sec "
        "FROM app_daily_usage a LEFT JOIN app_categories c ON LOWER(a.process_name)=c.process_name "
        "WHERE a.date=? GROUP BY cat, cat_zh ORDER BY sec DESC", (today,)))

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
    cats = query_db(
        "SELECT COALESCE(c.category,'other') as cat, SUM(a.foreground_seconds) as sec "
        "FROM app_daily_usage a LEFT JOIN app_categories c ON LOWER(a.process_name)=c.process_name "
        "WHERE a.date=? GROUP BY cat", (today,))
    secs = {c['cat']: (c['sec'] or 0) for c in cats}
    total = sum(secs.values()) or 1
    w = {'dev': 1.0, 'office': 0.9, 'browser': 0.5, 'tool': 0.7, 'social': 0.2, 'entertainment': 0.1, 'other': 0.5}
    score = sum(secs.get(k, 0) * w.get(k, 0.5) for k in w) / total * 100
    return jsonify({'score': min(100, max(0, round(score))), 'total_seconds': total, 'categories': secs})

@app.route("/api/insights")
def api_insights():
    today = today_str()
    dates = query_db("SELECT COUNT(DISTINCT date) as cnt FROM daily_summary")
    total_days = dates[0]['cnt'] if dates else 0
    if total_days < 3:
        return jsonify({'ready': False, 'message': f'数据不足3天，目前有 {total_days} 天数据。', 'total_days': total_days})
    insights = []
    today_apps = query_db("SELECT * FROM app_daily_usage WHERE date=? ORDER BY foreground_seconds DESC LIMIT 10", (today,))
    past_start = (datetime.now() - timedelta(days=min(total_days, 14))).strftime("%Y-%m-%d")
    avg_apps = query_db("SELECT process_name, AVG(foreground_seconds) as avg_sec FROM app_daily_usage WHERE date BETWEEN ? AND ? GROUP BY process_name", (past_start, today))
    avg_map = {a['process_name']: a['avg_sec'] for a in avg_apps}
    for app in today_apps:
        proc = app['process_name']; today_sec = app['foreground_seconds']; avg_sec = avg_map.get(proc, 0)
        if avg_sec > 0 and today_sec > avg_sec * 1.5:
            pct = int((today_sec / avg_sec - 1) * 100)
            insights.append(f"今天 {proc} 比平时多用了 {pct}%，注意合理分配时间。")
    late_apps = query_db("SELECT process_name, SUM(duration_seconds) as sec FROM usage_log WHERE date=? AND time >= '22:00' GROUP BY process_name ORDER BY sec DESC", (today,))
    late_total = sum(a['sec'] for a in late_apps)
    if late_total > 1800:
        ent_kw = ['game','steam','chrome','edge','browser','bilibili','douyin','youtube','netflix','video','player','music','qqmusic','spotify','wechat','telegram','discord','qq']
        late_ent = [a for a in late_apps if any(kw in a['process_name'].lower() for kw in ent_kw)]
        if late_ent:
            names = ', '.join(a['process_name'] for a in late_ent[:3])
            insights.append(f"晚上10点后娱乐软件使用偏多（{names} 等），建议早睡。")
    today_total = query_db("SELECT total_active_seconds FROM daily_summary WHERE date=?", (today,), single=True)
    if today_total and today_total['total_active_seconds'] > 28800:
        insights.append(f"今天已使用电脑 {today_total['total_active_seconds']/3600:.1f} 小时，建议定时起身活动。")
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

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=19999, debug=False)
