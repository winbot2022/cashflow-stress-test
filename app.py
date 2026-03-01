import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

st.set_page_config(page_title="資金繰り・サバイバル診断", layout="wide")

# --- フォント設定（文字化け対策） ---
FONT_PATH = 'NotoSansJP-Regular.ttf'
if os.path.exists(FONT_PATH):
    # フォントプロパティを設定
    fp = fm.FontProperties(fname=FONT_PATH)
    # matplotlibのデフォルトフォントとして登録
    plt.rcParams['font.family'] = fp.get_name()
    # グラフ描画時に明示的にフォントを指定するための変数
    font_prop = fp
else:
    st.error(f"フォントファイル {FONT_PATH} が見つかりません。")
    font_prop = None

st.title("🛡️ 資金繰り・ストレステスト（入出金分離モデル）")
st.write("「平均値」の安心を捨て、不運の重なりを可視化する。")

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
trials = st.sidebar.select_slider("シミュレーション回数", options=[100, 1000, 10000], value=1000)

# --- テスト実行ボタン ---
execute_button = st.sidebar.button("🚀 ストレステストを実行")

# --- シミュレーション実行 ---
if execute_button:
    months = 12
    results = []

    for _ in range(trials):
        cash = initial_cash
        cash_flow = [cash]
        for m in range(months):
            # --- 修正後の計算ロジック ---
        
            # 1. ベース売上の確定（ゆらぎ10%）
            current_base_rev = np.random.normal(base_revenue, base_revenue * 0.1)
            
            # 2. 大口入金の確定（抽選）
            is_delayed = np.random.rand() < hit_prob
            current_big_hit_rev = 0 if is_delayed else big_hit_revenue
            
            # 3. 合計入金の計算
            total_revenue = current_base_rev + current_big_hit_rev
            
            # 4. 出金の計算
            # 変動費は「実際に発生したベース売上」＋「大口（入金に関わらず仕事はしたと仮定）」に対して発生
            current_var_cost = (current_base_rev + big_hit_revenue) * variable_cost_rate
            total_out = fixed_cost + current_var_cost
            
            # 5. 残高更新
            cash += (total_revenue - total_out)
            cash_flow.append(cash)
            results.append(cash_flow)

    results = np.array(results)

    # --- 結果の表示 ---
    col1, col2 = st.columns([2, 1])

    with col1:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(results.T, color='gray', alpha=0.01) 
        ax.plot(np.median(results, axis=0), color='#1f77b4', linewidth=3, label='通常シナリオ（中央値）')
        ax.plot(np.percentile(results, 5, axis=0), color='#d62728', linestyle='--', linewidth=2, label='最悪のシナリオ（下位5%）')
        
        ax.axhline(0, color='black', linewidth=1.5)
        
        # グラフタイトルの日本語対応
        ax.set_title("12ヶ月間の資金推移シミュレーション", fontproperties=font_prop, fontsize=16)
        ax.set_xlabel("月数 (Month)", fontproperties=font_prop)
        ax.set_ylabel("現預金残高 (万円)", fontproperties=font_prop)
        ax.legend(prop=font_prop)
        
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
else:
    st.info("サイドバーの「🚀 ストレステストを実行」ボタンを押すと、1万回のシミュレーションが開始されます。")
