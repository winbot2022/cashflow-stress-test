import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="資金繰り・サバイバル診断", layout="wide")

st.title("🛡️ 資金繰り・ストレステスト（入出金分離モデル）")
st.write("「平均値」の安心を捨て、31分の1の「死にたくじ」を可視化する。")

# --- サイドバー：経営パラメータの入力 ---
st.sidebar.header("📊 経営データの入力")

initial_cash = st.sidebar.number_input("1. 現在の現預金 (万円)", value=1000, step=100)
st.sidebar.markdown("---")

# 入金セクション
st.sidebar.subheader("📥 入金（不確実）")
base_revenue = st.sidebar.number_input("月々のベース売上 (万円)", value=1200, step=50)
big_hit_revenue = st.sidebar.number_input("大口顧客の入金額 (万円)", value=500, step=50)
hit_prob = st.sidebar.slider("大口の入金遅延が発生する確率 (%)", 0.0, 20.0, 3.2) / 100

# 出金セクション
st.sidebar.subheader("📤 出金（確実な義務）")
fixed_cost = st.sidebar.number_input("月々の固定費：人件費・家賃等 (万円)", value=800, step=50)
variable_cost_rate = st.sidebar.slider("変動費率：仕入・外注費等 (%)", 0, 100, 30) / 100

st.sidebar.markdown("---")
trials = st.sidebar.select_slider("シミュレーション回数", options=[100, 1000, 10000], value=10000)

# --- シミュレーション・ロジック ---
months = 12
results = []

for _ in range(trials):
    cash = initial_cash
    cash_flow = [cash]
    for m in range(months):
        # 1. 入金の計算
        # ベース売上にも少しの変動（標準偏差10%と仮定）を与える
        current_rev = np.random.normal(base_revenue, base_revenue * 0.1)
        
        # 大口顧客の遅延抽選
        if np.random.rand() < hit_prob:
            # 今月は入金ゼロ（来月以降に回る想定だが、単月ストレスとして0で計算）
            pass 
        else:
            current_rev += big_hit_revenue
            
        # 2. 出金の計算
        # 固定費は必ず発生、変動費は「本来の売上予定」に対して発生すると仮定
        current_out = fixed_cost + (base_revenue + big_hit_revenue) * variable_cost_rate
        
        cash += (current_rev - current_out)
        cash_flow.append(cash)
    results.append(cash_flow)

results = np.array(results)

# --- 結果の表示 ---
col1, col2 = st.columns([2, 1])

with col1:
    fig, ax = plt.subplots(figsize=(10, 6))
    # 全試行を薄く描画
    ax.plot(results.T, color='gray', alpha=0.01) 
    # 中央値
    ax.plot(np.median(results, axis=0), color='#1f77b4', linewidth=3, label='通常シナリオ（中央値）')
    # ワースト5%
    ax.plot(np.percentile(results, 5, axis=0), color='#d62728', linestyle='--', linewidth=2, label='最悪のシナリオ（下位5%）')
    
    ax.axhline(0, color='black', linewidth=1.5)
    ax.set_xlabel("月数 (Month)")
    ax.set_ylabel("現預金残高 (万円)")
    ax.legend()
    st.pyplot(fig)

with col2:
    short_count = sum(1 for trial in results if any(cash < 0 for cash in trial))
    short_rate = short_count / trials * 100
    
    st.metric("1年以内の資金ショート確率", f"{short_rate:.2f} %")
    
    if short_rate > 5:
        st.error("⚠️ 危険水域です。固定費の削減か、融資枠の確保を推奨します。")
    elif short_rate > 1:
        st.warning("🟡 注意が必要です。大口依存からの脱却を検討しましょう。")
    else:
        st.success("🟢 比較的安全です。ただし、突発的なリスクへの備えは忘れずに。")

    st.info(f"""
    **診断メモ:**
    - 月間平均支出：約 {fixed_cost + (base_revenue + big_hit_revenue) * variable_cost_rate:.0f} 万円
    - 入金遅延時の単月赤字：約 {big_hit_revenue:.0f} 万円のマイナスインパクト
    """)
