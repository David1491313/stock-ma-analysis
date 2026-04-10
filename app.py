import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings, json, base64, requests, datetime

warnings.filterwarnings('ignore')

st.set_page_config(page_title="台股K線分析", page_icon="📈", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; background:#0d1117; color:#e6edf3; }
.stApp { background:#0d1117; }
.main-header { text-align:center; padding:18px 0 8px 0; }
.main-header h1 { font-size:2rem; color:#58a6ff; letter-spacing:2px; margin:0; }
.main-header p { color:#8b949e; font-size:.9rem; margin:4px 0 0 0; }
.stock-card { background:#161b22; border:1px solid #30363d; border-radius:12px; padding:18px 22px 10px 22px; margin-bottom:10px; }
.card-header { display:flex; align-items:baseline; gap:12px; margin-bottom:6px; }
.card-title { font-size:1.3rem; font-weight:700; color:#58a6ff; }
.card-code { color:#8b949e; font-size:.95rem; }
.card-sector { background:#21262d; border-radius:6px; padding:2px 10px; font-size:.8rem; color:#f0883e; }
.metric-row { display:flex; gap:18px; flex-wrap:wrap; margin:10px 0 6px 0; }
.metric-box { background:#0d1117; border-radius:8px; padding:8px 16px; min-width:90px; text-align:center; }
.metric-label { font-size:.72rem; color:#8b949e; margin-bottom:3px; }
.metric-value { font-size:1.1rem; font-weight:700; }
.up { color:#3fb950; }
.down { color:#f85149; }
.neutral { color:#8b949e; }
.stTextInput input { background:#161b22 !important; color:#e6edf3 !important; border:1px solid #30363d !important; border-radius:8px !important; }
section[data-testid="stSidebar"] { background:#161b22 !important; border-right:1px solid #30363d; }
div[data-testid="stButton"] button { background:#21262d; border:1px solid #30363d; color:#e6edf3; border-radius:8px; }
div[data-testid="stButton"] button:hover { background:#30363d; border-color:#58a6ff; }
.stRadio label, .stCheckbox label { color:#e6edf3 !important; }
.inst-wrap { overflow-x:auto; margin:8px 0; }
.inst-table { width:100%; border-collapse:collapse; font-size:.82rem; white-space:nowrap; }
.inst-table th { background:#21262d; color:#8b949e; padding:7px 12px; text-align:right; font-weight:600; border-bottom:2px solid #30363d; }
.inst-table th:first-child { text-align:center; min-width:80px; }
.inst-table td { padding:5px 12px; text-align:right; border-bottom:1px solid #1c2333; }
.inst-table td:first-child { text-align:center; color:#8b949e; }
.inst-table tr:hover td { background:#1c2333; }
.inst-table tr.total-row td { background:#1c2333; font-weight:700; border-top:2px solid #30363d; border-bottom:none; }
.inst-table tr.total-row td:first-child { color:#e6edf3; }
</style>
""", unsafe_allow_html=True)

GITHUB_TOKEN   = st.secrets.get("GITHUB_TOKEN","")
GITHUB_REPO    = st.secrets.get("GITHUB_REPO","")
WATCHLIST_FILE = st.secrets.get("WATCHLIST_FILE","watchlist.json")

def load_watchlist_from_github():
    if not GITHUB_TOKEN or not GITHUB_REPO: return None, None
    try:
        r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{WATCHLIST_FILE}",
                         headers={"Authorization":f"token {GITHUB_TOKEN}","Accept":"application/vnd.github.v3+json"}, timeout=8)
        if r.status_code==200:
            d = r.json()
            return json.loads(base64.b64decode(d["content"]).decode("utf-8")), d["sha"]
    except: pass
    return None, None

def save_watchlist_to_github(data):
    if not GITHUB_TOKEN or not GITHUB_REPO: return False
    try:
        content = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode()).decode()
        _, sha = load_watchlist_from_github()
        payload = {"message":"update watchlist","content":content}
        if sha: payload["sha"] = sha
        r = requests.put(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{WATCHLIST_FILE}",
                         headers={"Authorization":f"token {GITHUB_TOKEN}","Accept":"application/vnd.github.v3+json"},
                         json=payload, timeout=10)
        return r.status_code in (200,201)
    except: return False

@st.cache_data(ttl=86400)
def load_stock_db():
    try:
        import twstock
        db = {}
        for code, s in twstock.codes.items():
            name   = getattr(s,'name','')
            market = getattr(s,'market','')
            group  = getattr(s,'group','')
            if market in ('上市','上櫃'):
                suffix = '.TW' if market=='上市' else '.TWO'
                db[code] = (name, suffix, group)
        return db
    except:
        return {}

def get_info(code):
    db = load_stock_db()
    return db.get(code, ('', '.TW', ''))

def get_suffix(code): return get_info(code)[1]

def search_stocks(query):
    db = load_stock_db()
    q = query.strip()
    if not q: return []
    ql = q.lower()
    results = []
    for code,(name,suffix,group) in db.items():
        if code==q or name==q:      results.append((code,name,suffix,group,0))
        elif code.startswith(q):    results.append((code,name,suffix,group,1))
        elif name.startswith(q):    results.append((code,name,suffix,group,2))
        elif ql in name.lower():    results.append((code,name,suffix,group,3))
    results.sort(key=lambda x:(x[4], len(x[0])>4, x[0]))
    return results[:20]

def resolve(raw):
    raw = raw.strip()
    if not raw: return None
    db = load_stock_db()
    if raw in db: return raw + get_suffix(raw)
    results = search_stocks(raw)
    if results: return results[0][0] + results[0][2]
    return raw + '.TW'

@st.cache_data(ttl=3600)
def get_institutional_20d(code):
    try:
        start = (datetime.date.today() - datetime.timedelta(days=45)).strftime('%Y-%m-%d')
        url = (f"https://api.finmindtrade.com/api/v4/data"
               f"?dataset=TaiwanStockInstitutionalInvestorsBuySell"
               f"&data_id={code}&start_date={start}&token=")
        r = requests.get(url, timeout=12, headers={"User-Agent":"Mozilla/5.0"})
        raw = r.json()
        if raw.get('status') != 200 or not raw.get('data'):
            return []
        from collections import defaultdict
        daily = defaultdict(lambda: {'foreign':0,'trust':0,'dealer':0})
        for row in raw['data']:
            d    = row['date']
            name = row['name']
            net  = int(row['buy']) - int(row['sell'])
            if name == 'Foreign_Investor':        daily[d]['foreign'] += net
            elif name == 'Investment_Trust':      daily[d]['trust']   += net
            elif name in ('Dealer_self','Dealer_Hedging'): daily[d]['dealer'] += net
        dates = sorted(daily.keys(), reverse=True)[:20]
        return [{'date':d,'foreign':daily[d]['foreign'],'trust':daily[d]['trust'],
                 'dealer':daily[d]['dealer'],'total':daily[d]['foreign']+daily[d]['trust']+daily[d]['dealer']}
                for d in dates]
    except:
        return []

def render_inst_table(rows):
    if not rows:
        return '<div style="color:#8b949e;font-size:.82rem;padding:10px 0">⚠️ 無法取得三大法人資料</div>'
    def cell(v):
        if v>0:   return f'<span class="up">+{v:,}</span>'
        elif v<0: return f'<span class="down">{v:,}</span>'
        else:     return '<span class="neutral">-</span>'
    sum_f=sum(r['foreign'] for r in rows); sum_t=sum(r['trust'] for r in rows)
    sum_d=sum(r['dealer'] for r in rows); sum_all=sum_f+sum_t+sum_d; n=len(rows)
    html = f"""<div class="inst-wrap"><table class="inst-table">
      <thead><tr>
        <th>日期</th><th>外資（張）</th><th>投信（張）</th><th>自營商（張）</th><th>合計（張）</th>
      </tr></thead><tbody>"""
    for row in rows:
        html += f"<tr><td>{row['date']}</td><td>{cell(row['foreign'])}</td><td>{cell(row['trust'])}</td><td>{cell(row['dealer'])}</td><td>{cell(row['total'])}</td></tr>"
    html += f"""<tr class="total-row">
      <td>📊 {n}日合計</td><td>{cell(sum_f)}</td><td>{cell(sum_t)}</td><td>{cell(sum_d)}</td><td>{cell(sum_all)}</td>
    </tr></tbody></table></div>"""
    return html

DEFAULT_FOLDERS = {
    "⭐ 我的最愛": [],
    "🔬 半導體": ["2330","2317","2454"],
    "🚢 航運": ["2603","2615","2609"],
    "🏦 金融": ["2882","2881","2891"]
}

def init_folders():
    if 'folders' not in st.session_state:
        loaded, _ = load_watchlist_from_github()
        st.session_state.folders = loaded if loaded else DEFAULT_FOLDERS.copy()
    if 'cur_folder' not in st.session_state:
        st.session_state.cur_folder = list(st.session_state.folders.keys())[0]

def save_folders():
    save_watchlist_to_github(st.session_state.folders)

MA_CONFIG = [
    (5,   '#f0883e'),
    (10,  '#58a6ff'),
    (20,  '#bc8cff'),
    (60,  '#3fb950'),
    (120, '#f85149'),
    (240, '#ffa657'),
]

def get_ohlcv(ticker_symbol, period):
    period_map = {"1個月":"1mo","3個月":"3mo","6個月":"6mo","1年":"1y","2年":"2y","3年":"3y"}
    p = period_map.get(period, "3y")
    tk = yf.Ticker(ticker_symbol)
    df = tk.history(period=p)
    if df.empty: return None
    df.index = pd.to_datetime(df.index)
    df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def make_kline_chart(df, name, code, sector, active_mas):
    df = df.copy()
    # Drop rows with no volume (holidays / non-trading days)
    df = df[df['Volume'] > 0].copy()

    for n, _ in MA_CONFIG:
        df[f'MA{n}'] = df['Close'].rolling(n).mean()

    colors = ['#3fb950' if c >= o else '#f85149' for c, o in zip(df['Close'], df['Open'])]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02,
        row_heights=[0.68, 0.32],
        subplot_titles=(f"{name} ({code})  |  族群: {sector or 'N/A'}", "成交量")
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing=dict(line=dict(color='#3fb950'), fillcolor='#3fb950'),
        decreasing=dict(line=dict(color='#f85149'), fillcolor='#f85149'),
        name='K線', showlegend=False), row=1, col=1)

    for n, color in MA_CONFIG:
        key = f'MA{n}'
        fig.add_trace(go.Scatter(
            x=df.index, y=df[key], name=key,
            line=dict(color=color, width=1.5),
            visible=True if key in active_mas else 'legendonly',
            hovertemplate='%{y:.2f}'
        ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'], marker_color=colors,
        name='成交量', showlegend=False, opacity=0.8
    ), row=2, col=1)

    # Build list of all non-trading days to hide (weekends + holidays)
    # Use the actual trading dates to figure out gaps > 1 day
    dates = df.index.normalize().unique().sort_values()
    all_days = pd.date_range(start=dates[0], end=dates[-1], freq='D')
    missing = all_days.difference(dates)

    rangebreaks = [dict(bounds=['sat', 'mon'])]   # always skip weekends
    if len(missing) > 0:
        # Add individual holiday breaks
        for d in missing:
            if d.weekday() < 5:  # weekday = not weekend → holiday
                rangebreaks.append(dict(values=[d.strftime('%Y-%m-%d')]))

    rangeselector = dict(
        buttons=[
            dict(count=1,  label='1M',  step='month', stepmode='backward'),
            dict(count=3,  label='3M',  step='month', stepmode='backward'),
            dict(count=6,  label='6M',  step='month', stepmode='backward'),
            dict(count=1,  label='1Y',  step='year',  stepmode='backward'),
            dict(count=2,  label='2Y',  step='year',  stepmode='backward'),
            dict(step='all', label='全部'),
        ],
        bgcolor='#21262d', activecolor='#58a6ff',
        bordercolor='#30363d', borderwidth=1,
        font=dict(color='#e6edf3', size=11),
        x=0, y=1.0,
    )

    fig.update_layout(
        height=640,
        paper_bgcolor='#0d1117',
        plot_bgcolor='#161b22',
        font=dict(color='#e6edf3', family='Noto Sans TC'),
        xaxis=dict(
            rangeslider=dict(
                visible=True,
                thickness=0.05,
                bgcolor='#1c2333',
                bordercolor='#30363d',
                borderwidth=1,
            ),
            rangeselector=rangeselector,
            type='date',
            gridcolor='#21262d',
            rangebreaks=rangebreaks,
            tickfont=dict(size=10),
        ),
        xaxis2=dict(
            type='date',
            gridcolor='#21262d',
            rangebreaks=rangebreaks,
            tickfont=dict(size=10),
        ),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
            bgcolor='rgba(0,0,0,0)', font=dict(size=12),
            itemclick='toggle', itemdoubleclick='toggleothers'
        ),
        margin=dict(l=50, r=20, t=50, b=10),
        hovermode='x unified',
        dragmode='zoom',
    )
    fig.update_yaxes(gridcolor='#21262d', showgrid=True)
    fig.update_yaxes(title_text="價格 (TWD)", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    for ann in fig.layout.annotations:
        ann.font = dict(size=13, color='#8b949e')
    return fig

def get_metrics(df):
    close = df['Close']
    latest = close.iloc[-1]; prev = close.iloc[-2] if len(close)>1 else latest
    chg = latest - prev; chg_pct = chg/prev*100 if prev else 0
    return latest, chg, chg_pct, close.max(), close.min()

st.markdown('<div class="main-header"><h1>📈 台股K線分析</h1><p>輸入股票代碼或中文名稱，即時顯示K線圖＋均線＋成交量</p></div>', unsafe_allow_html=True)
init_folders()

with st.sidebar:
    st.markdown("### 📁 自選股資料夾")
    folder_names = list(st.session_state.folders.keys())
    for fn in folder_names:
        stocks = st.session_state.folders[fn]
        if st.button(f"{fn}  ({len(stocks)})", key=f"folder_{fn}", use_container_width=True):
            st.session_state.cur_folder = fn
            st.session_state.batch_codes = stocks.copy()
            st.session_state.do_analyze = False
    st.markdown("---")
    st.markdown("**當前資料夾：** " + st.session_state.cur_folder)
    cur = st.session_state.cur_folder
    cur_stocks = st.session_state.folders.get(cur, [])
    with st.expander("➕ 新增股票"):
        add_code = st.text_input("輸入代碼", key="add_code_input", placeholder="e.g. 2330")
        if st.button("新增", key="btn_add"):
            c = add_code.strip()
            if c and c not in st.session_state.folders[cur]:
                st.session_state.folders[cur].append(c)
                save_folders(); st.success(f"已新增 {c}"); st.rerun()
    with st.expander("🗑️ 移除股票"):
        if cur_stocks:
            rm = st.selectbox("選擇移除", cur_stocks, key="rm_select")
            if st.button("移除", key="btn_rm"):
                st.session_state.folders[cur].remove(rm)
                save_folders(); st.success(f"已移除 {rm}"); st.rerun()
        else:
            st.caption("資料夾是空的")
    with st.expander("📁 管理資料夾"):
        new_folder = st.text_input("新資料夾名稱", key="new_folder_input")
        if st.button("建立資料夾", key="btn_new_folder"):
            nf = new_folder.strip()
            if nf and nf not in st.session_state.folders:
                st.session_state.folders[nf] = []; save_folders(); st.success(f"已建立 {nf}"); st.rerun()
        if len(folder_names) > 1:
            del_folder = st.selectbox("刪除資料夾", folder_names, key="del_folder_select")
            if st.button("刪除資料夾", key="btn_del_folder"):
                del st.session_state.folders[del_folder]
                st.session_state.cur_folder = list(st.session_state.folders.keys())[0]
                save_folders(); st.rerun()
    st.markdown("---")
    period = st.radio("📅 期間", ["1個月","3個月","6個月","1年","2年","3年"], index=5, key="period_select")
    st.markdown("---")
    st.markdown("**📊 均線顯示**")
    active_mas = []
    defaults = {5:True, 10:True, 20:True, 60:False, 120:False, 240:False}
    cols_ma = st.columns(2)
    for i, (n, color) in enumerate(MA_CONFIG):
        col = cols_ma[i % 2]
        if col.checkbox(f"MA{n}", value=defaults[n], key=f"ma_toggle_{n}"):
            active_mas.append(f"MA{n}")

user_input = st.text_input("🔍", key="main_input",
    placeholder="e.g. 2330 或 台積電（按 Enter 分析）", label_visibility="collapsed")

if user_input and user_input != st.session_state.get('last_input',''):
    st.session_state.last_input = user_input
    st.session_state.do_analyze = True
    st.session_state.batch_codes = []

batch = st.session_state.get('batch_codes', [])

def render_stock(code_raw, period, active_mas):
    ticker_sym = resolve(code_raw)
    base_code  = ticker_sym.split('.')[0]
    name, _, sector = get_info(base_code)
    df = get_ohlcv(ticker_sym, period)
    if df is None or len(df) < 5:
        st.warning(f"⚠️ 無法取得 {code_raw} 的資料"); return
    latest, chg, chg_pct, high_val, low_val = get_metrics(df)
    chg_class = "up" if chg >= 0 else "down"
    sign = "+" if chg >= 0 else ""
    st.markdown(f"""
    <div class="stock-card">
      <div class="card-header">
        <span class="card-title">{name or code_raw}</span>
        <span class="card-code">{base_code}</span>
        <span class="card-sector">{sector or 'N/A'}</span>
      </div>
      <div class="metric-row">
        <div class="metric-box"><div class="metric-label">最新收盤</div><div class="metric-value {chg_class}">{latest:.2f}</div></div>
        <div class="metric-box"><div class="metric-label">漲跨</div><div class="metric-value {chg_class}">{sign}{chg:.2f}</div></div>
        <div class="metric-box"><div class="metric-label">漲跨幅</div><div class="metric-value {chg_class}">{sign}{chg_pct:.2f}%</div></div>
        <div class="metric-box"><div class="metric-label">區間最高</div><div class="metric-value up">{high_val:.2f}</div></div>
        <div class="metric-box"><div class="metric-label">區間最低</div><div class="metric-value down">{low_val:.2f}</div></div>
      </div>
    </div>""", unsafe_allow_html=True)
    fig = make_kline_chart(df, name or code_raw, base_code, sector, active_mas)
    st.plotly_chart(fig, use_container_width=True, config={
        'displayModeBar': True,
        'scrollZoom': True,
        'modeBarButtonsToRemove': ['lasso2d','select2d','toImage'],
        'displaylogo': False
    })
    with st.expander("🏦 三大法人明細（近20個交易日）", expanded=True):
        with st.spinner("載入三大法人資料..."):
            rows = get_institutional_20d(base_code)
        st.markdown(render_inst_table(rows), unsafe_allow_html=True)

if user_input and not st.session_state.get('do_analyze'):
    results = search_stocks(user_input)
    if results and not any(r[0] == user_input for r in results):
        options = [f"{r[0]} {r[1]}" for r in results[:8]]
        chosen = st.selectbox("選擇股票：", [""] + options, key="suggest_select")
        if chosen:
            pick = chosen.split()[0]
            st.session_state.last_input = pick
            st.session_state.do_analyze = True
            st.session_state.batch_codes = []
            st.rerun()

if batch:
    st.markdown(f"### 📁 {st.session_state.cur_folder}")
    for c in batch:
        render_stock(c, period, active_mas)
elif st.session_state.get('do_analyze') and user_input:
    render_stock(user_input, period, active_mas)
    st.session_state.do_analyze = False
