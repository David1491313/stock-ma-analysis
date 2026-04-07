import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import warnings
warnings.filterwarnings('ignore')

# ── 深色金融風格 CSS ─────────────────────────────────────
st.set_page_config(page_title="台股均線分析", page_icon="📈", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; }
.stApp { background-color: #0d1117; color: #e6edf3; }
section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
section[data-testid="stSidebar"] * { color: #e6edf3 !important; }
.main-header { background: linear-gradient(135deg, #1a3a52 0%, #0d2137 100%);
    border: 1px solid #1f6feb; border-radius: 12px; padding: 20px 28px; margin-bottom: 20px; }
.main-header h1 { color: #58a6ff; font-size: 1.9rem; margin: 0; font-weight: 700; }
.main-header p  { color: #8b949e; margin: 6px 0 0 0; font-size: 0.9rem; }
.stock-card { background: #161b22; border: 1px solid #30363d; border-radius: 10px;
    padding: 16px 20px; margin-bottom: 14px; }
.stock-card .ticker { color: #58a6ff; font-size: 1.1rem; font-weight: 700; }
.stock-card .sname  { color: #8b949e; font-size: 0.85rem; margin-left: 6px; }
.stock-card .price  { color: #e6edf3; font-size: 2rem; font-weight: 700; margin: 4px 0; }
.tag-up   { background:#1a3a2a; color:#3fb950; border:1px solid #238636;
    border-radius:6px; padding:3px 10px; font-size:0.82rem; font-weight:600; display:inline-block; }
.tag-down { background:#3a1a1a; color:#f85149; border:1px solid #da3633;
    border-radius:6px; padding:3px 10px; font-size:0.82rem; font-weight:600; display:inline-block; }
.tag-mid  { background:#2a2a1a; color:#d29922; border:1px solid #9e6a03;
    border-radius:6px; padding:3px 10px; font-size:0.82rem; font-weight:600; display:inline-block; }
.ma-row  { display:flex; gap:10px; margin-top:10px; flex-wrap:wrap; }
.ma-chip { border-radius:6px; padding:4px 12px; font-size:0.8rem; font-weight:600; }
.ma-up   { background:#0d2818; color:#3fb950; border:1px solid #238636; }
.ma-down { background:#2d1117; color:#f85149; border:1px solid #da3633; }
.data-table { width:100%; border-collapse:collapse; font-size:0.88rem; margin-top:8px; }
.data-table th { background:#1c2128; color:#8b949e; padding:10px 14px;
    text-align:left; border-bottom:1px solid #30363d; font-weight:600; }
.data-table td { padding:10px 14px; border-bottom:1px solid #21262d; color:#e6edf3; }
.data-table tr:hover td { background:#1c2128; }
.up  { color:#3fb950; font-weight:600; }
.dn  { color:#f85149; font-weight:600; }
.section-title { color:#58a6ff; font-size:1.05rem; font-weight:700;
    border-left:3px solid #1f6feb; padding-left:10px; margin: 22px 0 14px 0; }
/* 搜尋框 */
.stTextInput input { background:#161b22 !important; color:#e6edf3 !important;
    border:1px solid #30363d !important; border-radius:8px !important; font-size:1rem !important; }
.stTextInput input:focus { border-color:#1f6feb !important; box-shadow:0 0 0 3px rgba(31,111,235,0.15) !important; }
.stTextArea textarea { background:#0d1117 !important; color:#e6edf3 !important;
    border:1px solid #30363d !important; border-radius:8px !important;
    font-size:1.05rem !important; }
.stSelectbox > div > div { background:#161b22 !important; border:1px solid #30363d !important; color:#e6edf3 !important; }
.stButton button { background:linear-gradient(135deg,#1f6feb,#388bfd) !important;
    color:#fff !important; border:none !important; border-radius:8px !important;
    font-size:1rem !important; font-weight:700 !important; padding:10px 0 !important; }
.stButton button:hover { opacity:0.88 !important; }
.search-result-item { background:#161b22; border:1px solid #30363d; border-radius:8px;
    padding:10px 16px; margin:4px 0; cursor:pointer; display:flex; align-items:center; gap:12px; }
.search-result-item:hover { border-color:#58a6ff; }
.search-code { color:#58a6ff; font-weight:700; font-size:1rem; min-width:52px; }
.search-name { color:#e6edf3; font-size:0.92rem; }
.search-type { color:#8b949e; font-size:0.78rem; background:#21262d;
    padding:2px 8px; border-radius:4px; margin-left:auto; }
#MainMenu, footer { visibility:hidden; }
header[data-testid="stHeader"] { background:transparent; }
</style>
""", unsafe_allow_html=True)

# ── 台股名稱資料庫（從政府 API 動態載入）──────────────────
@st.cache_data(ttl=86400)
def load_stock_list():
    """從 TWSE ISIN 抓取台股上市+上櫃名稱，每天更新一次。"""
    db = {}   # code -> (name, suffix)
    for mode, suffix in [("2", "TW"), ("4", "TWO")]:
        try:
            url = f"https://isin.twse.com.tw/isin/C_public.jsp?strMode={mode}"
            resp = requests.get(url, timeout=10,
                headers={"User-Agent": "Mozilla/5.0"})
            resp.encoding = "big5"
            from html.parser import HTMLParser
            class TDParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.in_td = False
                    self.data = []
                    self.cur = ""
                def handle_starttag(self, tag, attrs):
                    if tag == "td": self.in_td = True; self.cur = ""
                def handle_endtag(self, tag):
                    if tag == "td": self.in_td = False; self.data.append(self.cur.strip())
                def handle_data(self, data):
                    if self.in_td: self.cur += data
            parser = TDParser()
            parser.feed(resp.text)
            import re
            seen = set()
            for cell in parser.data:
                m = re.match(r'^(\d{4,5})\s+(.+)$', cell)
                if m and m.group(1) not in seen:
                    seen.add(m.group(1))
                    db[m.group(1)] = (m.group(2).strip(), suffix)
        except Exception:
            pass
    return db

STOCK_DB = load_stock_list()

def get_stock_name(code):
    if code in STOCK_DB:
        return STOCK_DB[code][0]
    return ""

def search_stocks(query):
    """搜尋：支援代碼數字 or 中文名稱模糊比對"""
    query = query.strip()
    if not query:
        return []
    results = []
    q_lower = query.lower()
    for code, (name, suffix) in STOCK_DB.items():
        if code.startswith(query) or query in name:
            results.append((code, name, suffix))
    results.sort(key=lambda x: (not x[0].startswith(query), x[0]))
    return results[:20]

def resolve_ticker(code_raw: str) -> str:
    code = code_raw.strip().upper()
    if '.' in code:
        return code
    if code.isdigit():
        if code in STOCK_DB:
            return code + '.' + STOCK_DB[code][1]
        return code + '.TW'
    return code

# ── Header ──────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>📈 台股均線分析站</h1>
  <p>支援中文名稱搜尋・自動辨識上市/上櫃・即時查看 MA5 / MA10 / MA20 均線強弱</p>
</div>
""", unsafe_allow_html=True)

# ── 分析函式 ────────────────────────────────────────────
def get_close(df):
    if isinstance(df.columns, pd.MultiIndex):
        cols = [c for c in df.columns if c[0] == 'Close']
        if cols: return df[cols[0]]
        df.columns = df.columns.get_level_values(0)
    return df['Close']

def analyze(code_raw, period):
    ticker = resolve_ticker(code_raw)
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if df.empty or len(df) < 20:
            return None, None, f"{code_raw}：資料不足（至少需20個交易日）"
        close = get_close(df)
        d = pd.DataFrame({'Close': close})
        d['MA5']  = d['Close'].rolling(5).mean()
        d['MA10'] = d['Close'].rolling(10).mean()
        d['MA20'] = d['Close'].rolling(20).mean()
        d = d.dropna()
        lat = d.iloc[-1]
        c, m5, m10, m20 = float(lat['Close']), float(lat['MA5']), float(lat['MA10']), float(lat['MA20'])
        def pct(p,m): return (p-m)/m*100
        def arrow(p,m): return "▲" if p>m else "▼"
        code_clean = code_raw.split('.')[0].upper()
        sname = get_stock_name(code_clean) if code_clean.isdigit() else ""
        row = {
            '_code': code_clean, '_ticker': ticker, '_sname': sname,
            '_close':c, '_m5':m5, '_m10':m10, '_m20':m20,
            '代碼': code_clean, '名稱': sname, '最新收盤': round(c,2),
            'MA5': round(m5,2), 'MA10': round(m10,2), 'MA20': round(m20,2),
            'vs MA5':  f"{'🟢 站上' if c>m5  else '🔴 跌破'} {arrow(c,m5)}  ({pct(c,m5):+.2f}%)",
            'vs MA10': f"{'🟢 站上' if c>m10 else '🔴 跌破'} {arrow(c,m10)} ({pct(c,m10):+.2f}%)",
            'vs MA20': f"{'🟢 站上' if c>m20 else '🔴 跌破'} {arrow(c,m20)} ({pct(c,m20):+.2f}%)",
        }
        return row, d, None
    except Exception as e:
        return None, None, f"{code_raw}：{e}"

# ── 側邊欄 ──────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-title">🔍 搜尋股票</div>', unsafe_allow_html=True)

    search_q = st.text_input(
        "",
        placeholder="輸入代碼或中文名稱，例：台積電 / 8086",
        label_visibility="collapsed"
    )

    # 即時搜尋結果
    if search_q.strip():
        hits = search_stocks(search_q)
        if hits:
            st.markdown(f'<div style="color:#8b949e;font-size:0.8rem;margin-bottom:6px">找到 {len(hits)} 筆結果（點擊加入查詢清單）</div>', unsafe_allow_html=True)
            if 'watchlist' not in st.session_state:
                st.session_state.watchlist = []
            for code, name, suffix in hits:
                col1, col2 = st.columns([4,1])
                with col1:
                    st.markdown(f"""<div class="search-result-item">
                      <span class="search-code">{code}</span>
                      <span class="search-name">{name}</span>
                      <span class="search-type">{'上市' if suffix=='TW' else '上櫃'}</span>
                    </div>""", unsafe_allow_html=True)
                with col2:
                    if st.button("＋", key=f"add_{code}"):
                        if code not in st.session_state.watchlist:
                            st.session_state.watchlist.append(code)
                            st.rerun()
        else:
            st.markdown('<div style="color:#f85149;font-size:0.85rem;padding:8px">查無結果，請確認輸入</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-title">📋 查詢清單</div>', unsafe_allow_html=True)

    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = ['8086','2455','6138','2330']

    # 顯示目前清單
    to_remove = None
    for code in st.session_state.watchlist:
        name = get_stock_name(code)
        c1, c2 = st.columns([5,1])
        with c1:
            st.markdown(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:6px 12px;margin:3px 0"><span style="color:#58a6ff;font-weight:700">{code}</span><span style="color:#8b949e;font-size:0.85rem;margin-left:8px">{name}</span></div>', unsafe_allow_html=True)
        with c2:
            if st.button("✕", key=f"rm_{code}"):
                to_remove = code
    if to_remove:
        st.session_state.watchlist.remove(to_remove)
        st.rerun()

    # 手動新增
    manual = st.text_input("直接輸入代碼（Enter 加入）", placeholder="如：2330", label_visibility="visible", key="manual_add")
    if manual.strip():
        code_m = manual.strip().split('.')[0]
        if code_m not in st.session_state.watchlist:
            st.session_state.watchlist.append(code_m)
            st.rerun()

    st.markdown("---")
    period = st.selectbox("查詢區間", ["30d","60d","90d","180d","1y"], index=1,
        format_func=lambda x: {"30d":"近30天","60d":"近60天","90d":"近90天","180d":"近半年","1y":"近1年"}[x])
    run = st.button("🔍  開始分析", use_container_width=True)

    st.markdown(f"""
<div style='color:#8b949e;font-size:0.78rem;margin-top:8px;line-height:1.7'>
資料庫：{len(STOCK_DB)} 檔股票<br>
支援：台股代碼 / 中文名稱 / 美股代碼
</div>""", unsafe_allow_html=True)

# ── 主畫面 ──────────────────────────────────────────────
if run and st.session_state.watchlist:
    codes = st.session_state.watchlist
    results, dfs, errors = [], {}, []
    bar = st.progress(0, text="資料下載中...")
    for i, code in enumerate(codes):
        bar.progress((i+1)/len(codes), text=f"正在分析 {code}  {get_stock_name(code)}...")
        row, df, err = analyze(code, period)
        if row: results.append(row); dfs[code] = df
        if err:  errors.append(err)
    bar.empty()

    if errors:
        for e in errors:
            st.markdown(f'<div style="background:#3a1a1a;border:1px solid #da3633;border-radius:8px;padding:10px 14px;color:#f85149;margin:6px 0">⚠️ {e}</div>', unsafe_allow_html=True)

    if results:
        # 股票卡片
        st.markdown('<div class="section-title">📊 均線強弱總覽</div>', unsafe_allow_html=True)
        cols = st.columns(min(len(results), 4))
        for i, r in enumerate(results):
            a5  = r['_close'] > r['_m5']
            a10 = r['_close'] > r['_m10']
            a20 = r['_close'] > r['_m20']
            cnt = sum([a5,a10,a20])
            if cnt==3:   tag='<span class="tag-up">✅ 三線全站上（強勢）</span>'; bc='border-color:#238636'
            elif cnt==0: tag='<span class="tag-down">❌ 三線全跌破（弱勢）</span>'; bc='border-color:#da3633'
            else:        tag=f'<span class="tag-mid">⚡ {cnt}/3 線站上（整理中）</span>'; bc='border-color:#9e6a03'
            def chip(label, p, m):
                cls = "ma-up" if p>m else "ma-down"
                return f'<span class="ma-chip {cls}">{label} {"▲" if p>m else "▼"} ({(p-m)/m*100:+.1f}%)</span>'
            with cols[i % len(cols)]:
                st.markdown(f"""
<div class="stock-card" style="{bc}">
  <div><span class="ticker">{r['代碼']}</span><span class="sname">{r['名稱']}</span></div>
  <div class="price">$ {r['最新收盤']}</div>
  {tag}
  <div class="ma-row">{chip('MA5',r['_close'],r['_m5'])}{chip('MA10',r['_close'],r['_m10'])}{chip('MA20',r['_close'],r['_m20'])}</div>
</div>""", unsafe_allow_html=True)

        # 詳細表格
        st.markdown('<div class="section-title">📋 詳細數據</div>', unsafe_allow_html=True)
        rows_html = ""
        for r in results:
            def td_vs(v): cls="up" if "站上" in v else "dn"; return f'<td class="{cls}">{v}</td>'
            rows_html += f"<tr><td><b style='color:#58a6ff'>{r['代碼']}</b></td><td style='color:#8b949e'>{r['名稱']}</td><td><b>{r['最新收盤']}</b></td><td>{r['MA5']}</td><td>{r['MA10']}</td><td>{r['MA20']}</td>{td_vs(r['vs MA5'])}{td_vs(r['vs MA10'])}{td_vs(r['vs MA20'])}</tr>"
        st.markdown(f"""<table class="data-table"><thead><tr>
          <th>代碼</th><th>名稱</th><th>收盤</th><th>MA5</th><th>MA10</th><th>MA20</th>
          <th>vs MA5</th><th>vs MA10</th><th>vs MA20</th></tr></thead>
          <tbody>{rows_html}</tbody></table>""", unsafe_allow_html=True)

        # 走勢圖
        st.markdown('<div class="section-title">📉 均線走勢圖</div>', unsafe_allow_html=True)
        matplotlib.rcParams.update({
            'figure.facecolor':'#0d1117','axes.facecolor':'#161b22',
            'axes.edgecolor':'#30363d','axes.labelcolor':'#8b949e',
            'xtick.color':'#8b949e','ytick.color':'#8b949e',
            'grid.color':'#21262d','grid.linewidth':0.8,
            'text.color':'#e6edf3','legend.facecolor':'#1c2128',
            'legend.edgecolor':'#30363d','font.family':'DejaVu Sans',
        })
        n = len(dfs)
        cols_n = min(2, n)
        rows_n = (n + cols_n - 1) // cols_n
        fig, axes = plt.subplots(rows_n, cols_n, figsize=(16, 5*rows_n))
        if n==1: axes=[axes]
        elif rows_n==1: axes=list(axes)
        else: axes=[ax for ra in axes for ax in ra]
        COLORS = {'Close':'#e6edf3','MA5':'#58a6ff','MA10':'#f0883e','MA20':'#bc8cff'}
        for i,(code,df) in enumerate(dfs.items()):
            ax = axes[i]
            ax.plot(df.index,df['Close'],label='收盤',color=COLORS['Close'],lw=1.6,zorder=4)
            ax.plot(df.index,df['MA5'],  label='MA5', color=COLORS['MA5'],  lw=1.2,ls='--',zorder=3)
            ax.plot(df.index,df['MA10'], label='MA10',color=COLORS['MA10'], lw=1.2,ls='--',zorder=3)
            ax.plot(df.index,df['MA20'], label='MA20',color=COLORS['MA20'], lw=1.2,ls='--',zorder=3)
            lc = float(df['Close'].iloc[-1])
            ax.scatter(df.index[-1],lc,color='#f0f6fc',s=55,zorder=5)
            ax.annotate(f'  {lc:.1f}',(df.index[-1],lc),color='#f0f6fc',fontsize=9,va='center')
            sname = get_stock_name(code)
            title = f"{code} {sname}" if sname else resolve_ticker(code)
            ax.set_title(title,color='#58a6ff',fontsize=12,fontweight='bold',pad=8)
            ax.legend(fontsize=8,ncol=4,loc='upper left')
            ax.grid(True,alpha=0.6)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.tick_params(axis='x',rotation=30,labelsize=8)
            ax.tick_params(axis='y',labelsize=8)
            for sp in ax.spines.values(): sp.set_edgecolor('#30363d')
        for j in range(i+1,len(axes)): axes[j].set_visible(False)
        plt.tight_layout(pad=2.5)
        st.pyplot(fig)

elif not run:
    st.markdown("""
<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
            padding:32px;text-align:center;margin-top:16px">
  <div style="font-size:3rem">📊</div>
  <div style="color:#58a6ff;font-size:1.2rem;font-weight:700;margin:12px 0 8px">
    用左側搜尋框輸入中文股名或代碼
  </div>
  <div style="color:#8b949e">加入查詢清單後按「開始分析」</div>
</div>
<br>
<div class="section-title">🔥 熱門股票</div>
""", unsafe_allow_html=True)
    popular=[("2330","台積電"),("2317","鴻海"),("2454","聯發科"),
             ("2303","聯電"),("2382","廣達"),("3008","大立光"),
             ("8086","宏捷科"),("2455","全新"),("6138","聯亞")]
    cols=st.columns(3)
    for idx,(code,name) in enumerate(popular):
        with cols[idx%3]:
            st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;
border-radius:8px;padding:12px 16px;margin-bottom:10px">
<span style="color:#58a6ff;font-weight:700;font-size:1rem">{code}</span>
<span style="color:#8b949e;font-size:0.88rem;margin-left:8px">{name}</span>
</div>""", unsafe_allow_html=True)
else:
    st.warning("請先在左側搜尋並加入股票到查詢清單")
