import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

np.random.seed(42)
# --- ページ設定 ---
st.set_page_config(page_title="資金繰り・実務リスクモデル", layout="wide")

# --- フォント設定 ---
FONT_PATH = 'NotoSansJP-Regular.ttf'
if os.path.exists(FONT_PATH):
    fp = fm.FontProperties(fname=FONT_PATH)
    plt.rcParams['font.family'] = fp.get_name()
    font_prop = fp
else:
    font_prop = None

st.title("🛡️ 資金繰り・デッドライン・シミュレーター")
st.write("「入金ラグ」と「個別顧客の売上規模」を同期させた実戦型モデル。")

# --- サイドバー設定 ---
st.sidebar.header("📊 経営データの入力")
initial_cash = st.sidebar.number_input("1. 現在の現預金 (万円)", value=300, step=100)
num_clients = st.sidebar.slider("顧客数 (社)", 1, 50, 10)
total_revenue = st.sidebar.number_input("月間総売上 (万円)", value=1900, step=100)

# パレート配分（比率の計算）
raw_weights = 1.0 / (np.arange(1, num_clients + 1) ** 1.1)
weights = raw_weights / raw_weights.sum()

# 各社の売上高（万円）を計算
client_revenues = total_revenue * weights

st.sidebar.subheader("⚠️ 回収リスクの設定")
hit_prob = st.sidebar.slider("各社の遅延発生確率 (%)", 0, 50, 10)
recovery_rate = st.sidebar.slider("遅延発生後の月間回収率 (%)", 10, 100, 50, step=10)

st.sidebar.subheader("📤 出金（義務）")
fixed_cost = st.sidebar.number_input("月々の固定費 (万円)", value=1000, step=50)
variable_cost_rate = st.sidebar.slider("変動費率 (%)", 0, 100, 40) / 100

st.sidebar.markdown("---")
trials = st.sidebar.select_slider("シミュレーション回数", options=[100, 1000, 10000], value=1000)
execute_button = st.sidebar.button("🚀 ストレステストを実行")

if execute_button:
    months = 12
    results = []
    
    for _ in range(trials):
        cash = initial_cash
        pending_pools = np.zeros(num_clients)
        cash_flow = [cash]
        
        for m in range(months):
            # A. 当月の売上発生（微細なゆらぎを付与）
            current_sales = np.random.normal(total_revenue, total_revenue * 0.05) * weights
            outflow = fixed_cost + (current_sales.sum() * variable_cost_rate)
            
            inflow = 0
            for i in range(num_clients):
                # 滞留分の回収（前月までの滞留分に率をかける）
                recovered = pending_pools[i] * (recovery_rate / 100)
                inflow += recovered
                pending_pools[i] -= recovered
                
                # 新規遅延の判定
                if np.random.rand() < (hit_prob / 100):
                    pending_pools[i] += current_sales[i]
                else:
                    inflow += current_sales[i]
            
            # 月末残高
            cash = cash - outflow + inflow
            cash_flow.append(cash)

        results.append(cash_flow)

    results = np.array(results)

    # --- 描画エリア ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig, ax = plt.subplots(figsize=(10, 6))
        is_short = np.any(results < 0, axis=1)
        
        # 安全ルート
        ax.plot(results[~is_short].T, color='gray', alpha=0.02)
        # ショートルート
        if np.any(is_short):
            ax.plot(results[is_short].T, color='#d62728', alpha=0.04, linewidth=0.8)
        
        ax.plot(np.median(results, axis=0), color='#1f77b4', linewidth=4, label='通常シナリオ')
        ax.axhline(0, color='black', linewidth=2.5)
        ax.set_title("資金繰りシミュレーション（月末残高判定）", fontproperties=font_prop)
        ax.set_xlabel("月数", fontproperties=font_prop)
        ax.set_ylabel("現預金残高 (万円)", fontproperties=font_prop)
        st.pyplot(fig)

    with col2:
        short_rate = (np.sum(is_short) / trials) * 100
        st.metric("1年以内の資金ショート確率", f"{short_rate:.2f} %")
        
        # 修正ポイント：比率ではなく「売上高（万円）」でグラフを表示
        st.write(f"**上位10社の売上高（万円）**")
        # 上位10社（または顧客数分）を抽出して棒グラフ化
        display_data = client_revenues[:min(10, num_clients)]
        st.bar_chart(display_data)
        
        # 補足情報
        st.info(f"""
        - 最大顧客の売上: **{client_revenues[0]:.1f}万円**
        - 月間の総支出目安: **{fixed_cost + total_revenue * variable_cost_rate:.1f}万円**
        """)
        
        if short_rate > 10:
            st.error(f"最大顧客（{client_revenues[0]:.1f}万円）の入金が1ヶ月遅れるだけで、月間の支払いが困難になる構造です。")
