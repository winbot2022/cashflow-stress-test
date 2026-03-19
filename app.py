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
st.write("月間総売上は、最小値・最大値から正規分布を設定してシミュレーションします。")

# --- サイドバー設定 ---
st.sidebar.header("📊 経営データの入力")
initial_cash = st.sidebar.number_input("1. 現在の現預金 (万円)", value=300, step=100)
num_clients = st.sidebar.slider("顧客数 (社)", 1, 50, 10)

st.sidebar.subheader("月間総売上の想定レンジ")
min_revenue = st.sidebar.number_input("最小月間総売上 (万円)", value=1500, step=100)
max_revenue = st.sidebar.number_input("最大月間総売上 (万円)", value=2300, step=100)

# 入力チェック
if min_revenue > max_revenue:
    st.sidebar.error("最小月間総売上は、最大月間総売上以下にしてください。")

# 正規分布パラメータ（最小～最大を ±3σ とみなす）
mean_revenue = (min_revenue + max_revenue) / 2
std_revenue = (max_revenue - min_revenue) / 6 if max_revenue > min_revenue else 1e-6

# パレート配分（比率の計算）
raw_weights = 1.0 / (np.arange(1, num_clients + 1) ** 1.1)
weights = raw_weights / raw_weights.sum()

# 各社の基準売上高（平均月商ベース）
client_revenues = mean_revenue * weights

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
    if min_revenue > max_revenue:
        st.error("最小月間総売上が最大月間総売上を上回っています。入力を見直してください。")
    else:
        months = 12
        results = []

        for _ in range(trials):
            cash = initial_cash
            pending_pools = np.zeros(num_clients)
            cash_flow = [cash]

            for m in range(months):
                # A. 当月の月間総売上を正規分布から生成
                monthly_total_sales = np.random.normal(mean_revenue, std_revenue)

                # 実務上の想定として、最小値・最大値の範囲にクリップ
                monthly_total_sales = np.clip(monthly_total_sales, min_revenue, max_revenue)

                # 顧客別売上に配分
                current_sales = monthly_total_sales * weights

                # 出金
                outflow = fixed_cost + (current_sales.sum() * variable_cost_rate)

                # 入金
                inflow = 0
                for i in range(num_clients):
                    # 滞留分の回収
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
            ax.legend(prop=font_prop)
            st.pyplot(fig)

        with col2:
            short_rate = (np.sum(is_short) / trials) * 100
            st.metric("1年以内の資金ショート確率", f"{short_rate:.2f} %")

            st.write("**前提とした月間総売上分布**")
            st.info(
                f"""
- 最小月間総売上: **{min_revenue:.1f}万円**
- 最大月間総売上: **{max_revenue:.1f}万円**
- 想定平均売上: **{mean_revenue:.1f}万円**
- 推定標準偏差: **{std_revenue:.1f}万円**
"""
            )

            st.write("**上位10社の基準売上高（万円）**")
            display_data = client_revenues[:min(10, num_clients)]
            st.bar_chart(display_data)

            st.info(
                f"""
- 最大顧客の基準売上: **{client_revenues[0]:.1f}万円**
- 平均月間の総支出目安: **{fixed_cost + mean_revenue * variable_cost_rate:.1f}万円**
"""
            )

            if short_rate > 10:
                st.error(
                    f"最大顧客（基準売上 {client_revenues[0]:.1f}万円）の入金遅延が重なると、"
                    "月間の支払い継続が難しくなる構造です。"
                )
