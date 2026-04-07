import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import warnings
warnings.filterwarnings('ignore')

matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'sans-serif']

st.set_page_config(page_title="股票均線分析", page_icon="📈", layout="wide")
st.title("📈 股票均線分析（MA5 / MA10 / MA20）")
st.markdown("輸入台灣股票代碼（例：`2330.TW`、`8086.TWO`），即可查看均線走勢與強弱判斷。")

with st.sidebar:
    st.header("⚙️ 設定")
    tickers_input = st.text_area(
        "股票代碼（每行一個或逗號分隔）",
        value="3105.TW\n8086.TWO\n2455.TW\n6138.TWO",
        height=150,
        help="台股加 .TW（上市）或 .TWO（上櫃）"
    )
    period = st.selectbox("分析區間", ["30d", "60d", "90d", "180d", "1y"], index=1)
    run = st.button("🔍 開始分析", use_container_width=True, type="primary")
    st.markdown("---")
    st.markdown("**使用說明**\n- 上市股票：代碼 + `.TW`\n- 上櫃股票：代碼 + `.TWO`\n- 可同時分析多檔股票")

def get_close_series(df):
    if isinstance(df.columns, pd.MultiIndex):
        close_cols = [c for c in df.columns if c[0] == 'Close']
        if close_cols:
            return df[close_cols[0]]
        df.columns = df.columns.get_level_values(0)
    return df['Close']

def analyze_stock(ticker, period):
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if df.empty or len(df) < 20:
            return None, None, f"{ticker}：資料不足（需至少20個交易日）"
        close = get_close_series(df)
        df2 = pd.DataFrame({'Close': close})
        df2['MA5'] = df2['Close'].rolling(5).mean()
        df2['MA10'] = df2['Close'].rolling(10).mean()
        df2['MA20'] = df2['Close'].rolling(20).mean()
        df2 = df2.dropna()
        latest = df2.iloc[-1]
        c = float(latest['Close'])
        ma5 = float(latest['MA5'])
        ma10 = float(latest['MA10'])
        ma20 = float(latest['MA20'])
        def status(p, m):
            arrow = "▲" if p > m else "▼"
            emoji = "🟢" if p > m else "🔴"
            return f"{emoji} {'站上' if p > m else '跌破'} {arrow} ({(p-m)/m*100:+.2f}%)"
        row = {
            '股票': ticker,
            '最新收盤': round(c, 2),
            'MA5': round(ma5, 2),
            'MA10': round(ma10, 2),
            'MA20': round(ma20, 2),
            'vs MA5': status(c, ma5),
            'vs MA10': status(c, ma10),
            'vs MA20': status(c, ma20),
        }
        return row, df2, None
    except Exception as e:
        return None, None, f"{ticker}：{e}"

def color_cell(val):
    if isinstance(val, str):
        if '站上' in val:
            return 'color: green; font-weight: bold'
        if '跌破' in val:
            return 'color: red; font-weight: bold'
    return ''

if run:
    raw = tickers_input.replace('\n', ',')
    STOCKS = [t.strip() for t in raw.split(',') if t.strip()]
    if not STOCKS:
        st.warning("請輸入至少一個股票代碼")
    else:
        results, dfs, errors = [], {}, []
        progress_bar = st.progress(0, text="分析中...")
        for idx, t in enumerate(STOCKS):
            progress_bar.progress((idx + 1) / len(STOCKS), text=f"正在分析 {t}...")
            row, df, err = analyze_stock(t, period)
            if row:
                results.append(row)
                dfs[t] = df
            if err:
                errors.append(err)
        progress_bar.empty()

        if errors:
            for e in errors:
                st.warning(f"⚠️ {e}")

        if results:
            st.subheader("📊 均線分析結果")
            df_out = pd.DataFrame(results)
            try:
                styled = df_out.style.map(color_cell, subset=['vs MA5', 'vs MA10', 'vs MA20'])
            except AttributeError:
                styled = df_out.style.applymap(color_cell, subset=['vs MA5', 'vs MA10', 'vs MA20'])
            st.dataframe(styled, use_container_width=True, hide_index=True)

            st.subheader("📋 強弱總結")
            cols_summary = st.columns(len(results))
            for i, r in enumerate(results):
                a5 = '站上' in r['vs MA5']
                a10 = '站上' in r['vs MA10']
                a20 = '站上' in r['vs MA20']
                cnt = sum([a5, a10, a20])
                if cnt == 3:
                    tag = "✅ 三線全站上（強勢）"
                    color = "🟢"
                elif cnt == 0:
                    tag = "❌ 三線全跌破（弱勢）"
                    color = "🔴"
                else:
                    tag = "⚡ " + str(cnt) + "/3 線站上（整理中）"
                    color = "🟡"
                with cols_summary[i]:
                    st.metric(
                        label=color + " " + r['股票'],
                        value=str(round(r['最新收盤'], 2)),
                        delta=tag,
                        delta_color="off"
                    )

            st.subheader("📉 均線走勢圖（近 " + period + "）")
            n = len(dfs)
            cols_n = min(2, n)
            rows_n = (n + cols_n - 1) // cols_n
            fig, axes = plt.subplots(rows_n, cols_n, figsize=(16, 5 * rows_n))
            if n == 1:
                axes = [axes]
            elif rows_n == 1:
                axes = list(axes)
            else:
                axes = [ax for row_axes in axes for ax in row_axes]

            for i, (t, df) in enumerate(dfs.items()):
                ax = axes[i]
                ax.plot(df.index, df['Close'], label='Close', color='#333333', lw=1.8)
                ax.plot(df.index, df['MA5'], label='MA5', color='#2196F3', lw=1.3, ls='--')
                ax.plot(df.index, df['MA10'], label='MA10', color='#FF9800', lw=1.3, ls='--')
                ax.plot(df.index, df['MA20'], label='MA20', color='#E91E63', lw=1.3, ls='--')
                lc = float(df['Close'].iloc[-1])
                ax.scatter(df.index[-1], lc, color='black', zorder=5, s=60)
                ax.annotate(str(round(lc, 2)), (df.index[-1], lc),
                            xytext=(6, 4), textcoords='offset points', fontsize=9)
                ax.set_title(t, fontsize=13, fontweight='bold')
                ax.legend(fontsize=9)
                ax.grid(True, alpha=0.3)
                ax.tick_params(axis='x', rotation=30)

            for j in range(i + 1, len(axes)):
                axes[j].set_visible(False)

            plt.tight_layout()
            st.pyplot(fig)
else:
    st.info("👈 請在左側輸入股票代碼，然後按「開始分析」")
    st.markdown("### 範例股票代碼")
    examples = {
        "台積電": "2330.TW", "鴻海": "2317.TW", "聯發科": "2454.TW",
        "穩懋": "3105.TW", "宏捷科": "8086.TWO", "全新": "2455.TW"
    }
    cols = st.columns(3)
    for idx, (name, code) in enumerate(examples.items()):
        cols[idx % 3].code(name + ": " + code)
