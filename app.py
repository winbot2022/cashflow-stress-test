import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# --- ページ設定 ---
st.set_page_config(page_title="資金繰り・厳格リスクモデル", layout="wide")

# --- フォント設定 ---
FONT_PATH = 'NotoSansJP-Regular.ttf'
if os.path.exists(FONT_PATH):
    fp = fm.FontProperties(fname=FONT_PATH)
    plt.rcParams['font.family'] = fp.get_name()
    font_prop = fp
else:
    font_prop = None

st.title("🛡️ 資金繰り・厳格リスクシミュレーター")
st.write("「支払い後の瞬間」を判定。最大顧客の初月遅延を逃さない厳格モデル。")

# --- サイドバー設定 ---
st.sidebar.header("📊 経営データの入力")
initial_cash = st.sidebar.number_input("1. 現在の現預金 (万円)", value=300, step=100)
num_clients = st.sidebar.slider("顧客数 (社)", 1, 50, 10)
total_revenue = st.sidebar.number_input("月間総売上 (万円)", value=1900, step=100)

# パレート配分
raw_weights = 1.0 / (np.arange(1, num_clients + 1) ** 1.1)
weights = raw_weights / raw_weights.sum()

st.sidebar.subheader("⚠️ 回収リスクの設定")
hit_prob = st.sidebar.slider("各社の遅延発生確率 (%)", 0, 50, 10)
recovery_rate = st.sidebar.slider("遅延発生後の月間回収率 (%)", 10, 100, 50, step=10)

st.sidebar.subheader("📤 出金（義務）")
fixed_cost = st.sidebar.number_input("月々の固定費 (万円)", value=1000, step=50)
variable_cost_rate = st.sidebar.slider("変動費率 (%)", 0, 100, 40) / 100

trials = st.sidebar.select_slider("シミュレーション回数", options=[100, 1000, 10000], value=1000)
execute_button = st.sidebar.button("🚀 厳格テストを実行")

if execute_button:
    months = 12
    results = []
    
    for _ in range(trials):
        cash = initial_cash
        pending_pools = np.zeros(num_clients)
        cash_flow = [cash]
        
        for m in range(months):
            # A. 当月の「発生主義」売上
            current_sales = np.random.normal(total_revenue, total_revenue * 0.05) * weights
            
            # B. 出金の計算（義務的支払）
            outflow = fixed_cost + (current_sales.sum() * variable_cost_rate)
            
            # C. 先に「支払い」を行う（ここでショート判定）
            cash -= outflow
            # 支払い直後の残高を記録（入金前に判定するため）
            interim_cash = cash 
            
            # D. 回収の計算
            inflow = 0
            for i in range(num_clients):
                if np.random.rand() < (hit_prob / 100):
                    pending_pools[i] += current_sales[i]
                else:
                    inflow += current_sales[i]
                
                # 滞留分の回収
                recovered = pending_pools[i] * (recovery_rate / 100)
                inflow += recovered
                pending_pools[i] -= recovered
            
            # E. 入金を加算
            cash += inflow
            # グラフ用には入金後の残高を記録（ただし判定には interim_cash を使用）
            cash_flow.append(cash if interim_cash >= 0 else interim_cash)

        results.append(cash_flow)

    results = np.array(results)

    # --- 描画 ---
    col1, col2 = st.columns([2, 1])
    with col1:
        fig, ax = plt.subplots(figsize=(10, 6))
        # 厳格判定：一度でも「支払い後」が0未満になったら赤
        is_short = np.any(results < 0, axis=1)
        
        ax.plot(results[~is_short].T, color='gray', alpha=0.02)
        if np.any(is_short):
            ax.plot(results[is_short].T, color='#d62728', alpha=0.03, linewidth=0.8)
        
        ax.plot(np.median(results, axis=0), color='#1f77b4', linewidth=4, label='通常シナリオ')
        ax.axhline(0, color='black', linewidth=2.5)
        ax.set_title("厳格キャッシュフロー判定（支払い先行モデル）", fontproperties=font_prop)
        st.pyplot(fig)

    with col2:
        short_rate = (np.sum(is_short) / trials) * 100
        st.metric("1年以内の資金ショート確率", f"{short_rate:.2f} %")
        st.write(f"最大顧客の月商: {total_revenue * weights[0]:.1f}万円")
        st.write(f"月間固定費+変動費: {fixed_cost + total_revenue*variable_cost_rate:.1f}万円")
        
        if initial_cash < (fixed_cost + total_revenue * variable_cost_rate):
            st.error("🚨 警告：初期キャッシュが「一ヶ月の総支出」を下回っています。初月に最大顧客が遅延すれば100%ショートします。")
