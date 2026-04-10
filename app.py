import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings, json, base64, requests

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
.stock-card { background:#161b22; border:1px solid #30363d; border-radius:12px; padding:18px 22px 10px 22px; margin-bottom:22px; }
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
.inst-row { display:flex; gap:12px; flex-wrap:wrap; margin:8px 0 4px 0; }
.inst-box { background:#161b22; border:1px solid #30363d; border-radius:8px; padding:6px 14px; font-size:.82rem; text-align:center; flex:1; min-width:80px; }
.inst-label { color:#8b949e; margin-bottom:2px; }
.stTextInput input { background:#161b22 !important; color:#e6edf3 !important; border:1px solid #30363d !important; border-radius:8px !important; }
.stSelectbox div { background:#161b22 !important; color:#e6edf3 !important; }
section[data-testid="stSidebar"] { background:#161b22 !important; border-right:1px solid #30363d; }
div[data-testid="stButton"] button { background:#21262d; border:1px solid #30363d; color:#e6edf3; border-radius:8px; }
div[data-testid="stButton"] button:hover { background:#30363d; border-color:#58a6ff; }
.stRadio label { color:#e6edf3 !important; }
.stCheckbox label { color:#e6edf3 !important; font-size:.9rem !important; }
</style>
""", unsafe_allow_html=True)

# ── GitHub persistence ──────────────────────────────────────────────
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN","")
GITHUB_REPO  = st.secrets.get("GITHUB_REPO","")
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

# ── Stock DB ────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def load_stock_db():
    try:
        import twstock
        db = {}
        for code, s in twstock.codes.items():
            name = getattr(s,'name','')
            market = getattr(s,'market','')
            group = getattr(s,'group','')
            if market in ('上市','上櫃'):
                suffix = '.TW' if market=='上市' else '.TWO'
                db[code] = (name, suffix, group)
        return db
    except:
        return {}

def get_info(code):
    db = load_stock_db()
    if code in db: return db[code]
    return ('', '.TW', '')

def get_name(code):   return get_info(code)[0]
def get_suffix(code): return get_info(code)[1]

def search_stocks(query):
    db = load_stock_db()
    q = query.strip()
    if not q: return []
    ql = q.lower()
    results = []
    for code,(name,suffix,group) in db.items():
        if code==q or name==q: results.append((code,name,suffix,group,0))
        elif code.startswith(q): results.append((code,name,suffix,group,1))
        elif name.startswith(q): results.append((code,name,suffix,group,2))
        elif ql in name.lower(): results.append((code,name,suffix,group,3))
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

# ── Institutional investors ─────────────────────────────────────────
def get_institutional(code):
    try:
        import datetime
        today = datetime.date.today()
        date_str = today.strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/rwd/zh/fund/T86?stockNo={code}&response=json&date={date_str}"
        r = requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
        d = r.json()
        if d.get('stat')=='OK' and d.get('data'):
            row = d['data'][-1]
            def parse(s):
                try: return int(str(s).replace(',','').replace('+',''))
                except: return 0
            return parse(row[4]), parse(row[8]), parse(row[11]), parse(row[13])
    except: pass
    try:
        import datetime
        today = datetime.date.today()
        url = f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&se=EW&t=D&d={today.strftime('%Y/%m/%d')}&stkno={code}&s=0,asc,0"
        r = requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
        d = r.json()
        if d.get('aaData'):
            row = d['aaData'][0]
            def parse(s):
                try: return int(str(s).replace(',','').replace('+',''))
                except: return 0
            f = parse(row[4]); t = parse(row[10]); dl = parse(row[13])
            return f, t, dl, f+t+dl
    except: pass
    return None

# ── Folders ─────────────────────────────────────────────────────────
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

# ── MA config ───────────────────────────────────────────────────────
MA_CONFIG = [
    (5,   '#f0883e'),   # orange
    (10,  '#58a6ff'),   # blue
    (20,  '#bc8cff'),   # purple
    (60,  '#3fb950'),   # green
    (120, '#f85149'),   # red
    (240, '#ffa657'),   # yellow-orange
]

# ── OHLCV fetch ─────────────────────────────────────────────────────
def get_ohlcv(ticker_symbol, period):
    period_map = {"1個月":"1mo","3個月":"3mo","6個月":"6mo","1年":"1y","2年":"2y","3年":"3y"}
    p = period_map.get(period, "6mo")
    tk = yf.Ticker(ticker_symbol)
    df = tk.history(period=p)
    if df.empty: return None
    df.index = pd.to_datetime(df.index)
    df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# ── K-Line Chart ────────────────────────────────────────────────────
def make_kline_chart(df, name, code, sector, active_mas):
    df = df.copy()
    for n, _ in MA_CONFIG:
        df[f'MA{n}'] = df['Close'].rolling(n).mean()

    colors = ['#3fb950' if c >= o else '#f85149'
              for c, o in zip(df['Close'], df['Open'])]

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.72, 0.28],
        subplot_titles=(f"{name} ({code})  |  族群: {sector or 'N/A'}", "成交量")
    )

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'],   close=df['Close'],
        increasing=dict(line=dict(color='#3fb950'), fillcolor='#3fb950'),
        decreasing=dict(line=dict(color='#f85149'), fillcolor='#f85149'),
        name='K線', showlegend=False
    ), row=1, col=1)

    for n, color in MA_CONFIG:
        key = f'MA{n}'
        visible = key in active_mas
        fig.add_trace(go.Scatter(
            x=df.index, y=df[key],
            name=key,
            line=dict(color=color, width=1.5),
            visible=True if visible else 'legendonly',
            hovertemplate='%{y:.2f}'
        ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'],
        marker_color=colors,
        name='成交量', showlegend=False, opacity=0.8
    ), row=2, col=1)

    fig.update_layout(
        height=560,
        paper_bgcolor='#0d1117',
        plot_bgcolor='#161b22',
        font=dict(color='#e6edf3', family='Noto Sans TC'),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02,
            xanchor='right', x=1,
            bgcolor='rgba(0,0,0,0)', font=dict(size=12),
            itemclick='toggle', itemdoubleclick='toggleothers'
        ),
        margin=dict(l=50, r=20, t=45, b=20),
        hovermode='x unified'
    )
    fig.update_xaxes(
        gridcolor='#21262d', showgrid=True,
        tickfont=dict(size=10),
        rangebreaks=[dict(bounds=["sat","mon"])]
    )
    fig.update_yaxes(gridcolor='#21262d', showgrid=True)
    fig.update_yaxes(title_text="價格 (TWD)", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    for ann in fig.layout.annotations:
        ann.font = dict(size=13, color='#8b949e')
    return fig

def get_metrics(df):
    close = df['Close']
    latest = close.iloc[-1]
    prev   = close.iloc[-2] if len(close)>1 else latest
    chg    = latest - prev
    chg_pct = chg/prev*100 if prev else 0
    return latest, chg, chg_pct, close.max(), close.min()

# ── Main ─────────────────────────────────────────────────────────────
st.markdown('<div class="main-header"><h1>📈 台股K線分析</h1><p>輸入股票代碼或中文名稱，即時顯示K線圖＋均線＋成交量</p></div>', unsafe_allow_html=True)

init_folders()

# ── Sidebar ──────────────────────────────────────────────────────────
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
                save_folders()
                st.success(f"已新增 {c}")
                st.rerun()

    with st.expander("🗑️ 移除股票"):
        if cur_stocks:
            rm = st.selectbox("選擇移除", cur_stocks, key="rm_select")
            if st.button("移除", key="btn_rm"):
                st.session_state.folders[cur].remove(rm)
                save_folders()
                st.success(f"已移除 {rm}")
                st.rerun()
        else:
            st.caption("資料夾是空的")

    with st.expander("📁 管理資料夾"):
        new_folder = st.text_input("新資料夾名稱", key="new_folder_input")
        if st.button("建立資料夾", key="btn_new_folder"):
            nf = new_folder.strip()
            if nf and nf not in st.session_state.folders:
                st.session_state.folders[nf] = []
                save_folders()
                st.success(f"已建立 {nf}")
                st.rerun()
        if len(folder_names) > 1:
            del_folder = st.selectbox("刪除資料夾", folder_names, key="del_folder_select")
            if st.button("刪除資料夾", key="btn_del_folder"):
                del st.session_state.folders[del_folder]
                st.session_state.cur_folder = list(st.session_state.folders.keys())[0]
                save_folders()
                st.rerun()

    st.markdown("---")
    period = st.radio("📅 期間", ["1個月","3個月","6個月","1年","2年","3年"], index=2, key="period_select")

    st.markdown("---")
    st.markdown("**📊 均線顯示**")
    active_mas = []
    # Default on: MA5, MA10, MA20; Default off: MA60, MA120, MA240
    defaults = {5:True, 10:True, 20:True, 60:False, 120:False, 240:False}
    cols_ma = st.columns(2)
    for i, (n, color) in enumerate(MA_CONFIG):
        col = cols_ma[i % 2]
        label_html = f'<span style="color:{color};font-weight:700;">MA{n}</span>'
        checked = col.checkbox(f"MA{n}", value=defaults[n], key=f"ma_toggle_{n}")
        if checked:
            active_mas.append(f"MA{n}")

# ── Search ───────────────────────────────────────────────────────────
user_input = st.text_input(
    "🔍",
    key="main_input",
    placeholder="e.g. 2330 或 台積電（按 Enter 分析）",
    label_visibility="collapsed"
)

if user_input and user_input != st.session_state.get('last_input',''):
    st.session_state.last_input = user_input
    st.session_state.do_analyze = True
    st.session_state.batch_codes = []

batch = st.session_state.get('batch_codes', [])

# ── Render stock ─────────────────────────────────────────────────────
def render_stock(code_raw, period, active_mas):
    ticker_sym = resolve(code_raw)
    base_code = ticker_sym.split('.')[0]
    name, _, sector = get_info(base_code)

    df = get_ohlcv(ticker_sym, period)
    if df is None or len(df) < 5:
        st.warning(f"⚠️ 無法取得 {code_raw} 的資料")
        return

    latest, chg, chg_pct, high_val, low_val = get_metrics(df)
    chg_class = "up" if chg >= 0 else "down"
    sign = "+" if chg >= 0 else ""

    inst = get_institutional(base_code)
    if inst:
        foreign, trust, dealer, total = inst
        def fmt_inst(v):
            color = "up" if v>0 else ("down" if v<0 else "neutral")
            s = "+" if v>0 else ""
            return f'<span class="{color}">{s}{v:,}</span>'
        inst_html = f"""
        <div class="inst-row">
          <div class="inst-box"><div class="inst-label">外資</div>{fmt_inst(foreign)}</div>
          <div class="inst-box"><div class="inst-label">投信</div>{fmt_inst(trust)}</div>
          <div class="inst-box"><div class="inst-label">自營商</div>{fmt_inst(dealer)}</div>
          <div class="inst-box"><div class="inst-label">合計淨買超</div>{fmt_inst(total)}</div>
        </div>"""
    else:
        inst_html = '<div style="color:#8b949e;font-size:.8rem;margin:6px 0">三大法人：今日資料尚未更新</div>'

    st.markdown(f"""
    <div class="stock-card">
      <div class="card-header">
        <span class="card-title">{name or code_raw}</span>
        <span class="card-code">{base_code}</span>
        <span class="card-sector">{sector or 'N/A'}</span>
      </div>
      <div class="metric-row">
        <div class="metric-box"><div class="metric-label">最新收盤</div><div class="metric-value {chg_class}">{latest:.2f}</div></div>
        <div class="metric-box"><div class="metric-label">漲跌</div><div class="metric-value {chg_class}">{sign}{chg:.2f}</div></div>
        <div class="metric-box"><div class="metric-label">漲跌幅</div><div class="metric-value {chg_class}">{sign}{chg_pct:.2f}%</div></div>
        <div class="metric-box"><div class="metric-label">區間最高</div><div class="metric-value up">{high_val:.2f}</div></div>
        <div class="metric-box"><div class="metric-label">區間最低</div><div class="metric-value down">{low_val:.2f}</div></div>
      </div>
      {inst_html}
    </div>
    """, unsafe_allow_html=True)

    fig = make_kline_chart(df, name or code_raw, base_code, sector, active_mas)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# Suggestions
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

# ── Render ───────────────────────────────────────────────────────────
if batch:
    st.markdown(f"### 📁 {st.session_state.cur_folder}")
    for c in batch:
        render_stock(c, period, active_mas)
elif st.session_state.get('do_analyze') and user_input:
    render_stock(user_input, period, active_mas)
    st.session_state.do_analyze = False
