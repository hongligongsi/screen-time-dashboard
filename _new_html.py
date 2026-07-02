NEW_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>屏幕使用时间</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #1c1c1e;
    color: #ffffff;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ============ Chrome-like Container ============ */
.container {
    max-width: 460px;  /* iPhone-like card width */
    margin: 0 auto;
    padding: 48px 20px 60px;
}

/* ============ Header ============ */
.header {
    margin-bottom: 32px;
}
.header h1 {
    font-size: 34px;
    font-weight: 700;
    letter-spacing: 0.3px;
    color: #ffffff;
    line-height: 1.1;
}
.header .sub {
    font-size: 15px;
    color: #98989d;
    margin-top: 4px;
    font-weight: 400;
    letter-spacing: 0.1px;
}

/* ============ Tabs ============ */
.tab-bar {
    display: flex;
    background: #2c2c2e;
    border-radius: 10px;
    padding: 3px;
    margin-bottom: 24px;
}
.tab-btn {
    flex: 1;
    padding: 9px 0;
    text-align: center;
    font-size: 14px;
    font-weight: 500;
    color: #98989d;
    cursor: pointer;
    border-radius: 8px;
    transition: all 0.25s cubic-bezier(0.4, 0.0, 0.2, 1);
    border: none;
    background: transparent;
    -webkit-tap-highlight-color: transparent;
}
.tab-btn.active {
    background: #636366;
    color: #ffffff;
    font-weight: 600;
}

/* ============ Stat Hero ============ */
.hero-card {
    background: linear-gradient(135deg, #2c2c2e 0%, #3a3a3c 100%);
    border-radius: 16px;
    padding: 24px 20px;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}
.hero-card::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -30%;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(88,86,214,0.12) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-label {
    font-size: 13px;
    font-weight: 500;
    color: #98989d;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
}
.hero-value {
    font-size: 56px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -1px;
    line-height: 1.0;
    margin-bottom: 4px;
}
.hero-detail {
    font-size: 14px;
    color: #98989d;
    font-weight: 400;
}
.hero-stats {
    display: flex;
    gap: 20px;
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid rgba(255,255,255,0.08);
}
.hero-stat-item {
    flex: 1;
}
.hero-stat-item .num {
    font-size: 18px;
    font-weight: 600;
    color: #ffffff;
}
.hero-stat-item .label {
    font-size: 12px;
    color: #98989d;
    margin-top: 2px;
}

/* ============ Daily Bar Chart (Week) ============ */
.chart-card {
    background: #2c2c2e;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
}
.chart-title {
    font-size: 15px;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 16px;
}
.chart-bars {
    display: flex;
    align-items: flex-end;
    gap: 6px;
    height: 120px;
    padding-bottom: 28px;
    position: relative;
}
.chart-bar-group {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
    justify-content: flex-end;
    cursor: pointer;
    position: relative;
}
.chart-bar-track {
    width: 100%;
    max-width: 32px;
    border-radius: 6px 6px 2px 2px;
    min-height: 3px;
    transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
    position: relative;
    background: #48484a;
    overflow: hidden;
}
.chart-bar-fill {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    border-radius: 6px 6px 2px 2px;
    transition: height 0.5s cubic-bezier(0.4, 0.0, 0.2, 1);
    background: linear-gradient(180deg, #5e5ce6 0%, #7c7aff 100%);
}
.chart-bar-group.selected .chart-bar-fill {
    background: linear-gradient(180deg, #ff3b30 0%, #ff6b62 100%);
}
.chart-bar-label {
    position: absolute;
    bottom: 0;
    font-size: 11px;
    color: #98989d;
    font-weight: 400;
    white-space: nowrap;
}
.chart-bar-value {
    font-size: 10px;
    color: #636366;
    margin-bottom: 4px;
    font-weight: 500;
    transition: color 0.2s;
}
.chart-bar-group:hover .chart-bar-value {
    color: #98989d;
}

/* ============ Section Title ============ */
.section-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 12px;
    padding: 0 4px;
}
.section-title {
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
}
.section-sub {
    font-size: 13px;
    color: #5e5ce6;
    font-weight: 500;
    cursor: pointer;
}

/* ============ App List (iOS Style) ============ */
.app-list {
    background: #2c2c2e;
    border-radius: 14px;
    overflow: hidden;
    margin-bottom: 20px;
}
.app-item {
    display: flex;
    align-items: center;
    padding: 11px 16px;
    min-height: 52px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    transition: background 0.15s;
    cursor: pointer;
}
.app-item:last-child { border-bottom: none; }
.app-item:hover { background: rgba(255,255,255,0.03); }

.app-icon-wrap {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    font-weight: 700;
    color: #fff;
    margin-right: 12px;
    flex-shrink: 0;
    text-transform: uppercase;
    position: relative;
    box-shadow: 0 2px 6px rgba(0,0,0,0.2);
}
.app-info { flex: 1; min-width: 0; }
.app-name {
    font-size: 15px;
    font-weight: 500;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.app-meta {
    font-size: 12px;
    color: #98989d;
    margin-top: 2px;
}
.app-right {
    text-align: right;
    flex-shrink: 0;
    margin-left: 12px;
}
.app-time {
    font-size: 16px;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: -0.3px;
}
.app-notif {
    font-size: 11px;
    color: #ff453a;
    margin-top: 2px;
}

/* ============ Insights ============ */
.insights-card {
    background: linear-gradient(135deg, #2c2c2e 0%, #3a3a3c 100%);
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 20px;
}
.insights-card .title {
    font-size: 15px;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.insights-card .title::before {
    content: '💡';
    font-size: 16px;
}
.insight-item {
    padding: 8px 0;
    font-size: 14px;
    color: #e5e5ea;
    line-height: 1.5;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.insight-item:last-child { border-bottom: none; }
.insight-wait {
    font-size: 14px;
    color: #98989d;
    text-align: center;
    padding: 16px 0;
}

/* ============ Hour Detail Modal ============ */
.hour-detail {
    background: #2c2c2e;
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 20px;
    display: none;
    border: 1px solid rgba(94,92,230,0.2);
}
.hour-detail.show { display: block; }
.hour-detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}
.hour-detail-header .title {
    font-size: 14px;
    font-weight: 600;
    color: #ffffff;
}
.hour-detail-header .close {
    font-size: 13px;
    color: #5e5ce6;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 6px;
}
.hour-detail-header .close:hover {
    background: rgba(94,92,230,0.1);
}
.hour-app-item {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    font-size: 13px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.hour-app-item:last-child { border-bottom: none; }
.hour-app-name { color: #e5e5ea; }
.hour-app-time { color: #98989d; font-weight: 500; }

/* ============ Empty State ============ */
.empty-state {
    text-align: center;
    padding: 40px 20px;
    color: #636366;
    font-size: 14px;
    line-height: 1.6;
}
.empty-state .icon {
    font-size: 40px;
    margin-bottom: 12px;
    display: block;
}

/* ============ Loading Skeleton ============ */
@keyframes shimmer {
    0% { opacity: 0.06; }
    50% { opacity: 0.15; }
    100% { opacity: 0.06; }
}
.skeleton {
    background: rgba(255,255,255,0.08);
    border-radius: 8px;
    animation: shimmer 1.8s ease-in-out infinite;
    height: 20px;
    margin: 8px 0;
}

/* ============ Scrollbar ============ */
::-webkit-scrollbar {
    width: 0;
    height: 0;
}

/* ============ Animations ============ */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}
.app-item { animation: fadeInUp 0.35s ease both; }
.app-item:nth-child(1) { animation-delay: 0.02s; }
.app-item:nth-child(2) { animation-delay: 0.04s; }
.app-item:nth-child(3) { animation-delay: 0.06s; }
.app-item:nth-child(4) { animation-delay: 0.08s; }
.app-item:nth-child(5) { animation-delay: 0.10s; }
.app-item:nth-child(6) { animation-delay: 0.12s; }
.app-item:nth-child(7) { animation-delay: 0.14s; }
.app-item:nth-child(8) { animation-delay: 0.16s; }
</style>
</head>
<body>
<div class="container" id="app">
    <div class="header">
        <h1>屏幕使用时间</h1>
        <div class="sub" id="headerDate"></div>
    </div>

    <div class="tab-bar">
        <button class="tab-btn active" data-range="today">今日</button>
        <button class="tab-btn" data-range="week">本周</button>
        <button class="tab-btn" data-range="month">本月</button>
    </div>

    <!-- 主统计 -->
    <div class="hero-card" id="heroCard">
        <div class="hero-label">今日屏幕使用时间</div>
        <div class="hero-value" id="heroValue">--</div>
        <div class="hero-detail" id="heroDetail">加载中...</div>
        <div class="hero-stats">
            <div class="hero-stat-item">
                <div class="num" id="statApps">--</div>
                <div class="label">应用数</div>
            </div>
            <div class="hero-stat-item">
                <div class="num" id="statPickups">--</div>
                <div class="label">启动次数</div>
            </div>
            <div class="hero-stat-item">
                <div class="num" id="statNotif">--</div>
                <div class="label">通知</div>
            </div>
        </div>
    </div>

    <!-- 时间轴图表 -->
    <div class="chart-card">
        <div class="chart-title" id="chartTitle">每小时使用情况</div>
        <div class="chart-bars" id="chartBars"></div>
    </div>

    <!-- 选中时段详情 -->
    <div class="hour-detail" id="hourDetail">
        <div class="hour-detail-header">
            <span class="title" id="hourDetailTitle"></span>
            <span class="close" id="hourCloseBtn">关闭</span>
        </div>
        <div id="hourDetailContent"></div>
    </div>

    <!-- 应用列表 -->
    <div class="section-header">
        <div class="section-title" id="listTitle">最常用 App</div>
        <div class="section-sub" id="listSub"></div>
    </div>
    <div class="app-list" id="appList"></div>

    <!-- 建议 -->
    <div class="insights-card" id="insightsCard">
        <div class="title">使用建议</div>
        <div id="insightsContent" class="insight-wait">分析中...</div>
    </div>
</div>

<script>
const API = '/api';
let currentRange = 'today';
let hourlyData = [];
let selectedHour = -1;
let appColors = {};

function pickColor(name) {
    if (appColors[name]) return appColors[name];
    const palettes = [
        ['#5e5ce6','#7c7aff'],
        ['#ff453a','#ff6b62'],
        ['#ff9f0a','#ffb84d'],
        ['#30d158','#5ae67a'],
        ['#0a84ff','#4da6ff'],
        ['#bf5af2','#d68aff'],
        ['#ff375f','#ff6b82'],
        ['#64d2ff','#94e0ff'],
        ['#ac8e68','#c4ad93'],
        ['#ff6482','#ff8fa3'],
        ['#76d672','#9ee49a'],
        ['#ffd60a','#ffe44d'],
    ];
    const i = Object.keys(appColors).length % palettes.length;
    return palettes[i];
}

function formatTime(seconds) {
    if (!seconds || seconds < 60) return '0 分钟';
    const h = Math.floor(seconds / 3600);
    const m = Math.round((seconds % 3600) / 60);
    if (h > 0 && m > 0) return h + ' 小时 ' + m + ' 分钟';
    if (h > 0) return h + ' 小时';
    return m + ' 分钟';
}

function formatTimeShort(seconds) {
    if (!seconds || seconds < 60) return '<1分钟';
    const h = Math.floor(seconds / 3600);
    const m = Math.round((seconds % 3600) / 60);
    if (h > 0) return h + 'h ' + (m > 0 ? m + 'm' : '');
    return m + ' 分钟';
}

function cleanName(name) {
    return (name || '').replace(/\.exe$/i, '');
}

async function fetchAPI(url) {
    try {
        const resp = await fetch(url);
        return await resp.json();
    } catch(e) {
        return null;
    }
}

function getDateRange() {
    const now = new Date();
    const today = now.toISOString().slice(0,10);
    const d = new Date(now);
    if (currentRange === 'today') return {start: today, end: today};
    if (currentRange === 'week') {
        const day = d.getDay();
        const diff = day === 0 ? 6 : day - 1; // Monday as start
        d.setDate(d.getDate() - diff);
        return {start: d.toISOString().slice(0,10), end: today};
    }
    if (currentRange === 'month') {
        return {start: now.getFullYear()+'-'+String(now.getMonth()+1).padStart(2,'0')+'-01', end: today};
    }
    return {start: today, end: today};
}

function renderChart(values, title, labels) {
    document.getElementById('chartTitle').textContent = title;
    const container = document.getElementById('chartBars');
    const maxVal = Math.max(...values, 1);
    
    container.innerHTML = values.map((v, i) => {
        const pct = (v / maxVal) * 100;
        const isSel = i === selectedHour;
        const label = labels ? labels[i] : (i + '时');
        return '<div class="chart-bar-group' + (isSel ? ' selected' : '') + '" data-idx="' + i + '">' +
            '<div class="chart-bar-value">' + (v > 0 ? formatTimeShort(v) : '') + '</div>' +
            '<div class="chart-bar-track">' +
                '<div class="chart-bar-fill" style="height:' + Math.max(pct, 2) + '%"></div>' +
            '</div>' +
            '<div class="chart-bar-label">' + label + '</div>' +
        '</div>';
    }).join('');
    
    // Click handlers
    container.querySelectorAll('.chart-bar-group').forEach(el => {
        el.addEventListener('click', function() {
            const idx = parseInt(this.dataset.idx);
            selectedHour = (selectedHour === idx) ? -1 : idx;
            refresh();
        });
    });
}

async function refresh() {
    const range = getDateRange();
    
    if (currentRange === 'today') {
        const data = await fetchAPI(API + '/today');
        if (data) renderToday(data);
    } else {
        const data = await fetchAPI(API + '/range?start=' + range.start + '&end=' + range.end);
        if (data) renderRange(data);
    }
    
    const insights = await fetchAPI(API + '/insights');
    if (insights) renderInsights(insights);
    
    const now = new Date();
    document.getElementById('headerDate').textContent =
        range.start === range.end
            ? now.getFullYear() + '年' + (now.getMonth()+1) + '月' + now.getDate() + '日'
            : range.start + ' ~ ' + range.end;
}

function renderToday(data) {
    // Hero
    document.getElementById('heroValue').textContent = formatTime(data.total_active_seconds).replace('0 分钟','0m');
    const appsCount = data.apps ? data.apps.length : 0;
    const totalPickups = data.apps ? data.apps.reduce((s, a) => s + (a.switch_count || 0), 0) : 0;
    document.getElementById('statApps').textContent = appsCount;
    document.getElementById('statPickups').textContent = totalPickups;
    document.getElementById('statNotif').textContent = data.notification_count || 0;
    
    const hour = new Date().getHours();
    document.getElementById('heroDetail').textContent =
        '截止 ' + hour + ':00 · 共打开 ' + appsCount + ' 个应用';
    
    hourlyData = data.hourly || [];
    renderChart(hourlyData, '每小时使用情况', null);
    
    // Hour detail
    renderHourDetail(data);
    
    // App list
    renderAppList(data.apps || [], false);
    document.getElementById('listTitle').textContent = '最常用 App';
    document.getElementById('listSub').textContent = formatTime(data.total_active_seconds) + ' 总计';
}

function renderRange(data) {
    const totalSec = (data.daily || []).reduce((s, d) => s + (d.total_active_seconds || 0), 0);
    const daysCount = data.daily ? data.daily.length : 0;
    const avgSec = daysCount > 0 ? Math.round(totalSec / daysCount) : 0;
    
    document.getElementById('heroValue').textContent = formatTime(avgSec).replace('0 分钟','0m');
    document.getElementById('heroDetail').textContent = '日均 · ' + daysCount + ' 天';
    
    const appsCount = data.apps ? data.apps.length : 0;
    const totalPickups = data.apps ? data.apps.reduce((s, a) => s + (a.total_switches || 0), 0) : 0;
    document.getElementById('statApps').textContent = appsCount;
    document.getElementById('statPickups').textContent = totalPickups;
    
    const totalNotif = (data.notifications || []).reduce((s, n) => s + n.cnt, 0);
    document.getElementById('statNotif').textContent = totalNotif;
    
    // Chart shows daily
    const dailySecs = (data.daily || []).map(d => d.total_active_seconds || 0);
    const dailyLabels = (data.daily || []).map(d => {
        const parts = (d.date || '').split('-');
        return (parseInt(parts[1]) + '/' + parseInt(parts[2]));
    });
    renderChart(dailySecs, '每日使用情况', dailyLabels);
    selectedHour = -1;
    document.getElementById('hourDetail').classList.remove('show');
    
    renderAppList(data.apps || [], false);
    document.getElementById('listTitle').textContent = '应用使用详情（汇总）';
    document.getElementById('listSub').textContent = '共 ' + daysCount + ' 天 · 日均 ' + formatTime(avgSec);
}

function renderAppList(apps) {
    const list = document.getElementById('appList');
    if (!apps || apps.length === 0) {
        list.innerHTML = '<div class="empty-state"><span class="icon">📊</span>暂无使用数据<br>采集程序正在记录中...</div>';
        return;
    }
    
    list.innerHTML = apps.map((app) => {
        const name = cleanName(app.process_name);
        const seconds = app.foreground_seconds || app.total_seconds || 0;
        const switches = app.switch_count || app.total_switches || 0;
        const notifs = app.notification_count || 0;
        const gradient = pickColor(app.process_name);
        const initial = name.charAt(0).toUpperCase();
        
        let meta = '';
        if (switches > 0) meta += '启动 ' + switches + ' 次';
        if (meta) meta += ' · ';
        meta += formatTime(seconds);
        
        let notifHtml = '';
        if (notifs > 0) {
            notifHtml = '<div class="app-notif">' + notifs + ' 条通知</div>';
        }
        
        return '<div class="app-item">' +
            '<div class="app-icon-wrap" style="background:linear-gradient(135deg,' + gradient[0] + ' 0%,' + gradient[1] + ' 100%)">' + initial + '</div>' +
            '<div class="app-info">' +
                '<div class="app-name">' + name + '</div>' +
                '<div class="app-meta">' + meta + '</div>' +
            '</div>' +
            '<div class="app-right">' +
                '<div class="app-time">' + formatTimeShort(seconds) + '</div>' +
                notifHtml +
            '</div>' +
        '</div>';
    }).join('');
}

function renderHourDetail(data) {
    const detail = document.getElementById('hourDetail');
    if (selectedHour < 0 || currentRange !== 'today') {
        detail.classList.remove('show');
        return;
    }
    
    if (!data || !data.hourly) { detail.classList.remove('show'); return; }
    const val = data.hourly[selectedHour] || 0;
    document.getElementById('hourDetailTitle').textContent =
        selectedHour + ':00 ~ ' + (selectedHour + 1) + ':00 · ' + formatTime(val);
    
    const content = document.getElementById('hourDetailContent');
    if (val === 0) {
        content.innerHTML = '<div class="insight-wait">该时段无活跃记录</div>';
    } else {
        content.innerHTML = '<div class="insight-wait">选中时段内活跃 ' + formatTime(val) + '</div>';
    }
    detail.classList.add('show');
}

function renderInsights(data) {
    const content = document.getElementById('insightsContent');
    if (!data || !data.ready) {
        content.innerHTML = '<div class="insight-wait">' +
            (data ? data.message : '分析中...') + '</div>';
        return;
    }
    if (!data.insights || data.insights.length === 0) {
        content.innerHTML = '<div class="insight-wait">使用习惯良好，继续保持。</div>';
        return;
    }
    content.innerHTML = data.insights.map(i =>
        '<div class="insight-item">' + i + '</div>'
    ).join('');
}

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        currentRange = this.dataset.range;
        selectedHour = -1;
        document.getElementById('hourDetail').classList.remove('show');
        refresh();
    });
});

// Hour detail close
document.getElementById('hourCloseBtn').addEventListener('click', () => {
    selectedHour = -1;
    document.getElementById('hourDetail').classList.remove('show');
    document.querySelectorAll('.chart-bar-group').forEach(el => el.classList.remove('selected'));
});

// Auto refresh
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""
