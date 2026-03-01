import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# --- ページ設定 ---
st.set_page_config(page_title="資金繰り・10社分散リスクモデル", layout="wide")

# --- フォント設定 ---
FONT_PATH = 'NotoSansJP-Regular.ttf'
if os.path.exists(FONT_PATH):
    fp = fm.FontProperties(fname=FONT_PATH)
    plt.rcParams['font.family'] = fp.get_name()
    font_prop = fp
else:
    font_prop = None

st.title("⚖️ 資金繰り・10社分散リスクモデル")
st.write("「全社一律」ではなく、「10社それぞれの支払い遅延」がランダムに重なる恐怖を可視化します。")

# --- サイドバー：設定 ---
st.sidebar.header("📊 経営データの入力")
initial_cash = st.sidebar.number_input("1. 現在の現預金 (万円)", value=300, step=100)

st.sidebar.subheader("📥 入金構造（10社合計）")
total_revenue = st.sidebar.number_input("月間総売上 (万円)", value=1900, step=100)

st.sidebar.subheader("⚠️ 個別顧客の遅延リスク")
hit_prob_per_client = st.sidebar.slider("各社の遅延発生確率 (%)", 0, 50, 10)

st.sidebar.subheader("📤 出金（確実な義務）")
fixed_cost = st.sidebar.number_input("月々の固定費 (万円)", value=1000, step=50)
variable_cost_rate = st.sidebar.slider("変動費率 (%)", 0, 100, 40) / 100

trials = st.sidebar.select_slider("シミュレーション回数", options=[100, 1000, 10000], value=1000)
execute_button = st.sidebar.button("🚀 ストレステストを実行")

if execute_button:
    months = 12
    # 顧客10社の売上構成比（上位に偏らせる：A社30%, B社20%, C社15%, ... 残り数%ずつ）
    weights = np.array([30, 20, 15, 10, 8, 5, 4, 4, 2, 2])
    weights = weights / weights.sum()
    
    results = []

    for _ in range(trials):
        cash = initial_cash
        pending_balances = np.zeros(10) # 10社それぞれの未回収残高
        cash_flow = [cash]
        
        for m in range(months):
            # 1. 各社の売上発生（総売上を分配 + 5%の微細な変動）
            monthly_total_sales = np.random.normal(total_revenue, total_revenue * 0.05)
            client_sales = monthly_total_sales * weights
            
            # 2. 各社ごとに遅延を判定
            inflow = 0
            for i in range(10):
                is_delayed = np.random.rand() < (hit_prob_per_client / 100)
                
                if is_delayed:
                    # 遅延：前月の残高は回収できるが、今月分は丸々未回収へ
                    inflow += pending_balances[i]
                    pending_balances[i] = client_sales[i]
                else:
                    # 平時：今月分 + 前月の残高を全額回収
                    inflow += client_sales[i] + pending_balances[i]
                    pending_balances[i] = 0
            
            # 3. 出金（売上に応じた変動費 + 固定費）※出金は遅延しない
            outflow = fixed_cost + (monthly_total_sales * variable_cost_rate)
            
            # 4. 残高更新
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
            ax.plot(results[is_short].T, color='#d62728', alpha=0.05, linewidth=0.5)
        ax.plot(np.median(results, axis=0), color='#1f77b4', linewidth=4, label='通常シナリオ')
        ax.axhline(0, color='black', linewidth=2)
        ax.set_title("10社分散リスク・シミュレーション", fontproperties=font_prop)
        st.pyplot(fig)

    with col2:
        short_rate = (np.sum(is_short) / trials) * 100
        st.metric("1年以内の資金ショート確率", f"{short_rate:.2f} %")
        st.info(f"""
        **このモデルのリアリティ:**
        - **依存度の可視化**: A社(30%)が遅れた月と、J社(2%)が遅れた月では、グラフの凹みが全く違います。
        - **不運の重なり**: 「たまたま上位3社が同時に遅れた」という最悪のケースが赤線として描画されます。
        """)
