# 프로젝트 구조 기준 전체 Python 파일 구성 및 전략 흐름 정리 (2025 최신, 자동 저장 매크로 포함)

# 📁 pykrx/trend_following_project/

# ├── main.py
import os, glob, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import dates as mdates
from modules.signal_logic import find_leading_sectors
from modules.stock_filter import filter_first_golden_cross_stock
from modules.data_loader import load_sector_stock_csv
from modules.data_loader import get_sector_index_ohlcv
from modules.sector_map import sector_code_map
from modules.crawler import ensure_sector_stock_csv
from modules.indicators import calculate_rsi
from modules.strategy import should_exit_stock, save_stock_ohlcv
import numpy as np

excluded_sector_codes = {"1003", "1005", "1045"}
start_date = "20200101"
end_date = "20250101"
kospi_df = pd.read_csv("data/index_1001_코스피.csv", index_col=0, parse_dates=True)
kospi_df = kospi_df[start_date:end_date]
kospi_returns = kospi_df['종가'] / kospi_df['종가'].iloc[0] * 100
kospi_returns.index = kospi_returns.index.normalize()

files = glob.glob("data/index_*.csv")
sector_data_dict = {}
for path in files:
    code = path.split("_")[1]
    if code in excluded_sector_codes:
        continue
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    sector_data_dict[code] = df

leading_sectors = find_leading_sectors(sector_data_dict, kospi_df)
print(f"[DEBUG] 주도 업종 수: {len(leading_sectors)}")

summary_results = []
pnl = []
dates = []
pnl_events = []

initial_cash = 100000000  # 1억 원 시작
cash = initial_cash

for code, _, rs in leading_sectors:
    if code in excluded_sector_codes:
        continue

    name = sector_code_map.get(code, f"업종코드 {code}")
    print(f"\n🔥 주도 업종: {code} | {name} | RS: {rs:.2f}")

    ensure_sector_stock_csv(code)
    sector_path = f"sector_data/sector_{code}.csv"
    if not os.path.exists(sector_path):
        continue
    stock_dict = load_sector_stock_csv(sector_path)
    candidates = filter_first_golden_cross_stock(stock_dict, start_date, end_date, kospi_df)

    print("📈 매수 후보 종목:")
    for c in candidates:
        print(f"  ✔️ {c}")

    if not candidates:
        continue

    for ticker, name, *_ in candidates:
        stock_path = f"stock_data/{ticker}.csv"
        if not os.path.exists(stock_path):
            save_stock_ohlcv(ticker, start_date, end_date)
        if not os.path.exists(stock_path):
            continue

        df = pd.read_csv(stock_path, index_col=0, parse_dates=True)
        df['RSI'] = calculate_rsi(df['종가'])
        df['MA5'] = df['종가'].rolling(5).mean()
        df['MA60'] = df['종가'].rolling(60).mean()

        entry_price = None
        for i in range(60, len(df)):
            if entry_price is None:
                if df['MA5'].iloc[i] > df['MA60'].iloc[i] and df['MA5'].iloc[i-1] <= df['MA60'].iloc[i-1]:
                    entry_price = df['종가'].iloc[i]
                    entry_date = df.index[i]
                    pnl_events.append((entry_date, cash, 'buy', name))
                    break

        if entry_price:
            for j in range(i+1, len(df)):
                if should_exit_stock(df.iloc[:j+1]):
                    exit_price = df['종가'].iloc[j]
                    exit_date = df.index[j]
                    fee = 0.002
                    net_return = (exit_price / entry_price) * (1 - fee)**2
                    cash *= net_return
                    summary_results.append({
                        "종목": name,
                        "매수일": entry_date,
                        "매도일": exit_date,
                        "수익률": net_return - 1
                    })
                    pnl.append(cash)
                    dates.append(exit_date)
                    pnl_events.append((exit_date, cash, 'sell', name))
                    break

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
