import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="台股均線分析", page_icon="📈", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
html,body,[class*="css"]{font-family:'Noto Sans TC',sans-serif;}
.stApp{background:#0d1117;color:#e6edf3;}
section[data-testid="stSidebar"]{background:#161b22;border-right:1px solid #30363d;}
section[data-testid="stSidebar"] *{color:#e6edf3 !important;}
.main-header{background:linear-gradient(135deg,#1a3a52,#0d2137);border:1px solid #1f6feb;border-radius:12px;padding:20px 28px;margin-bottom:20px;}
.main-header h1{color:#58a6ff;font-size:1.9rem;margin:0;font-weight:700;}
.main-header p{color:#8b949e;margin:6px 0 0 0;font-size:.9rem;}
.stock-card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px 20px;margin-bottom:14px;}
.ticker{color:#58a6ff;font-size:1.1rem;font-weight:700;}.sname{color:#e6edf3;font-size:.9rem;margin-left:6px;}
.group-badge{background:#1c2128;color:#8b949e;font-size:.75rem;border:1px solid #30363d;border-radius:4px;padding:2px 8px;margin-left:8px;vertical-align:middle;}
.price{color:#e6edf3;font-size:2rem;font-weight:700;margin:4px 0;}
.tag-up{background:#1a3a2a;color:#3fb950;border:1px solid #238636;border-radius:6px;padding:3px 10px;font-size:.82rem;font-weight:600;display:inline-block;}
.tag-down{background:#3a1a1a;color:#f85149;border:1px solid #da3633;border-radius:6px;padding:3px 10px;font-size:.82rem;font-weight:600;display:inline-block;}
.tag-mid{background:#2a2a1a;color:#d29922;border:1px solid #9e6a03;border-radius:6px;padding:3px 10px;font-size:.82rem;font-weight:600;display:inline-block;}
.ma-row{display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;}
.ma-chip{border-radius:6px;padding:4px 12px;font-size:.8rem;font-weight:600;}
.ma-up{background:#0d2818;color:#3fb950;border:1px solid #238636;}
.ma-down{background:#2d1117;color:#f85149;border:1px solid #da3633;}
.data-table{width:100%;border-collapse:collapse;font-size:.88rem;margin-top:8px;}
.data-table th{background:#1c2128;color:#8b949e;padding:10px 14px;text-align:left;border-bottom:1px solid #30363d;font-weight:600;}
.data-table td{padding:10px 14px;border-bottom:1px solid #21262d;color:#e6edf3;}
.data-table tr:hover td{background:#1c2128;}
.up{color:#3fb950;font-weight:600;}.dn{color:#f85149;font-weight:600;}
.section-title{color:#58a6ff;font-size:1.05rem;font-weight:700;border-left:3px solid #1f6feb;padding-left:10px;margin:22px 0 14px 0;}
.hit-item{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:9px 14px;margin:3px 0;display:flex;align-items:center;gap:8px;cursor:pointer;}
.hit-code{color:#58a6ff;font-weight:700;min-width:52px;font-size:.9rem;}
.hit-name{color:#e6edf3;font-size:.88rem;flex:1;}
.hit-group{color:#8b949e;font-size:.72rem;background:#21262d;padding:2px 6px;border-radius:4px;white-space:nowrap;}
.hit-mkt{color:#8b949e;font-size:.72rem;background:#21262d;padding:2px 6px;border-radius:4px;}
.stTextInput input{background:#161b22 !important;color:#e6edf3 !important;border:1px solid #30363d !important;border-radius:8px !important;font-size:1rem !important;}
.stTextInput input:focus{border-color:#1f6feb !important;}
.stSelectbox>div>div{background:#161b22 !important;border:1px solid #30363d !important;color:#e6edf3 !important;}
.stButton button{background:linear-gradient(135deg,#1f6feb,#388bfd) !important;color:#fff !important;border:none !important;border-radius:8px !important;font-size:1rem !important;font-weight:700 !important;padding:10px 0 !important;}
.stButton button:hover{opacity:.88 !important;}
#MainMenu,footer{visibility:hidden;}
header[data-testid="stHeader"]{background:transparent;}
</style>
""", unsafe_allow_html=True)

# ── 台股資料庫：使用 twstock 套件 ──────────────────────────
@st.cache_data(ttl=3600*12, show_spinner=False)
def load_stock_db():
    db = {}
    try:
        import twstock
        for code, stock in twstock.codes.items():
            if not code.isdigit():
                continue
            name   = getattr(stock, 'name',   '') or ''
            market = getattr(stock, 'market', '') or ''
            group  = getattr(stock, 'group',  '') or ''
            if '上市' in market or market == 'TWSE':
                sfx = 'TW'
            elif '上櫃' in market or market in ('OTC','TPEx'):
                sfx = 'TWO'
            else:
                sfx = 'TW'
            db[code] = (name, sfx, group)
    except Exception:
        pass

    if not db:
        fallback = {
            "1101":("台泥","TW","水泥工業"),
            "1216":("統一","TW","食品工業"),
            "1301":("台塑","TW","塑膠工業"),
            "1303":("南亞","TW","塑膠工業"),
            "2002":("中鋼","TW","鋼鐵工業"),
            "2303":("聯電","TW","半導體業"),
            "2308":("台達電","TW","電子零組件業"),
            "2317":("鴻海","TW","電子零組件業"),
            "2330":("台積電","TW","半導體業"),
            "2382":("廣達","TW","電腦及週邊設備業"),
            "2412":("中華電","TW","通信網路業"),
            "2454":("聯發科","TW","半導體業"),
            "2603":("長榮","TW","航運業"),
            "2881":("富邦金","TW","金融保險業"),
            "2882":("國泰金","TW","金融保險業"),
            "3008":("大立光","TW","光電業"),
            "3034":("聯詠","TW","半導體業"),
            "4938":("和碩","TW","電腦及週邊設備業"),
            "6505":("台塑化","TW","油電燃氣業"),
            "8086":("宏捷科","TWO","半導體業"),
            "2455":("全新","TWO","半導體業"),
            "6138":("聯亞","TWO","半導體業"),
        }
        db = fallback
    return db

STOCK_DB = load_stock_db()

def get_info(code):
    v = STOCK_DB.get(code, ("","TW",""))
    if isinstance(v, tuple):
        name  = v[0] if len(v) > 0 else ""
        sfx   = v[1] if len(v) > 1 else "TW"
        group = v[2] if len(v) > 2 else ""
        return name, sfx, group
    return v, "TW", ""

def get_name(code):   return get_info(code)[0]
def get_suffix(code): return get_info(code)[1]
def get_group(code):  return get_info(code)[2]

def search_stocks(query):
    q = query.strip()
    if not q: return []
    out = []
    for code, val in STOCK_DB.items():
        if isinstance(val, tuple):
            name  = val[0] if len(val) > 0 else ""
            sfx   = val[1] if len(val) > 1 else "TW"
            group = val[2] if len(val) > 2 else ""
        else:
            name, sfx, group = val, "TW", ""
        if code.startswith(q) or q in name:
            out.append((code, name, sfx, group))
    out.sort(key=lambda x: (
        x[0] != q,
        x[1] != q,
        len(x[0]) > 4,
        not x[0].startswith(q),
        x[0],
    ))
    return out[:20]

def resolve(raw):
    code = raw.strip().upper()
    if '.' in code: return code
    if code.isdigit():
        sfx = get_suffix(code) or "TW"
        return code + '.' + sfx
    return code

# ── Header ──────────────────────────────────────────────
st.markdown("""<div class="main-header">
  <h1>📈 台股均線分析站</h1>
  <p>支援中文名稱搜尋・自動辨識上市/上櫃・即時查看 MA5 / MA10 / MA20 均線強弱</p>
</div>""", unsafe_allow_html=True)

# ── Session state init ───────────────────────────────────
if 'wl' not in st.session_state:
    st.session_state.wl = ['8086','2455','6138','2330']
if 'do_analyze' not in st.session_state:
    st.session_state.do_analyze = False

# ── 分析函式 ────────────────────────────────────────────
def get_close(df):
    if isinstance(df.columns, pd.MultiIndex):
        cols = [c for c in df.columns if c[0] == 'Close']
        if cols: return df[cols[0]]
        df.columns = df.columns.get_level_values(0)
    return df['Close']

def analyze(code_raw, period):
    ticker = resolve(code_raw)
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if df.empty or len(df) < 20:
            return None, None, f"{code_raw}：資料不足（需至少20交易日）"
        close = get_close(df)
        d = pd.DataFrame({'Close': close})
        d['MA5']  = d['Close'].rolling(5).mean()
        d['MA10'] = d['Close'].rolling(10).mean()
        d['MA20'] = d['Close'].rolling(20).mean()
        d = d.dropna()
        lat = d.iloc[-1]
        c, m5, m10, m20 = float(lat['Close']), float(lat['MA5']), float(lat['MA10']), float(lat['MA20'])
        pct = lambda p, m: (p - m) / m * 100
        arr = lambda p, m: "▲" if p > m else "▼"
        code_c = code_raw.split('.')[0].upper()
        sname, _, grp = get_info(code_c) if code_c.isdigit() else ("", "TW", "")
        row = {
            '_code': code_c, '_ticker': ticker, '_sname': sname, '_group': grp,
            '_close': c, '_m5': m5, '_m10': m10, '_m20': m20,
            '代碼': code_c, '名稱': sname, '族群': grp, '最新收盤': round(c, 2),
            'MA5': round(m5,2), 'MA10': round(m10,2), 'MA20': round(m20,2),
            'vs MA5':  f"{'🟢 站上' if c>m5  else '🔴 跌破'} {arr(c,m5)}  ({pct(c,m5):+.2f}%)",
            'vs MA10': f"{'🟢 站上' if c>m10 else '🔴 跌破'} {arr(c,m10)} ({pct(c,m10):+.2f}%)",
            'vs MA20': f"{'🟢 站上' if c>m20 else '🔴 跌破'} {arr(c,m20)} ({pct(c,m20):+.2f}%)",
        }
        return row, d, None
    except Exception as e:
        return None, None, f"{code_raw}：{e}"

# ── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-title">🔍 搜尋股票</div>', unsafe_allow_html=True)
    db_n = len(STOCK_DB)
    st.markdown(f'<div style="color:#8b949e;font-size:.78rem;margin-bottom:8px">資料庫：{db_n} 檔股票</div>', unsafe_allow_html=True)

    search_q = st.text_input("", placeholder="輸入代碼或中文名稱，如：台積電 / 8086",
                             label_visibility="collapsed", key="search_input")

    if search_q.strip():
        hits = search_stocks(search_q)
        if hits:
            st.markdown(f'<div style="color:#8b949e;font-size:.78rem;margin-bottom:6px">找到 {len(hits)} 筆（點 ＋ 加入清單）</div>', unsafe_allow_html=True)
            for code, name, sfx, group in hits:
                c1, c2 = st.columns([5, 1])
                mkt = "上市" if sfx == "TW" else "上櫃"
                grp_html = f'<span class="hit-group">{group}</span>' if group else ''
                with c1:
                    st.markdown(
                        f'<div class="hit-item">'
                        f'<span class="hit-code">{code}</span>'
                        f'<span class="hit-name">{name}</span>'
                        f'{grp_html}'
                        f'<span class="hit-mkt">{mkt}</span>'
                        f'</div>',
                        unsafe_allow_html=True)
                with c2:
                    if st.button("＋", key=f"a_{code}"):
                        if code not in st.session_state.wl:
                            st.session_state.wl.append(code)
                        st.session_state.do_analyze = True
                        st.rerun()
        else:
            st.markdown('<div style="color:#f85149;font-size:.85rem;padding:6px">查無結果</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-title">📋 查詢清單</div>', unsafe_allow_html=True)
    rm = None
    for code in st.session_state.wl:
        name, _, grp = get_info(code)
        c1, c2 = st.columns([5, 1])
        with c1:
            grp_txt = f' · {grp}' if grp else ''
            st.markdown(
                f'<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;'
                f'padding:6px 12px;margin:2px 0">'
                f'<span style="color:#58a6ff;font-weight:700">{code}</span>'
                f'<span style="color:#e6edf3;font-size:.83rem;margin-left:8px">{name}</span>'
                f'<span style="color:#6e7681;font-size:.75rem">{grp_txt}</span>'
                f'</div>',
                unsafe_allow_html=True)
        with c2:
            if st.button("✕", key=f"r_{code}"):
                rm = code
    if rm:
        st.session_state.wl.remove(rm)
        st.rerun()

    manual = st.text_input("手動輸入代碼（Enter 加入並分析）", placeholder="如：2330", key="mi")
    if manual.strip():
        c = manual.strip().split('.')[0]
        if c not in st.session_state.wl:
            st.session_state.wl.append(c)
        st.session_state.do_analyze = True
        st.rerun()

    st.markdown("---")
    period = st.selectbox(
        "查詢區間", ["30d","60d","90d","180d","1y"], index=1,
        format_func=lambda x: {"30d":"近30天","60d":"近60天","90d":"近90天","180d":"近半年","1y":"近1年"}[x])

    run = st.button("🔍 開始分析", use_container_width=True)
    if run:
        st.session_state.do_analyze = True

# ── 觸發分析 ─────────────────────────────────────────────
do_run = st.session_state.do_analyze
if do_run:
    st.session_state.do_analyze = False   # reset

# ── Main ────────────────────────────────────────────────
if do_run and st.session_state.wl:
    results, dfs, errors = [], {}, []
    bar = st.progress(0, text="資料下載中…")
    for i, code in enumerate(st.session_state.wl):
        n = get_name(code)
        bar.progress((i+1)/len(st.session_state.wl), text=f"正在分析 {code} {n}…")
        row, df, err = analyze(code, period)
        if row: results.append(row); dfs[code] = df
        if err: errors.append(err)
    bar.empty()

    if errors:
        for e in errors:
            st.markdown(f'<div style="background:#3a1a1a;border:1px solid #da3633;border-radius:8px;padding:10px 14px;color:#f85149;margin:6px 0">⚠️ {e}</div>', unsafe_allow_html=True)

    if results:
        st.markdown('<div class="section-title">📊 均線強弱總覽</div>', unsafe_allow_html=True)
        cols = st.columns(min(len(results), 4))
        for i, r in enumerate(results):
            a5  = r['_close'] > r['_m5']
            a10 = r['_close'] > r['_m10']
            a20 = r['_close'] > r['_m20']
            cnt = sum([a5, a10, a20])
            if cnt == 3:
                tag = '<span class="tag-up">✅ 三線全站上（強勢）</span>'; bc = 'border-color:#238636'
            elif cnt == 0:
                tag = '<span class="tag-down">❌ 三線全跌破（弱勢）</span>'; bc = 'border-color:#da3633'
            else:
                tag = f'<span class="tag-mid">⚡ {cnt}/3 線站上（整理中）</span>'; bc = 'border-color:#9e6a03'

            def chip(lb, p, m):
                cl = "ma-up" if p > m else "ma-down"
                return f'<span class="ma-chip {cl}">{lb} {"▲" if p>m else "▼"} ({(p-m)/m*100:+.1f}%)</span>'

            grp_badge = f'<span class="group-badge">🏭 {r["_group"]}</span>' if r["_group"] else ''
            with cols[i % len(cols)]:
                st.markdown(f"""<div class="stock-card" style="{bc}">
  <div><span class="ticker">{r['代碼']}</span><span class="sname">{r['名稱']}</span>{grp_badge}</div>
  <div class="price">$ {r['最新收盤']}</div>{tag}
  <div class="ma-row">{chip('MA5',r['_close'],r['_m5'])}{chip('MA10',r['_close'],r['_m10'])}{chip('MA20',r['_close'],r['_m20'])}</div>
</div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-title">📋 詳細數據</div>', unsafe_allow_html=True)
        rh = ""
        for r in results:
            td = lambda v: f'<td class="{"up" if "站上" in v else "dn"}">{v}</td>'
            grp_cell = f'<span style="color:#8b949e;font-size:.8rem">{r["族群"]}</span>' if r["族群"] else ''
            rh += (f"<tr>"
                   f"<td><b style='color:#58a6ff'>{r['代碼']}</b></td>"
                   f"<td style='color:#e6edf3'>{r['名稱']}</td>"
                   f"<td>{grp_cell}</td>"
                   f"<td><b>{r['最新收盤']}</b></td>"
                   f"<td>{r['MA5']}</td><td>{r['MA10']}</td><td>{r['MA20']}</td>"
                   f"{td(r['vs MA5'])}{td(r['vs MA10'])}{td(r['vs MA20'])}"
                   f"</tr>")
        st.markdown(f"""<table class="data-table"><thead><tr>
<th>代碼</th><th>名稱</th><th>族群</th><th>收盤</th><th>MA5</th><th>MA10</th><th>MA20</th>
<th>vs MA5</th><th>vs MA10</th><th>vs MA20</th></tr></thead><tbody>{rh}</tbody></table>""", unsafe_allow_html=True)

        st.markdown('<div class="section-title">📉 均線走勢圖</div>', unsafe_allow_html=True)
        matplotlib.rcParams.update({
            'figure.facecolor':'#0d1117','axes.facecolor':'#161b22',
            'axes.edgecolor':'#30363d','axes.labelcolor':'#8b949e',
            'xtick.color':'#8b949e','ytick.color':'#8b949e',
            'grid.color':'#21262d','grid.linewidth':0.8,
            'text.color':'#e6edf3','legend.facecolor':'#1c2128',
            'legend.edgecolor':'#30363d','font.family':'DejaVu Sans'})
        n = len(dfs); cn = min(2, n); rn = (n + cn - 1) // cn
        fig, axes = plt.subplots(rn, cn, figsize=(16, 5*rn))
        if n == 1: axes = [axes]
        elif rn == 1: axes = list(axes)
        else: axes = [ax for ra in axes for ax in ra]
        CLR = {'Close':'#e6edf3','MA5':'#58a6ff','MA10':'#f0883e','MA20':'#bc8cff'}
        for i, (code, df) in enumerate(dfs.items()):
            ax = axes[i]
            ax.plot(df.index, df['Close'], label='收盤', color=CLR['Close'], lw=1.6, zorder=4)
            ax.plot(df.index, df['MA5'],   label='MA5',  color=CLR['MA5'],   lw=1.2, ls='--', zorder=3)
            ax.plot(df.index, df['MA10'],  label='MA10', color=CLR['MA10'],  lw=1.2, ls='--', zorder=3)
            ax.plot(df.index, df['MA20'],  label='MA20', color=CLR['MA20'],  lw=1.2, ls='--', zorder=3)
            lc = float(df['Close'].iloc[-1])
            ax.scatter(df.index[-1], lc, color='#f0f6fc', s=55, zorder=5)
            ax.annotate(f' {lc:.1f}', (df.index[-1], lc), color='#f0f6fc', fontsize=9, va='center')
            sn, _, grp = get_info(code)
            title_grp = f'  [{grp}]' if grp else ''
            ax.set_title(f"{code} {sn}{title_grp}", color='#58a6ff', fontsize=12, fontweight='bold', pad=8)
            ax.legend(fontsize=8, ncol=4, loc='upper left')
            ax.grid(True, alpha=0.6)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.tick_params(axis='x', rotation=30, labelsize=8)
            ax.tick_params(axis='y', labelsize=8)
            for sp in ax.spines.values(): sp.set_edgecolor('#30363d')
        for j in range(i+1, len(axes)): axes[j].set_visible(False)
        plt.tight_layout(pad=2.5)
        st.pyplot(fig)

elif not do_run:
    st.markdown("""<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
padding:32px;text-align:center;margin-top:16px">
  <div style="font-size:3rem">📊</div>
  <div style="color:#58a6ff;font-size:1.2rem;font-weight:700;margin:12px 0 8px">
    左側搜尋股票後點 ＋ 即可自動開始分析</div>
  <div style="color:#8b949e">或輸入代碼按 Enter・點擊「開始分析」</div>
</div><br><div class="section-title">🔥 熱門股票</div>""", unsafe_allow_html=True)
    pop = [("2330","台積電","半導體業"),("2317","鴻海","電子零組件業"),("2454","聯發科","半導體業"),
           ("2303","聯電","半導體業"),("2382","廣達","電腦及週邊設備業"),("3008","大立光","光電業"),
           ("8086","宏捷科","半導體業"),("2455","全新","半導體業"),("6138","聯亞","半導體業")]
    cols = st.columns(3)
    for i, (code, name, grp) in enumerate(pop):
        with cols[i % 3]:
            st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;
border-radius:8px;padding:12px 16px;margin-bottom:10px">
<span style="color:#58a6ff;font-weight:700">{code}</span>
<span style="color:#e6edf3;font-size:.88rem;margin-left:8px">{name}</span>
<span style="color:#6e7681;font-size:.75rem;display:block;margin-top:3px">{grp}</span>
</div>""", unsafe_allow_html=True)
else:
    st.warning("請先在左側加入股票到查詢清單")
