# --- シミュレーションループ内（一部抜粋） ---
for m in range(months):
    # 1. 売上の発生
    current_sales = np.random.normal(total_revenue, total_revenue * 0.05) * weights
    outflow = fixed_cost + (current_sales.sum() * variable_cost_rate)
    
    inflow = 0
    for i in range(num_clients):
        # 修正ポイント：滞留分の回収を「新規遅延」の判定より先に行う
        # これにより、今月発生した遅延分が今月中に回収されるのを防ぐ
        recovered = pending_pools[i] * (recovery_rate / 100)
        inflow += recovered
        pending_pools[i] -= recovered
        
        # 新規遅延の判定
        if np.random.rand() < (hit_prob / 100):
            # 遅延：今月は0、全額が来月以降の回収プールへ
            pending_pools[i] += current_sales[i]
        else:
            # 正常：全額入金
            inflow += current_sales[i]
            
    # 月末残高
    cash = cash - outflow + inflow
    cash_flow.append(cash)
