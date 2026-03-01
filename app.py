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

st.title("🛡️ 資金繰り・ストレステスト（全社回収リスク・V字回復モデル）")
st.write("「黒字倒産」の正体：利益は出ているのに、回収の『谷』で力尽きるリスクを可視化する。")

# --- サイドバー：経営データの入力（戦略的デフォルト値） ---
st.sidebar.header("📊 経営データの入力")

# 1. 現預金（少し心許ない300万に設定）
initial_cash = st.sidebar.number_input("1. 現在の現預金 (万円)", value=300, step=100)
st.sidebar.markdown("---")

# 2. 売上セクション
st.sidebar.subheader("📥 入金構造")
base_revenue = st.sidebar.number_input("月々のベース売上 (万円)", value=1500, step=50)
big_hit_revenue = st.sidebar.number_input("大口顧客の売上（予定） (万円)", value=400, step=50)

# 3. 回収リスク（全社一律に適用）
st.sidebar.subheader("⚠️ 回収遅延リスク")
collection_risk_prob = st.sidebar.slider("回収遅延（全社的）が発生する確率 (%)", 0, 20, 5)
collection_rate_on_hit = st.sidebar.slider("遅延発生時の回収率 (%)", 0, 100, 70) / 100

if collection_risk_prob > 0:
    st.sidebar.caption(f"💡 {100/collection_risk_prob:.1f} ヶ月に1回、全売上の {100 - (collection_rate_on_hit*100):.0f}% が翌月にスライドする計算です。")

# 4. 出金セクション（義務）
st.sidebar.subheader("📤 出金（確実な義務）")
fixed_cost = st.sidebar.number_input("月々の固定費：人件費・家賃等 (万円)", value=1000, step=50)
variable_cost_rate = st.sidebar.slider("変動費率 (%)", 0, 100, 40) / 100

st.sidebar.markdown("---")
trials = st.sidebar.select_slider("シミュレーション回数", options=[100, 1000, 10000], value=1000)

# --- シミュレーション実行 ---
execute_button = st.sidebar.button("🚀 ストレステストを実行")

if execute_button:
    months = 12
    results = []

    for _ in range(trials):
        cash = initial_cash
        pending_cash = 0  # 翌月に持ち越される未回収金
        cash_flow = [cash]
        
        for m in range(months):
            # A. 売上の発生（10%のゆらぎ）
            planned_sales = base_revenue + big_hit_revenue
            actual_sales = np.random.normal(planned_sales, planned_sales * 0.1)
            
            # B. 回収の抽選（V字回復ロジック）
            is_hit = np.random.rand() < (collection_risk_prob / 100)
            
            if is_hit:
                # 遅延発生：一部だけ入金、残りは翌月へ
                inflow = (actual_sales * collection_rate_on_hit) + pending_cash
                pending_cash = actual_sales * (1 - collection_rate_on_hit)
            else:
                # 平時：今月分 ＋ 前月の未回収分を全額回収
                inflow = actual_sales + pending_cash
                pending_cash = 0
            
            # C. 出金（売上に応じた変動費 ＋ 固定費）
            # 入金が遅れても、仕事をした分の変動費は発生する
            outflow = fixed_cost + (actual_sales * variable_cost_rate)
            
            # D. 残高更新
            cash += (inflow - outflow)
            cash_flow.append(cash)
            
        results.append(cash_flow)

    results = np.array(results)

    # --- グラフ描画 ---
    col1, col2 = st.columns([2, 1])

    with col1:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 資金ショート判定
        is_short = np.any(results < 0, axis=1)
        safe_paths = results[~is_short]
        short_paths = results[is_short]

        # 1. 安全なルート（グレー）
        ax.plot(safe_paths.T, color='gray', alpha=0.01) 
        
        # 2. ショートしたルート（赤：V字の谷が可視化される）
        if len(short_paths) > 0:
            ax.plot(short_paths.T, color='#d62728', alpha=0.05) 
        
        # 3. 通常シナリオ（中央値：青太線）
        ax.plot(np.median(results, axis=0), color='#1f77b4', linewidth=4, label='通常シナリオ（中央値）')
        
        # 死線
        ax.axhline(0, color='black', linewidth=2.5)
        
        ax.set_title("12ヶ月間の資金推移：赤線は一時的でも0を割った試行", fontproperties=font_prop, fontsize=16)
        ax.set_xlabel("月数 (Month)", fontproperties=font_prop)
        ax.set_ylabel("現預金残高 (万円)", fontproperties=font_prop)
        ax.legend(prop=font_prop)
        st.pyplot(fig)

    with col2:
        short_count = len(short_paths)
        short_rate = (short_count / trials) * 100
        
        st.metric("1年以内の資金ショート確率", f"{short_rate:.2f} %")
        st.write(f"（{trials}回中、{short_count}回が回収の『谷』に落ちました）")
        
        # 理論上の月間収支（平時）
        expected_profit = (base_revenue + big_hit_revenue) * (1 - variable_cost_rate) - fixed_cost
        # 遅延発生時のインパクト
        impact = (base_revenue + big_hit_revenue) * (1 - collection_rate_on_hit)
        
        st.info(f"""
        **診断メモ:**
        - 通常時の月間利益：約 {expected_profit:.0f} 万円
        - 遅延発生時のキャッシュ減：約 -{impact:.0f} 万円
        """)
        
        if short_rate > 10:
            st.error("🚨 警告：今の現預金では、全社的な回収遅延が一度起きるだけで致命傷になります。")
        elif short_rate > 0:
            st.warning("⚠️ 注意：序盤の蓄積が少ない時期にリスクが集中しています。")
        else:
            st.success("🟢 健全です。回収遅延が起きても耐えられる厚みがあります。")

else:
    st.info("サイドバーで経営数値を入力し、「🚀 ストレステストを実行」を押してください。")
