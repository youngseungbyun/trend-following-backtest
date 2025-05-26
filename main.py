# main.py

import os, glob, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import dates as mdates
from tqdm import tqdm
from modules.data_loader import load_sector_stock_csv, get_stock_ohlcv
from modules.strategy import should_exit_stock, save_stock_ohlcv
from modules.indicators import calculate_indicators
from modules.sector_map import sector_code_map
from modules.stock_filter import get_top_supertrend_stock  # ✅ 변경된 함수 사용

# 기본 설정
start_date = "20200101"
end_date = "20210501"
initial_cash = 100000000
cash = initial_cash
fee_rate = 0.002
excluded_sector_codes = {"1003", "1005", "1045"}

# KOSPI 시계열 불러오기
kospi_df = pd.read_csv("data/index_1001_코스피.csv", index_col=0, parse_dates=True)
kospi_df = kospi_df[start_date:end_date]
kospi_returns = kospi_df['종가'] / kospi_df['종가'].iloc[0] * 100
kospi_returns.index = kospi_returns.index.normalize()

# 시그널 로딩 (한글 컬럼명 대응)
signals = pd.read_csv("outputs/leading_sectors_timeseries.csv", parse_dates=["날짜"])
signals = signals[(signals["날짜"] >= start_date) & (signals["날짜"] <= end_date)]

position = None
summary_results = []
pnl = []
dates = []
pnl_events = []

for _, row in tqdm(signals.iterrows(), total=len(signals)):
    date = pd.to_datetime(row['날짜'])
    sector_code = str(row["업종코드"])
    sector_name = row["업종명"]
    if sector_code in excluded_sector_codes:
        continue

    sector_path = f"sector_data/sector_{sector_code}.csv"
    if not os.path.exists(sector_path):
        continue
    stock_dict = load_sector_stock_csv(sector_path)

    top_stock = get_top_supertrend_stock(stock_dict, date, kospi_df)  # ✅ 여기 변경
    if not top_stock:
        continue

    # 신규 진입 or 교체매매
    if position is None:
        position = top_stock
        pnl_events.append((position['entry_date'], cash, 'buy', position['name']))
        continue
    elif position["code"] != top_stock["code"]:
        exit_price = position["df"]["종가"].iloc[-1]
        net_ret = (exit_price / position["entry_price"]) * (1 - fee_rate)**2
        cash *= net_ret
        pnl.append(cash)
        dates.append(date)
        summary_results.append({
            "종목": position["name"],
            "매수일": position["entry_date"],
            "매도일": date,
            "수익률": net_ret - 1
        })
        pnl_events.append((date, cash, 'sell', position["name"]))

        # 교체 진입
        position = top_stock
        pnl_events.append((position['entry_date'], cash, 'buy', position['name']))
        continue

    # 동일 종목 유지 → 매도 조건 확인
    if should_exit_stock(position["df"]):
        exit_price = position["df"]["종가"].iloc[-1]
        net_ret = (exit_price / position["entry_price"]) * (1 - fee_rate)**2
        cash *= net_ret
        pnl.append(cash)
        dates.append(date)
        summary_results.append({
            "종목": position["name"],
            "매수일": position["entry_date"],
            "매도일": date,
            "수익률": net_ret - 1
        })
        pnl_events.append((date, cash, 'sell', position["name"]))
        position = None

# ✅ 성과 출력 및 기존 그래프 그대로 유지
if summary_results:
    summary_df = pd.DataFrame(summary_results)
    summary_df.set_index("종목", inplace=True)
    print("\n📈 수익률 종합 요약:")
    print(summary_df)

    returns = summary_df['수익률']
    cumulative_return = cash / initial_cash - 1
    win_rate = (returns > 0).sum() / len(returns)
    mdd = min((min(pnl[:i+1]) / max(pnl[:i+1]) - 1) for i in range(len(pnl))) if pnl else 0
    sharpe = returns.mean() / returns.std() * (252 ** 0.5) if returns.std() > 0 else 0

    print(f"\n💼 총 누적 수익률: {cumulative_return:.2%}")
    print(f"✅ 승률: {win_rate:.2%}")
    print(f"📉 MDD: {mdd:.2%}")
    print(f"📈 Sharpe Ratio: {sharpe:.2f}")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    strategy_df = pd.DataFrame({"날짜": dates, "자산": pnl}).drop_duplicates(subset="날짜").sort_values("날짜").set_index("날짜")
    strategy_df.index = strategy_df.index.normalize()
    strategy_df = strategy_df.reindex(kospi_returns.index, method='ffill')
    strategy_returns = strategy_df['자산'] / initial_cash * 100

    # 누적 수익률 그래프
    ax1.plot(strategy_returns.index, strategy_returns, label="전략 누적 수익률", color='red')
    ax1.plot(kospi_returns.index, kospi_returns, label="KOSPI", color='gray')
    for ev_date, ev_cash, ev_type, stock in pnl_events:
        ev_date = pd.to_datetime(ev_date).normalize()
        if ev_date not in strategy_returns.index:
            continue
        color = 'blue' if ev_type == 'buy' else 'green'
        yoffset = 5 if ev_type == 'buy' else -10
        ax1.annotate(f"{ev_type.upper()}\n{stock}",
                     xy=(ev_date, strategy_returns.loc[ev_date]),
                     xytext=(0, yoffset),
                     textcoords='offset points',
                     ha='center', color=color,
                     arrowprops=dict(arrowstyle='->', color=color))
    ax1.set_title("누적 수익률 비교: 전략 vs KOSPI")
    ax1.set_ylabel("누적 수익률 (%)")
    ax1.grid(True)
    ax1.legend()

    # PnL 자산 곡선
    ax2.plot(strategy_df.index, strategy_df['자산'], label="자산 PnL", color='blue')
    ax2.set_title("총 자산 변화 (PnL)")
    ax2.set_ylabel("자산 (KRW)")
    ax2.grid(True)
    ax2.legend()

    plt.tight_layout()
    plt.show()
else:
    print("⚠️ 매도 조건 충족 종목이 없습니다.")
