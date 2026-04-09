import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings, json, base64, requests
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
.folder-card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:10px 14px;margin:4px 0;cursor:pointer;transition:border-color .15s;}
.folder-card:hover,.folder-card.active{border-color:#1f6feb;background:#1c2128;}
.folder-title{color:#58a6ff;font-weight:700;font-size:.95rem;}
.folder-count{color:#8b949e;font-size:.75rem;margin-left:6px;}
.stock-card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px 20px;margin-bottom:14px;}
.ticker{color:#58a6ff;font-size:1.1rem;font-weight:700;}
.sname{color:#e6edf3;font-size:.9rem;margin-left:6px;}
.group-badge{background:#1c2a3a;color:#a5d6ff;font-size:.73rem;border:1px solid #1f6feb55;border-radius:4px;padding:2px 8px;margin-left:8px;vertical-align:middle;}
.price{color:#e6edf3;font-size:2rem;font-weight:700;margin:4px 0;}
.tag-up{background:#1a3a2a;color:#3fb950;border:1px solid #238636;border-radius:6px;padding:3px 10px;font-size:.82rem;font-weight:600;display:inline-block;}
.tag-down{background:#3a1a1a;color:#f85149;border:1px solid #da3633;border-radius:6px;padding:3px 10px;font-size:.82rem;font-weight:600;display:inline-block;}
.tag-mid{background:#2a2a1a;color:#d29922;border:1px solid #9e6a03;border-radius:6px;padding:3px 10px;font-size:.82rem;font-weight:600;display:inline-block;}
.ma-row{display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;}
.ma-chip{border-radius:6px;padding:4px 12px;font-size:.8rem;font-weight:600;}
.ma-up{background:#0d2818;color:#3fb950;border:1px solid #238636;}
.ma-down{background:#2d1117;color:#f85149;border:1px solid #da3633;}
.inst-box{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 16px;margin-top:10px;}
.inst-title{color:#8b949e;font-size:.78rem;margin-bottom:6px;font-weight:600;}
.inst-row{display:flex;gap:12px;flex-wrap:wrap;}
.inst-chip{border-radius:5px;padding:3px 10px;font-size:.78rem;font-weight:600;}
.inst-buy{background:#0d2818;color:#3fb950;border:1px solid #238636;}
.inst-sell{background:#2d1117;color:#f85149;border:1px solid #da3633;}
.inst-zero{background:#1c2128;color:#8b949e;border:1px solid #30363d;}
.data-table{width:100%;border-collapse:collapse;font-size:.85rem;margin-top:8px;}
.data-table th{background:#1c2128;color:#8b949e;padding:8px 12px;text-align:left;border-bottom:1px solid #30363d;font-weight:600;}
.data-table td{padding:8px 12px;border-bottom:1px solid #21262d;color:#e6edf3;}
.data-table tr:hover td{background:#1c2128;}
.up{color:#3fb950;font-weight:600;}.dn{color:#f85149;font-weight:600;}
.section-title{color:#58a6ff;font-size:1.05rem;font-weight:700;border-left:3px solid #1f6feb;padding-left:10px;margin:22px 0 14px 0;}
.hit-item{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:9px 14px;margin:3px 0;display:flex;align-items:center;gap:8px;}
.hit-code{color:#58a6ff;font-weight:700;min-width:52px;font-size:.9rem;}
.hit-name{color:#e6edf3;font-size:.88rem;flex:1;}
.hit-group{color:#a5d6ff;font-size:.72rem;background:#1c2a3a;padding:2px 6px;border-radius:4px;white-space:nowrap;}
.hit-mkt{color:#8b949e;font-size:.72rem;background:#21262d;padding:2px 6px;border-radius:4px;}
.stTextInput input{background:#161b22 !important;color:#e6edf3 !important;border:1px solid #30363d !important;border-radius:8px !important;font-size:1rem !important;}
.stTextInput input:focus{border-color:#1f6feb !important;}
.stSelectbox>div>div{background:#161b22 !important;border:1px solid #30363d !important;color:#e6edf3 !important;}
.stButton button{background:linear-gradient(135deg,#1f6feb,#388bfd) !important;color:#fff !important;border:none !important;border-radius:8px !important;font-size:.9rem !important;font-weight:700 !important;}
.stButton button:hover{opacity:.88 !important;}
#MainMenu,footer{visibility:hidden;}
header[data-testid="stHeader"]{background:transparent;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  GitHub 永久儲存
# ══════════════════════════════════════════════
GH_TOKEN = st.secrets.get("GITHUB_TOKEN","")
GH_REPO  = st.secrets.get("GITHUB_REPO","David1491313/stock-ma-analysis")
WL_FILE  = st.secrets.get("WATCHLIST_FILE","watchlist.json")
GH_API   = f"https://api.github.com/repos/{GH_REPO}/contents/{WL_FILE}"
GH_HDR   = {"Authorization":f"token {GH_TOKEN}","Accept":"application/vnd.github.v3+json"}

DEFAULT_FOLDERS = {
    "⭐ 我的最愛": ["2330","2454","2317"],
    "🔬 半導體":   ["2330","2303","2454","8086","2455"],
    "🚢 航運":     ["2603","2609","2610"],
    "🏦 金融":     ["2881","2882","2884","2886","2891"],
}

@st.cache_data(ttl=60, show_spinner=False)
def load_watchlist_from_github():
    try:
        r = requests.get(GH_API, headers=GH_HDR, timeout=5)
        if r.status_code == 200:
            content = base64.b64decode(r.json()["content"]).decode("utf-8")
            return json.loads(content)
    except Exception:
        pass
    return DEFAULT_FOLDERS.copy()

def save_watchlist_to_github(data):
    try:
        content_b64 = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode()).decode()
        # 先取 sha
        r = requests.get(GH_API, headers=GH_HDR, timeout=5)
        sha = r.json().get("sha","") if r.status_code==200 else ""
        payload = {"message":"update watchlist","content":content_b64}
        if sha: payload["sha"] = sha
        requests.put(GH_API, headers=GH_HDR, json=payload, timeout=10)
        load_watchlist_from_github.clear()
    except Exception as e:
        st.warning(f"儲存失敗：{e}")

# ══════════════════════════════════════════════
#  台股資料庫
# ══════════════════════════════════════════════
@st.cache_data(ttl=3600*12, show_spinner=False)
def load_stock_db():
    db = {}
    try:
        import twstock
        for code, stock in twstock.codes.items():
            if not code.isdigit(): continue
            name   = getattr(stock,'name','') or ''
            market = getattr(stock,'market','') or ''
            group  = getattr(stock,'group','') or ''
            sfx = 'TW' if ('上市' in market or market=='TWSE') else                   'TWO' if ('上櫃' in market or market in ('OTC','TPEx')) else 'TW'
            db[code] = (name, sfx, group)
    except: pass
    if not db:
        db={"2330":("台積電","TW","半導體業"),"2317":("鴻海","TW","電子零組件業"),
            "2454":("聯發科","TW","半導體業"),"2303":("聯電","TW","半導體業"),
            "2382":("廣達","TW","電腦及週邊設備業"),"3008":("大立光","TW","光電業"),
            "2412":("中華電","TW","通信網路業"),"2881":("富邦金","TW","金融保險業"),
            "2882":("國泰金","TW","金融保險業"),"2603":("長榮","TW","航運業"),
            "2609":("陽明","TW","航運業"),"2886":("兆豐金","TW","金融保險業"),
            "8086":("宏捷科","TWO","半導體業"),"2455":("全新","TWO","半導體業"),
            "6138":("聯亞","TWO","半導體業")}
    return db

STOCK_DB = load_stock_db()

def get_info(code):
    v = STOCK_DB.get(code,("","TW",""))
    if isinstance(v,tuple) and len(v)==3: return v
    return str(v),"TW",""
def get_name(code):   return get_info(code)[0]
def get_suffix(code): return get_info(code)[1]

def search_stocks(query):
    q=query.strip()
    if not q: return []
    out=[]
    for code,val in STOCK_DB.items():
        name=val[0] if isinstance(val,tuple) else val
        sfx=val[1] if isinstance(val,tuple) and len(val)>1 else "TW"
        group=val[2] if isinstance(val,tuple) and len(val)>2 else ""
        if code.startswith(q) or q in name:
            out.append((code,name,sfx,group))
    out.sort(key=lambda x:(x[0]!=q,x[1]!=q,len(x[0])>4,not x[0].startswith(q),x[0]))
    return out[:20]

def resolve(raw):
    code=raw.strip().upper()
    if '.' in code: return code
    if code.isdigit(): return code+'.'+(get_suffix(code) or "TW")
    return code

# ══════════════════════════════════════════════
#  三大法人資料（TWSE API）
# ══════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def get_institutional(code):
    try:
        url = f"https://www.twse.com.tw/rwd/zh/fund/T86?stockNo={code}&response=json"
        r = requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
        data = r.json()
        if data.get("stat") != "OK" or not data.get("data"):
            return None
        row = data["data"][0]
        # 欄位：外資買、外資賣、外資淨、投信買、投信賣、投信淨、自營買、自營賣、自營淨、三大合計
        def to_int(s):
            try: return int(str(s).replace(",","").replace("+",""))
            except: return 0
        foreign_net = to_int(row[4])
        trust_net   = to_int(row[8])
        dealer_net  = to_int(row[11]) if len(row)>11 else 0
        total_net   = to_int(row[13]) if len(row)>13 else foreign_net+trust_net+dealer_net
        return {"外資":foreign_net,"投信":trust_net,"自營":dealer_net,"合計":total_net}
    except:
        return None

# ══════════════════════════════════════════════
#  Session state
# ══════════════════════════════════════════════
if 'folders' not in st.session_state:
    st.session_state.folders = load_watchlist_from_github()
if 'active_folder' not in st.session_state:
    st.session_state.active_folder = list(st.session_state.folders.keys())[0] if st.session_state.folders else ""
if 'do_analyze' not in st.session_state:
    st.session_state.do_analyze = False
if 'search_hits' not in st.session_state:
    st.session_state.search_hits = []
if 'search_q' not in st.session_state:
    st.session_state.search_q = ''
if 'last_input' not in st.session_state:
    st.session_state.last_input = ''

def save_folders():
    save_watchlist_to_github(st.session_state.folders)

# ══════════════════════════════════════════════
#  Header
# ══════════════════════════════════════════════
st.markdown("""<div class="main-header">
  <h1>📈 台股均線分析站</h1>
  <p>資料夾管理自選股・均線分析・三大法人動向・資料永久保存</p>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  分析函式
# ══════════════════════════════════════════════
def get_close(df):
    if isinstance(df.columns, pd.MultiIndex):
        cols=[c for c in df.columns if c[0]=='Close']
        if cols: return df[cols[0]]
        df.columns=df.columns.get_level_values(0)
    return df['Close']

def analyze(code_raw, period):
    ticker=resolve(code_raw)
    try:
        df=yf.download(ticker,period=period,progress=False,auto_adjust=True)
        if df.empty or len(df)<20:
            return None,None,f"{code_raw}：資料不足"
        close=get_close(df)
        d=pd.DataFrame({'Close':close})
        d['MA5']=d['Close'].rolling(5).mean()
        d['MA10']=d['Close'].rolling(10).mean()
        d['MA20']=d['Close'].rolling(20).mean()
        d=d.dropna()
        lat=d.iloc[-1]
        c,m5,m10,m20=float(lat['Close']),float(lat['MA5']),float(lat['MA10']),float(lat['MA20'])
        pct=lambda p,m:(p-m)/m*100
        arr=lambda p,m:"▲" if p>m else "▼"
        code_c=code_raw.split('.')[0].upper()
        sname,_,grp=get_info(code_c) if code_c.isdigit() else ("","TW","")
        row={'_code':code_c,'_ticker':ticker,'_sname':sname,'_group':grp,
             '_close':c,'_m5':m5,'_m10':m10,'_m20':m20,
             '代碼':code_c,'名稱':sname,'族群':grp,'最新收盤':round(c,2),
             'MA5':round(m5,2),'MA10':round(m10,2),'MA20':round(m20,2),
             'vs MA5': f"{'🟢 站上' if c>m5  else '🔴 跌破'} {arr(c,m5)} ({pct(c,m5):+.2f}%)",
             'vs MA10':f"{'🟢 站上' if c>m10 else '🔴 跌破'} {arr(c,m10)} ({pct(c,m10):+.2f}%)",
             'vs MA20':f"{'🟢 站上' if c>m20 else '🔴 跌破'} {arr(c,m20)} ({pct(c,m20):+.2f}%)",}
        return row,d,None
    except Exception as e:
        return None,None,f"{code_raw}：{e}"

# ══════════════════════════════════════════════
#  Sidebar
# ══════════════════════════════════════════════
with st.sidebar:
    # 搜尋框
    st.markdown('<div class="section-title">🔍 搜尋股票</div>', unsafe_allow_html=True)
    curr_input = st.text_input("",placeholder="代碼或名稱，如：2330 / 台積電",
                               label_visibility="collapsed",key="unified_input")
    if curr_input.strip() and curr_input.strip()!=st.session_state.last_input:
        q=curr_input.strip()
        st.session_state.last_input=q
        hits=search_stocks(q)
        if q.isdigit() and len(q)<=6:
            af=st.session_state.active_folder
            if af and q not in st.session_state.folders.get(af,[]):
                st.session_state.folders.setdefault(af,[]).append(q)
                save_folders()
            st.session_state.search_hits=[]
            st.session_state.search_q=''
            st.session_state.do_analyze=True
        elif hits and (len(hits)==1 or hits[0][0]==q or hits[0][1]==q):
            c=hits[0][0]
            af=st.session_state.active_folder
            if af and c not in st.session_state.folders.get(af,[]):
                st.session_state.folders.setdefault(af,[]).append(c)
                save_folders()
            st.session_state.search_hits=[]
            st.session_state.search_q=''
            st.session_state.do_analyze=True
        elif hits:
            st.session_state.search_hits=hits
            st.session_state.search_q=q
        else:
            st.session_state.search_hits=[]
            st.session_state.search_q=q
    if not curr_input.strip():
        st.session_state.last_input=''

    if st.session_state.search_hits:
        q_show=st.session_state.search_q
        st.markdown(f'<div style="color:#8b949e;font-size:.76rem;margin:4px 0">「{q_show}」找到 {len(st.session_state.search_hits)} 筆：</div>',unsafe_allow_html=True)
        for code,name,sfx,group in st.session_state.search_hits:
            c1,c2=st.columns([5,1])
            grp_html=f'<span class="hit-group">🏭 {group}</span>' if group else ''
            mkt="上市" if sfx=="TW" else "上櫃"
            with c1:
                st.markdown(f'<div class="hit-item"><span class="hit-code">{code}</span><span class="hit-name">{name}</span>{grp_html}<span class="hit-mkt">{mkt}</span></div>',unsafe_allow_html=True)
            with c2:
                if st.button("＋",key=f"a_{code}"):
                    af=st.session_state.active_folder
                    if af and code not in st.session_state.folders.get(af,[]):
                        st.session_state.folders.setdefault(af,[]).append(code)
                        save_folders()
                    st.session_state.search_hits=[]
                    st.session_state.search_q=''
                    st.session_state.last_input=''
                    st.session_state.do_analyze=True
    elif st.session_state.search_q and not st.session_state.search_hits:
        st.markdown(f'<div style="color:#f85149;font-size:.82rem;padding:4px">「{st.session_state.search_q}」查無結果</div>',unsafe_allow_html=True)

    st.markdown("---")

    # 資料夾管理
    st.markdown('<div class="section-title">📁 我的資料夾</div>', unsafe_allow_html=True)

    folders=st.session_state.folders
    active=st.session_state.active_folder

    for fname in list(folders.keys()):
        stocks=folders[fname]
        is_active=(fname==active)
        c1,c2=st.columns([5,1])
        with c1:
            card_class="folder-card active" if is_active else "folder-card"
            if st.button(f"{fname}  ({len(stocks)}支)",key=f"f_{fname}",
                         use_container_width=True):
                st.session_state.active_folder=fname
                st.session_state.do_analyze=True
        with c2:
            if st.button("🗑",key=f"fd_{fname}"):
                del st.session_state.folders[fname]
                if st.session_state.active_folder==fname:
                    st.session_state.active_folder=list(st.session_state.folders.keys())[0] if st.session_state.folders else ""
                save_folders()
                st.rerun()

    # 新增資料夾
    with st.expander("＋ 新增資料夾"):
        new_name=st.text_input("資料夾名稱",placeholder="如：AI概念股",key="new_folder_name")
        if st.button("建立",key="create_folder"):
            if new_name.strip() and new_name.strip() not in folders:
                st.session_state.folders[new_name.strip()]=[]
                st.session_state.active_folder=new_name.strip()
                save_folders()
                st.rerun()

    # 目前資料夾的股票清單
    af=st.session_state.active_folder
    if af and af in st.session_state.folders:
        st.markdown(f'<div style="color:#8b949e;font-size:.78rem;margin:6px 0 4px">📂 {af}</div>',unsafe_allow_html=True)
        stocks=st.session_state.folders[af]
        rm=None
        for code in stocks:
            name,_,grp=get_info(code)
            c1,c2=st.columns([5,1])
            with c1:
                grp_txt=f' · <span style="color:#a5d6ff;font-size:.7rem">{grp}</span>' if grp else ''
                st.markdown(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:5px;padding:5px 10px;margin:2px 0"><span style="color:#58a6ff;font-weight:700">{code}</span> <span style="color:#e6edf3;font-size:.82rem">{name}</span>{grp_txt}</div>',unsafe_allow_html=True)
            with c2:
                if st.button("✕",key=f"r_{af}_{code}"):
                    rm=code
        if rm:
            st.session_state.folders[af].remove(rm)
            save_folders()
            st.rerun()

    st.markdown("---")
    period_map={"30d":"近30天","60d":"近60天","90d":"近90天","180d":"近半年","1y":"近1年"}
    period=st.selectbox("查詢區間",list(period_map.keys()),index=1,format_func=lambda x:period_map[x])
    show_inst=st.checkbox("顯示三大法人",value=True)
    if st.button("🔍 開始分析",use_container_width=True):
        st.session_state.do_analyze=True

# ══════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════
do_run=st.session_state.do_analyze
st.session_state.do_analyze=False

af=st.session_state.active_folder
wl=st.session_state.folders.get(af,[]) if af else []

if do_run and wl:
    results,dfs,errors=[],{},[],
    bar=st.progress(0,text="資料下載中…")
    for i,code in enumerate(wl):
        n=get_name(code)
        bar.progress((i+1)/len(wl),text=f"正在分析 {code} {n}…")
        row,df,err=analyze(code,period)
        if row: results.append(row); dfs[code]=df
        if err: errors.append(err)
    bar.empty()

    if errors:
        for e in errors:
            st.markdown(f'<div style="background:#3a1a1a;border:1px solid #da3633;border-radius:8px;padding:10px 14px;color:#f85149;margin:4px 0">⚠️ {e}</div>',unsafe_allow_html=True)

    if results:
        st.markdown(f'<div class="section-title">📊 {af} — 均線強弱總覽</div>',unsafe_allow_html=True)
        cols=st.columns(min(len(results),4))

        def chip(lb,p,m):
            cl="ma-up" if p>m else "ma-down"
            return f'<span class="ma-chip {cl}">{lb} {"▲" if p>m else "▼"} ({(p-m)/m*100:+.1f}%)</span>'

        def inst_html(code):
            if not show_inst: return ''
            d=get_institutional(code)
            if not d: return '<div style="color:#6e7681;font-size:.75rem;margin-top:8px">三大法人：無資料</div>'
            def cls(v): return "inst-buy" if v>0 else "inst-sell" if v<0 else "inst-zero"
            def fmt(v): return f"+{v:,}" if v>0 else f"{v:,}"
            chips=''.join([f'<span class="inst-chip {cls(d[k])}">{k} {fmt(d[k])}</span>' for k in ["外資","投信","自營","合計"]])
            return f'<div class="inst-box"><div class="inst-title">🏛 三大法人買賣超（張）</div><div class="inst-row">{chips}</div></div>'

        for i,r in enumerate(results):
            a5=r['_close']>r['_m5']; a10=r['_close']>r['_m10']; a20=r['_close']>r['_m20']
            cnt=sum([a5,a10,a20])
            if cnt==3:   tag='<span class="tag-up">✅ 三線全站上（強勢）</span>'; bc='border-color:#238636'
            elif cnt==0: tag='<span class="tag-down">❌ 三線全跌破（弱勢）</span>'; bc='border-color:#da3633'
            else:        tag=f'<span class="tag-mid">⚡ {cnt}/3 線站上（整理中）</span>'; bc='border-color:#9e6a03'
            grp_badge=f'<span class="group-badge">🏭 {r["_group"]}</span>' if r["_group"] else ''
            with cols[i%len(cols)]:
                st.markdown(f"""<div class="stock-card" style="{bc}">
  <div><span class="ticker">{r['代碼']}</span><span class="sname">{r['名稱']}</span>{grp_badge}</div>
  <div class="price">$ {r['最新收盤']}</div>{tag}
  <div class="ma-row">{chip('MA5',r['_close'],r['_m5'])}{chip('MA10',r['_close'],r['_m10'])}{chip('MA20',r['_close'],r['_m20'])}</div>
  {inst_html(r['_code'])}
</div>""",unsafe_allow_html=True)

        st.markdown('<div class="section-title">📋 詳細數據</div>',unsafe_allow_html=True)
        rh=""
        for r in results:
            td=lambda v:f'<td class="{"up" if "站上" in v else "dn"}">{v}</td>'
            rh+=(f"<tr><td><b style='color:#58a6ff'>{r['代碼']}</b></td><td>{r['名稱']}</td>"
                 f"<td><span style='color:#a5d6ff;font-size:.8rem'>{r['族群']}</span></td>"
                 f"<td><b>{r['最新收盤']}</b></td><td>{r['MA5']}</td><td>{r['MA10']}</td><td>{r['MA20']}</td>"
                 f"{td(r['vs MA5'])}{td(r['vs MA10'])}{td(r['vs MA20'])}</tr>")
        st.markdown(f"""<table class="data-table"><thead><tr>
<th>代碼</th><th>名稱</th><th>族群</th><th>收盤</th><th>MA5</th><th>MA10</th><th>MA20</th>
<th>vs MA5</th><th>vs MA10</th><th>vs MA20</th></tr></thead><tbody>{rh}</tbody></table>""",unsafe_allow_html=True)

        st.markdown('<div class="section-title">📉 均線走勢圖</div>',unsafe_allow_html=True)
        matplotlib.rcParams.update({'figure.facecolor':'#0d1117','axes.facecolor':'#161b22',
            'axes.edgecolor':'#30363d','axes.labelcolor':'#8b949e','xtick.color':'#8b949e',
            'ytick.color':'#8b949e','grid.color':'#21262d','grid.linewidth':0.8,
            'text.color':'#e6edf3','legend.facecolor':'#1c2128','legend.edgecolor':'#30363d',
            'font.family':'DejaVu Sans'})
        n=len(dfs); cn=min(2,n); rn=(n+cn-1)//cn
        fig,axes=plt.subplots(rn,cn,figsize=(16,5*rn))
        if n==1: axes=[axes]
        elif rn==1: axes=list(axes)
        else: axes=[ax for ra in axes for ax in ra]
        CLR={'Close':'#e6edf3','MA5':'#58a6ff','MA10':'#f0883e','MA20':'#bc8cff'}
        for i,(code,df) in enumerate(dfs.items()):
            ax=axes[i]
            ax.plot(df.index,df['Close'],label='收盤',color=CLR['Close'],lw=1.6,zorder=4)
            ax.plot(df.index,df['MA5'],label='MA5',color=CLR['MA5'],lw=1.2,ls='--',zorder=3)
            ax.plot(df.index,df['MA10'],label='MA10',color=CLR['MA10'],lw=1.2,ls='--',zorder=3)
            ax.plot(df.index,df['MA20'],label='MA20',color=CLR['MA20'],lw=1.2,ls='--',zorder=3)
            lc=float(df['Close'].iloc[-1])
            ax.scatter(df.index[-1],lc,color='#f0f6fc',s=55,zorder=5)
            ax.annotate(f' {lc:.1f}',(df.index[-1],lc),color='#f0f6fc',fontsize=9,va='center')
            sn,_,grp=get_info(code)
            ax.set_title(f"{code} {sn}{'  ['+grp+']' if grp else ''}",color='#58a6ff',fontsize=12,fontweight='bold',pad=8)
            ax.legend(fontsize=8,ncol=4,loc='upper left')
            ax.grid(True,alpha=0.6)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.tick_params(axis='x',rotation=30,labelsize=8)
            ax.tick_params(axis='y',labelsize=8)
            for sp in ax.spines.values(): sp.set_edgecolor('#30363d')
        for j in range(i+1,len(axes)): axes[j].set_visible(False)
        plt.tight_layout(pad=2.5)
        st.pyplot(fig)

else:
    folders=st.session_state.folders
    af=st.session_state.active_folder
    if af and folders.get(af):
        st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
padding:28px;text-align:center;margin-top:8px">
  <div style="font-size:2.5rem">📁</div>
  <div style="color:#58a6ff;font-size:1.1rem;font-weight:700;margin:10px 0 6px">{af}</div>
  <div style="color:#8b949e">共 {len(folders[af])} 支股票・點左側「開始分析」或直接輸入代碼</div>
</div>""",unsafe_allow_html=True)
    else:
        st.markdown("""<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
padding:28px;text-align:center;margin-top:8px">
  <div style="font-size:2.5rem">📊</div>
  <div style="color:#58a6ff;font-size:1.1rem;font-weight:700;margin:10px 0 6px">選擇或建立資料夾，然後加入股票</div>
  <div style="color:#8b949e">左側輸入代碼/名稱加入目前資料夾，按「開始分析」查看結果</div>
</div>""",unsafe_allow_html=True)
