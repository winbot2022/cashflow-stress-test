import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# --- ページ設定 ---
st.set_page_config(page_title="資金繰り・成長リスクシミュレーター", layout="wide")

# --- フォント設定 ---
FONT_PATH = 'NotoSansJP-Regular.ttf'
if os.path.exists(FONT_PATH):
    fp = fm.FontProperties(fname=FONT_PATH)
    plt.rcParams['font.family'] = fp.get_name()
    font_prop = fp
else:
    font_prop = None

st.title("🚀 資金繰り・成長リスクシミュレーター")
st.write("「新規大口取引」がもたらす資金の谷（デスバレー）を可視化します。")

# --- サイドバー設定 ---
st.sidebar.header("📊 1. 既存事業のベースライン")
initial_cash = st.sidebar.number_input("現在の現預金 (万円)", value=500, step=100)
base_revenue = st.sidebar.number_input("既存の月間総売上 (万円)", value=1500, step=50)
fixed_cost = st.sidebar.number_input("既存の固定費 (万円)", value=1000, step=50)
var_cost_rate = st.sidebar.slider("既存の変動費率 (%)", 0, 100, 40) / 100

st.sidebar.markdown("---")
st.sidebar.header("⚡ 2. 新規大口取引の条件")
new_deal_rev = st.sidebar.number_input("新規取引の月間売上 (万円)", value=1000, step=100)
new_deal_var_rate = st.sidebar.slider("新規取引の変動費率 (%)", 0, 100, 60) / 100
start_month = st.sidebar.slider("取引開始月 (支出発生)", 1, 6, 3)
payment_lag = st.sidebar.slider("入金までのラグ (ヶ月)", 1, 6, 2)

st.sidebar.markdown("---")
st.sidebar.header("⚠️ リスク設定")
hit_prob = st.sidebar.slider("既存顧客の遅延確率 (%)", 0, 50, 5)

execute_button = st.sidebar.button("🚀 成長リスクをシミュレート")

if execute_button:
    months = 18 # 成長後の安定まで見るため18ヶ月に延長
    trials = 1000
    results = []
    
    for _ in range(trials):
        cash = initial_cash
        pending_pool = 0 # 既存顧客の滞留金
        cash_flow = [cash]
        
        for m in range(1, months + 1):
            # A. 既存事業の計算
            current_base_sales = np.random.normal(base_revenue, base_revenue * 0.05)
            # 既存の出金
            base_outflow = fixed_cost + (current_base_sales * var_cost_rate)
            
            # B. 新規取引の計算
            new_outflow = 0
            new_inflow = 0
            if m >= start_month:
                # 支出は開始月から発生
                new_outflow = new_deal_rev * new_deal_var_rate
                # 入金はラグを経て発生
                if m >= (start_month + payment_lag):
                    new_inflow = new_deal_rev
            
            # C. 回収計算（既存事業のみリスクありとする）
            inflow = 0
            # 前月までの滞留分を50%ずつ回収
            recovered = pending_pool * 0.5
            inflow += recovered
            pending_pool -= recovered
            
            if np.random.rand() < (hit_prob / 100):
                pending_pool += current_base_sales
            else:
                inflow += current_base_sales
            
            # D. 月末キャッシュ更新
            total_in = inflow + new_inflow
            total_out = base_outflow + new_outflow
            cash = cash - total_out + total_in
            cash_flow.append(cash)

        results.append(cash_flow)

    results = np.array(results)

    # --- 描画 ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig, ax = plt.subplots(figsize=(10, 6))
        is_short = np.any(results < 0, axis=1)
        
        # 描画
        time_axis = np.arange(months + 1)
        ax.plot(time_axis, results[~is_short].T, color='gray', alpha=0.02)
        if np.any(is_short):
            ax.plot(time_axis, results[is_short].T, color='#d62728', alpha=0.04)
        
        ax.plot(time_axis, np.median(results, axis=0), color='#1f77b4', linewidth=4, label='通常推移')
        ax.axhline(0, color='black', linewidth=2)
        
        # 新規取引の重要ライン
        ax.axvline(start_month, color='green', linestyle='--', label='取引開始（支出発生）')
        ax.axvline(start_month + payment_lag, color='orange', linestyle='--', label='初回収（入金開始）')
        
        ax.set_title("成長の罠：新規取引に伴う『資金の谷』", fontproperties=font_prop, fontsize=16)
        ax.legend(prop=font_prop)
        st.pyplot(fig)

    with col2:
        short_rate = (np.sum(is_short) / trials) * 100
        st.metric("ショート確率（成長リスク込）", f"{short_rate:.2f} %")
        
        # 最も深く凹むポイントの特定
        median_path = np.median(results, axis=0)
        deepest_point = np.min(median_path)
        required_buffer = abs(min(0, deepest_point))
        
        st.subheader("💡 診断結果")
        if deepest_point < initial_cash:
            st.warning(f"新規取引により、最大で残高が **{initial_cash - deepest_point:.0f}万円** 減少します。")
        
        if short_rate > 20:
            st.error(f"この取引を開始するには、現在の現預金では不十分です。開始までに最低でも **{required_buffer + 500:.0f}万円** の追加資金（融資）を確保してください。")
        
        st.info(f"""
        **シミュレーションの構造:**
        - {start_month}ヶ月目に新規取引のコストが発生
        - {start_month + payment_lag}ヶ月目に初めて売上が入金
        - その間の **{payment_lag}ヶ月間** が最も危険なゾーンです。
        """)
