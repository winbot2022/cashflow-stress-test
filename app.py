import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# --- ページ設定 ---
st.set_page_config(page_title="資金繰り・債権滞留シミュレーター", layout="wide")

# --- フォント設定 ---
FONT_PATH = 'NotoSansJP-Regular.ttf'
if os.path.exists(FONT_PATH):
    fp = fm.FontProperties(fname=FONT_PATH)
    plt.rcParams['font.family'] = fp.get_name()
    font_prop = fp
else:
    font_prop = None

st.title("⚖️ 資金繰り・債権滞留リスクモデル")
st.write("「いつ入るか」の不確実性を可視化し、資金の『底打ち』時間をシミュレーションします。")

# --- サイドバー：設定 ---
st.sidebar.header("📊 経営データの入力")
initial_cash = st.sidebar.number_input("1. 現在の現預金 (万円)", value=300, step=100)

st.sidebar.subheader("📥 顧客ポートフォリオ")
num_clients = st.sidebar.slider("顧客数 (社)", 1, 50, 10)
total_revenue = st.sidebar.number_input("月間総売上 (万円)", value=1900, step=100)

# パレート配分の計算
raw_weights = 1.0 / (np.arange(1, num_clients + 1) ** 1.1)
weights = raw_weights / raw_weights.sum()

st.sidebar.subheader("⚠️ 回収リスクの設定")
hit_prob = st.sidebar.slider("各社の遅延発生確率 (%)", 0, 50, 5)
# ご提案の「翌月回収率」
recovery_rate = st.sidebar.slider("遅延発生後の月間回収率 (%)", 10, 100, 100, step=10)

st.sidebar.subheader("📤 出金（義務）")
fixed_cost = st.sidebar.number_input("月々の固定費 (万円)", value=1000, step=50)
variable_cost_rate = st.sidebar.slider("変動費率 (%)", 0, 100, 40) / 100

trials = st.sidebar.select_slider("シミュレーション回数", options=[100, 1000, 10000], value=1000)
execute_button = st.sidebar.button("🚀 ストレステストを実行")

if execute_button:
    months = 12
    results = []

    for _ in range(trials):
        cash = initial_cash
        # 各社ごとの滞留債権プール
        pending_pools = np.zeros(num_clients)
        cash_flow = [cash]
        
        for m in range(months):
            # 売上発生
            current_sales = np.random.normal(total_revenue, total_revenue * 0.05) * weights
            
            inflow = 0
            for i in range(num_clients):
                # 1. 新規遅延の判定
                if np.random.rand() < (hit_prob / 100):
                    pending_pools[i] += current_sales[i] # プールに積み上がる
                else:
                    inflow += current_sales[i] # 正常入金
                
                # 2. 滞留分の回収（ご提案の率を適用）
                recovered = pending_pools[i] * (recovery_rate / 100)
                inflow += recovered
                pending_pools[i] -= recovered
            
            # 出金（売上連動）
            outflow = fixed_cost + (current_sales.sum() * variable_cost_rate)
            cash += (inflow - outflow)
            cash_flow.append(cash)
            
        results.append(cash_flow)

    results = np.array(results)

    # --- グラフ表示 ---
    col1, col2 = st.columns([2, 1])
    with col1:
        fig, ax = plt.subplots(figsize=(10, 6))
        is_short = np.any(results < 0, axis=1)
        ax.plot(results[~is_short].T, color='gray', alpha=0.02)
        if np.any(is_short):
            ax.plot(results[is_short].T, color='#d62728', alpha=0.03, linewidth=0.8)
        
        ax.plot(np.median(results, axis=0), color='#1f77b4', linewidth=4, label='通常シナリオ')
        ax.axhline(0, color='black', linewidth=2)
        ax.set_title(f"回収率{recovery_rate}% 設定時のキャッシュ推移", fontproperties=font_prop)
        st.pyplot(fig)

    with col2:
        short_rate = (np.sum(is_short) / trials) * 100
        st.metric("1年以内の資金ショート確率", f"{short_rate:.2f} %")
        st.write("**顧客別の売上比率**")
        st.bar_chart(weights[:min(10, num_clients)])
        
        if recovery_rate < 100:
            st.warning(f"回収率が{recovery_rate}%のため、一度の遅延が解消されるまで平均して {100/recovery_rate:.1f} ヶ月かかります。これが赤線の『回復の遅れ』に繋がっています。")
