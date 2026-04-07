import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
warnings.filterwarnings('ignore')

# ── 深色金融風格 ──────────────────────────────────────────
st.set_page_config(page_title="台股均線分析", page_icon="📈", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; }

/* 整體背景 */
.stApp { background-color: #0d1117; color: #e6edf3; }
section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
section[data-testid="stSidebar"] * { color: #e6edf3 !important; }

/* 主標題 */
.main-header {
    background: linear-gradient(135deg, #1a3a52 0%, #0d2137 100%);
    border: 1px solid #1f6feb;
    border-radius: 12px;
    padding: 20px 28px;
    margin-bottom: 20px;
}
.main-header h1 { color: #58a6ff; font-size: 1.9rem; margin: 0; font-weight: 700; }
.main-header p { color: #8b949e; margin: 6px 0 0 0; font-size: 0.9rem; }

/* 股票卡片 */
.stock-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 14px;
    transition: border-color 0.2s;
}
.stock-card:hover { border-color: #58a6ff; }
.stock-card .ticker { color: #58a6ff; font-size: 1.1rem; font-weight: 700; }
.stock-card .price { color: #e6edf3; font-size: 2rem; font-weight: 700; margin: 4px 0; }
.stock-card .tag-up { background:#1a3a2a; color:#3fb950; border:1px solid #238636;
    border-radius:6px; padding:3px 10px; font-size:0.82rem; font-weight:600; display:inline-block; }
.stock-card .tag-down { background:#3a1a1a; color:#f85149; border:1px solid #da3633;
    border-radius:6px; padding:3px 10px; font-size:0.82rem; font-weight:600; display:inline-block; }
.stock-card .tag-mid { background:#2a2a1a; color:#d29922; border:1px solid #9e6a03;
    border-radius:6px; padding:3px 10px; font-size:0.82rem; font-weight:600; display:inline-block; }

/* MA 指標 */
.ma-row { display:flex; gap:10px; margin-top:10px; flex-wrap:wrap; }
.ma-chip { border-radius:6px; padding:4px 12px; font-size:0.8rem; font-weight:600; }
.ma-up   { background:#0d2818; color:#3fb950; border:1px solid #238636; }
.ma-down { background:#2d1117; color:#f85149; border:1px solid #da3633; }

/* 表格 */
.data-table { width:100%; border-collapse:collapse; font-size:0.88rem; margin-top:8px; }
.data-table th { background:#1c2128; color:#8b949e; padding:10px 14px;
    text-align:left; border-bottom:1px solid #30363d; font-weight:600; }
.data-table td { padding:10px 14px; border-bottom:1px solid #21262d; color:#e6edf3; }
.data-table tr:hover td { background:#1c2128; }
.up { color:#3fb950; font-weight:600; }
.dn { color:#f85149; font-weight:600; }

/* 區塊標題 */
.section-title {
    color:#58a6ff; font-size:1.05rem; font-weight:700;
    border-left:3px solid #1f6feb; padding-left:10px;
    margin: 22px 0 14px 0;
}

/* Input 美化 */
.stTextArea textarea {
    background:#0d1117 !important; color:#e6edf3 !important;
    border:1px solid #30363d !important; border-radius:8px !important;
    font-size:1.1rem !important; font-family:'Noto Sans TC',monospace !important;
}
.stTextArea textarea:focus { border-color:#1f6feb !important; box-shadow:0 0 0 3px rgba(31,111,235,0.15) !important; }
.stSelectbox > div > div { background:#161b22 !important; border:1px solid #30363d !important; color:#e6edf3 !important; }
.stButton button {
    background:linear-gradient(135deg,#1f6feb,#388bfd) !important;
    color:#fff !important; border:none !important; border-radius:8px !important;
    font-size:1rem !important; font-weight:700 !important; padding:10px 0 !important;
    transition:all 0.2s !important;
}
.stButton button:hover { opacity:0.88 !important; transform:translateY(-1px) !important; }
.stAlert { background:#161b22 !important; border-color:#30363d !important; }

/* 隱藏 Streamlit 預設元素 */
#MainMenu, footer { visibility:hidden; }
header[data-testid="stHeader"] { background:transparent; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>📈 台股均線分析站</h1>
  <p>輸入股票代碼，即時查看 MA5 / MA10 / MA20 均線強弱判斷</p>
</div>
""", unsafe_allow_html=True)

# ── 自動補後綴 ──────────────────────────────────────────
TWSE_PREFIXES = set()   # 上市代碼特徵：一般4碼數字
OTC_CODES = {           # 常見上櫃代碼（可自行擴充）
    '8086','6138','3105','4743','6547','6523','6510','4966','3529','6278',
    '8044','8083','3661','6548','4927','3008','6196','3533','3552','4966',
}

def resolve_ticker(code: str) -> str:
    code = code.strip().upper()
    # 已有後綴直接回傳
    if code.endswith('.TW') or code.endswith('.TWO') or '.' in code:
        return code
    # 純數字代碼 -> 判斷上市/上櫃
    if code.isdigit():
        if code in OTC_CODES:
            return code + '.TWO'
        return code + '.TW'
    # 英文代碼（美股）直接回傳
    return code

# ── 側邊欄 ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-title">⚙️ 查詢設定</div>', unsafe_allow_html=True)
    raw_input = st.text_area(
        "股票代碼",
        value="8086\n2455\n6138\n2330",
        height=160,
        placeholder="每行一個代碼\n例：2330  8086  TSM",
        help="直接輸入台股代碼，不需要加 .TW"
    )
    period = st.selectbox("查詢區間", ["30d","60d","90d","180d","1y"], index=1,
        format_func=lambda x: {"30d":"近30天","60d":"近60天","90d":"近90天",
                                "180d":"近半年","1y":"近1年"}[x])
    run = st.button("🔍  開始分析", use_container_width=True)

    st.markdown("---")
    st.markdown("""
<div style='color:#8b949e; font-size:0.82rem; line-height:1.8'>
<b style='color:#58a6ff'>📌 使用說明</b><br>
• 直接輸入代碼即可，不需 .TW<br>
• 上櫃股票會自動辨識<br>
• 美股輸入英文代碼（如 TSLA）<br>
• 每行一個，或用空白/逗號分隔
</div>
""", unsafe_allow_html=True)

# ── 分析函式 ───────────────────────────────────────────
def get_close(df):
    if isinstance(df.columns, pd.MultiIndex):
        cols = [c for c in df.columns if c[0] == 'Close']
        if cols:
            return df[cols[0]]
        df.columns = df.columns.get_level_values(0)
    return df['Close']

def analyze(ticker_raw, period):
    ticker = resolve_ticker(ticker_raw)
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if df.empty or len(df) < 20:
            return None, None, f"{ticker_raw}（{ticker}）：資料不足"
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
        row = {
            '_ticker_raw': ticker_raw,
            '_ticker': ticker,
            '代碼': ticker_raw.upper(),
            '最新收盤': round(c,2),
            'MA5':  round(m5,2), 'MA10': round(m10,2), 'MA20': round(m20,2),
            'vs MA5':  f"{'🟢 站上' if c>m5  else '🔴 跌破'} {arrow(c,m5)}  ({pct(c,m5):+.2f}%)",
            'vs MA10': f"{'🟢 站上' if c>m10 else '🔴 跌破'} {arrow(c,m10)} ({pct(c,m10):+.2f}%)",
            'vs MA20': f"{'🟢 站上' if c>m20 else '🔴 跌破'} {arrow(c,m20)} ({pct(c,m20):+.2f}%)",
            '_close':c,'_m5':m5,'_m10':m10,'_m20':m20,
        }
        return row, d, None
    except Exception as e:
        return None, None, f"{ticker_raw}：{e}"

# ── 執行 ───────────────────────────────────────────────
if run:
    # 解析輸入
    import re
    raw_codes = re.split(r'[,\s\n]+', raw_input.strip())
    codes = [c.strip() for c in raw_codes if c.strip()]
    if not codes:
        st.warning("請輸入至少一個代碼")
    else:
        results, dfs, errors = [], {}, []
        bar = st.progress(0, text="資料下載中...")
        for i, code in enumerate(codes):
            bar.progress((i+1)/len(codes), text=f"正在分析 {code}...")
            row, df, err = analyze(code, period)
            if row: results.append(row); dfs[code] = df
            if err:  errors.append(err)
        bar.empty()

        if errors:
            for e in errors:
                st.markdown(f'<div style="background:#3a1a1a;border:1px solid #da3633;border-radius:8px;padding:10px 14px;color:#f85149;margin:6px 0">⚠️ {e}</div>', unsafe_allow_html=True)

        if results:
            # ── 股票卡片 ───────────────────────────────
            st.markdown('<div class="section-title">📊 均線強弱總覽</div>', unsafe_allow_html=True)
            cols = st.columns(min(len(results), 4))
            for i, r in enumerate(results):
                a5  = r['_close'] > r['_m5']
                a10 = r['_close'] > r['_m10']
                a20 = r['_close'] > r['_m20']
                cnt = sum([a5,a10,a20])
                if cnt==3:   status_tag='<span class="tag-up">✅ 三線全站上（強勢）</span>'; border='border-color:#238636'
                elif cnt==0: status_tag='<span class="tag-down">❌ 三線全跌破（弱勢）</span>'; border='border-color:#da3633'
                else:        status_tag=f'<span class="tag-mid">⚡ {cnt}/3 線站上（整理中）</span>'; border='border-color:#9e6a03'

                def chip(label, p, m):
                    cls = "ma-up" if p>m else "ma-down"
                    arr = "▲" if p>m else "▼"
                    pct_val = (p-m)/m*100
                    return f'<span class="ma-chip {cls}">{label} {arr} ({pct_val:+.1f}%)</span>'

                html = f"""
<div class="stock-card" style="{border}">
  <div class="ticker">{r['代碼']} <span style="color:#8b949e;font-size:0.8rem;font-weight:400">（{r['_ticker']}）</span></div>
  <div class="price">$ {r['最新收盤']}</div>
  {status_tag}
  <div class="ma-row">
    {chip('MA5',  r['_close'], r['_m5'])}
    {chip('MA10', r['_close'], r['_m10'])}
    {chip('MA20', r['_close'], r['_m20'])}
  </div>
</div>"""
                with cols[i % len(cols)]:
                    st.markdown(html, unsafe_allow_html=True)

            # ── 詳細數字表格 ───────────────────────────
            st.markdown('<div class="section-title">📋 詳細數據</div>', unsafe_allow_html=True)
            rows_html = ""
            for r in results:
                def td_vs(val):
                    cls = "up" if "站上" in val else "dn"
                    return f'<td class="{cls}">{val}</td>'
                rows_html += f"""<tr>
                  <td><b style="color:#58a6ff">{r['代碼']}</b></td>
                  <td><b>{r['最新收盤']}</b></td>
                  <td>{r['MA5']}</td><td>{r['MA10']}</td><td>{r['MA20']}</td>
                  {td_vs(r['vs MA5'])}{td_vs(r['vs MA10'])}{td_vs(r['vs MA20'])}
                </tr>"""
            st.markdown(f"""
<table class="data-table">
<thead><tr>
  <th>代碼</th><th>收盤</th><th>MA5</th><th>MA10</th><th>MA20</th>
  <th>vs MA5</th><th>vs MA10</th><th>vs MA20</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>""", unsafe_allow_html=True)

            # ── 走勢圖 ────────────────────────────────
            st.markdown('<div class="section-title">📉 均線走勢圖</div>', unsafe_allow_html=True)
            matplotlib.rcParams.update({
                'figure.facecolor':  '#0d1117',
                'axes.facecolor':    '#161b22',
                'axes.edgecolor':    '#30363d',
                'axes.labelcolor':   '#8b949e',
                'xtick.color':       '#8b949e',
                'ytick.color':       '#8b949e',
                'grid.color':        '#21262d',
                'grid.linewidth':    0.8,
                'text.color':        '#e6edf3',
                'legend.facecolor':  '#1c2128',
                'legend.edgecolor':  '#30363d',
                'font.family':       'DejaVu Sans',
            })
            n = len(dfs)
            cols_n = min(2, n)
            rows_n = (n + cols_n - 1) // cols_n
            fig, axes = plt.subplots(rows_n, cols_n, figsize=(16, 5*rows_n))
            if n == 1:   axes = [axes]
            elif rows_n == 1: axes = list(axes)
            else: axes = [ax for row_a in axes for ax in row_a]

            COLORS = {'Close':'#e6edf3','MA5':'#58a6ff','MA10':'#f0883e','MA20':'#bc8cff'}
            for i,(code,df) in enumerate(dfs.items()):
                ax = axes[i]
                ax.plot(df.index, df['Close'], label='收盤', color=COLORS['Close'], lw=1.6, zorder=4)
                ax.plot(df.index, df['MA5'],   label='MA5',  color=COLORS['MA5'],   lw=1.2, ls='--', zorder=3)
                ax.plot(df.index, df['MA10'],  label='MA10', color=COLORS['MA10'],  lw=1.2, ls='--', zorder=3)
                ax.plot(df.index, df['MA20'],  label='MA20', color=COLORS['MA20'],  lw=1.2, ls='--', zorder=3)
                lc = float(df['Close'].iloc[-1])
                ax.scatter(df.index[-1], lc, color='#f0f6fc', s=55, zorder=5)
                ax.annotate(f'  {lc:.1f}', (df.index[-1], lc),
                    color='#f0f6fc', fontsize=9, va='center')
                ax.set_title(resolve_ticker(code), color='#58a6ff', fontsize=12, fontweight='bold', pad=8)
                ax.legend(fontsize=8, ncol=4, loc='upper left')
                ax.grid(True, alpha=0.6)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                ax.tick_params(axis='x', rotation=30, labelsize=8)
                ax.tick_params(axis='y', labelsize=8)
                for spine in ax.spines.values(): spine.set_edgecolor('#30363d')

            for j in range(i+1, len(axes)):
                axes[j].set_visible(False)
            plt.tight_layout(pad=2.5)
            st.pyplot(fig)
else:
    # ── 首頁提示 ──────────────────────────────────────
    st.markdown("""
<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
            padding:32px;text-align:center;margin-top:16px">
  <div style="font-size:3rem">📊</div>
  <div style="color:#58a6ff;font-size:1.2rem;font-weight:700;margin:12px 0 8px">
    在左側輸入股票代碼，然後按「開始分析」
  </div>
  <div style="color:#8b949e;font-size:0.9rem">直接輸入數字代碼即可，不需要加 .TW</div>
</div>
<br>
<div class="section-title">🔥 熱門股票參考</div>
""", unsafe_allow_html=True)
    popular = [
        ("2330","台積電"),("2317","鴻海"),("2454","聯發科"),
        ("2303","聯電"), ("2382","廣達"),("3008","大立光"),
        ("8086","宏捷科"),("2455","全新"), ("6138","聯亞"),
    ]
    cols = st.columns(3)
    for idx,(code,name) in enumerate(popular):
        with cols[idx % 3]:
            st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;
            padding:12px 16px;margin-bottom:10px;cursor:pointer">
  <span style="color:#58a6ff;font-weight:700;font-size:1rem">{code}</span>
  <span style="color:#8b949e;font-size:0.88rem;margin-left:8px">{name}</span>
</div>""", unsafe_allow_html=True)
