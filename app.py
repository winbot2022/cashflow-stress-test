import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# --- ページ設定 ---
st.set_page_config(page_title="資金繰り・サバイバル診断", layout="wide")

# --- フォント設定（文字化け対策） ---
FONT_PATH = 'NotoSansJP-Regular.ttf'
if os.path.exists(FONT_PATH):
    fp = fm.FontProperties(fname=FONT_PATH)
    plt.rcParams['font.family'] = fp.get_name()
    font_prop = fp
else:
    font_prop = None

st.title("🛡️ 資金繰り・ストレステスト（サバイバル可視化モデル）")
st.write("「平均値」の安心を捨て、倒産に至る『赤い線』の正体を暴く。")

# --- サイドバー：経営データの入力 ---
st.sidebar.header("📊 経営データの入力")

initial_cash = st.sidebar.number_input("1. 現在の現預金 (万円)", value=400, step=100)
st.sidebar.markdown("---")

# 入金セクション
st.sidebar.subheader("📥 入金（不確実）")
base_revenue = st.sidebar.number_input("月々のベース売上 (万円)", value=1000, step=50)
big_hit_revenue = st.sidebar.number_input("大口顧客の入金額 (万円)", value=600, step=50)

# 確率は整数で「エイ、ヤ」
hit_prob_percent = st.sidebar.slider("大口の入金遅延が発生する確率 (%)", 0, 20, 3)
hit_prob = hit_prob_percent / 100
if hit_prob_percent > 0:
    st.sidebar.caption(f"💡 およそ {100/hit_prob_percent:.1f} ヶ月に1回発生するリスクです。")

# 出金セクション
st.sidebar.subheader("📤 出金（確実な義務）")
fixed_cost = st.sidebar.number_input("月々の固定費：人件費・家賃等 (万円)", value=950, step=50)
variable_cost_rate = st.sidebar.slider("変動費率：仕入・外注費等 (%)", 0, 100, 30) / 100

st.sidebar.markdown("---")
trials = st.sidebar.select_slider("シミュレーション回数", options=[100, 1000, 10000], value=1000)

# --- テスト実行ボタン ---
execute_button = st.sidebar.button("🚀 ストレステストを実行")

if execute_button:
    months = 12
    results = []

    for _ in range(trials):
        cash = initial_cash
        cash_flow = [cash]
        for m in range(months):
            # 1. ベース売上の確定（10%のゆらぎ）
            current_base_rev = np.random.normal(base_revenue, base_revenue * 0.1)
            
            # 2. 大口入金の確定（抽選）
            is_delayed = np.random.rand() < hit_prob
            current_big_hit_rev = 0 if is_delayed else big_hit_revenue
            
            # 3. 合計入金の計算
            total_revenue = current_base_rev + current_big_hit_rev
            
            # 4. 出金の計算（変動費は大口入金予定分も含む）
            current_var_cost = (current_base_rev + big_hit_revenue) * variable_cost_rate
            total_out = fixed_cost + current_var_cost
            
            # 5. 残高更新
            cash += (total_revenue - total_out)
            cash_flow.append(cash)
        results.append(cash_flow)

    results = np.array(results)

    # --- グラフ描画 ---
    col1, col2 = st.columns([2, 1])

    with col1:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 資金ショートしたかどうかの判定（一度でも0を下回った行）
        is_short = np.any(results < 0, axis=1)
        safe_paths = results[~is_short]
        short_paths = results[is_short]

        # 1. 安全なルート（グレー：極薄）
        ax.plot(safe_paths.T, color='gray', alpha=0.01) 
        
        # 2. ショートしたルート（赤：実在感を出すために少しだけalphaを上げる）
        if len(short_paths) > 0:
            ax.plot(short_paths.T, color='#d62728', alpha=0.03) 
        
        # 3. 通常シナリオ（中央値）
        ax.plot(np.median(results, axis=0), color='#1f77b4', linewidth=4, label='通常シナリオ（中央値）')
        
        # 0のライン（死線）
        ax.axhline(0, color='black', linewidth=2.5)
        
        ax.set_title("12ヶ月間の資金推移：赤線は『一度でもショートした』試行", fontproperties=font_prop, fontsize=16)
        ax.set_xlabel("月数 (Month)", fontproperties=font_prop)
        ax.set_ylabel("現預金残高 (万円)", fontproperties=font_prop)
        ax.legend(prop=font_prop)
        st.pyplot(fig)

    with col2:
        short_count = len(short_paths)
        short_rate = (short_count / trials) * 100
        
        st.metric("1年以内の資金ショート確率", f"{short_rate:.2f} %")
        st.write(f"（{trials}回中、{short_count}回が0を割りました）")
        
        # 検算用（期待利益）
        expected_profit = (base_revenue + big_hit_revenue) * (1 - variable_cost_rate) - fixed_cost
        
        st.info(f"""
        **診断メモ:**
        - 通常時の月間純増：約 {expected_profit:.0f} 万円
        - 入金遅延時の単月インパクト：約 -{big_hit_revenue:.0f} 万円
        """)
        
        if short_rate > 30:
            st.error("🚨 極めて危険です。モデル上の赤い線が示す通り、入金遅延一発で倒産の危機に直面します。")
        elif short_rate > 5:
            st.warning("⚠️ 危険水域です。現預金の積み増しが必要です。")
        else:
            st.success("🟢 健全ですが、赤線が一本でもあればそのリスクは存在します。")

else:
    st.info("左側のサイドバーで数値を調整し、「🚀 ストレステストを実行」を押してください。")
