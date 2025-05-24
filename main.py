# main.py - 날짜 기반 루프 정렬 및 SELECT 로그 시점 일치
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from modules.signal_logic import find_leading_sectors
from modules.stock_filter import filter_first_golden_cross_stock
from modules.data_loader import load_sector_stock_csv, extract_sector_code_from_filename
from modules.sector_map import sector_code_map, valid_sector_codes
from modules.strategy import should_exit_stock, save_stock_ohlcv
from modules.indicators import ensure_indicators_cached

start_date = "20200101"
end_date = "20250101"

# Load KOSPI 100 index
kospi_df = pd.read_csv("data/index_1001_코스피.csv", index_col=0, parse_dates=True)
kospi_df = kospi_df[start_date:end_date]
kospi_returns = kospi_df['종가'] / kospi_df['종가'].iloc[0] * 100

# Load all sector data
import glob
sector_data_dict = {}
for path in glob.glob("data/index_*.csv"):
    code = extract_sector_code_from_filename(path)
    if code in valid_sector_codes:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        sector_data_dict[code] = df[start_date:end_date]

all_dates = kospi_df.index
cash = 100_000_000
position = None
portfolio = []
pnl_curve = []
returns = []

for current_date in all_dates:
    # 날짜 기준 주도 업종 계산
    active_sector_data = {
        k: v.loc[:current_date] for k, v in sector_data_dict.items()
        if current_date in v.index and len(v.loc[:current_date]) >= 60
    }
    if not active_sector_data:
        pnl_curve.append({"date": current_date, "asset": cash})
        continue

    leading_sectors = find_leading_sectors(active_sector_data, kospi_df.loc[:current_date])
    if not leading_sectors:
        pnl_curve.append({"date": current_date, "asset": cash})
        continue

    best_code, sector_name, rs = leading_sectors[0]
    from modules.crawler import ensure_sector_stock_csv
    if not ensure_sector_stock_csv(best_code):
        pnl_curve.append({"date": current_date, "asset": cash})
        continue

    sector_path = f"sector_data/sector_{best_code}.csv"
    if not os.path.exists(sector_path):
        pnl_curve.append({"date": current_date, "asset": cash})
        continue

    stock_dict = load_sector_stock_csv(sector_path)
    candidates = filter_first_golden_cross_stock(stock_dict, start_date, end_date, kospi_df)
    if not candidates:
        pnl_curve.append({"date": current_date, "asset": cash})
        continue

    ticker, name, cross_date, _ = candidates[0]
    cross_date = pd.to_datetime(str(int(float(cross_date))), format="%Y%m%d", errors='coerce')
    if pd.isna(cross_date) or cross_date > current_date:
        pnl_curve.append({"date": current_date, "asset": cash})
        continue

    print(f"[SELECT @ {current_date.date()}] ✅ 골든크로스 가장 빠른 종목: {ticker} | {name} | 날짜: {cross_date.date()}")

    stock_path = f"stock_data/{ticker}.csv"
    if not os.path.exists(stock_path):
        if not save_stock_ohlcv(ticker, start=start_date, end=end_date):
            pnl_curve.append({"date": current_date, "asset": cash})
            continue

    df_raw = pd.read_csv(stock_path, index_col=0, parse_dates=True)
    df = ensure_indicators_cached(ticker, df_raw, kospi_df)
    df = df.loc[:current_date]
    if len(df) < 60:
        pnl_curve.append({"date": current_date, "asset": cash})
        continue

    price_now = df['종가'].iloc[-1]

    if position is None:
        position = {
            "ticker": ticker, "name": name, "entry_date": current_date,
            "entry_price": price_now, "sector_code": best_code, "rs": rs
        }
        pnl_curve.append({"date": current_date, "asset": cash, "event": "buy", "label": name})
        continue

    df_pos = ensure_indicators_cached(position['ticker'], pd.read_csv(f"stock_data/{position['ticker']}.csv", index_col=0, parse_dates=True), kospi_df)
    df_pos = df_pos.loc[:current_date]
    if len(df_pos) < 2:
        pnl_curve.append({"date": current_date, "asset": cash})
        continue

    if should_exit_stock(df_pos):
        exit_price = df_pos['종가'].iloc[-1]
        ret = (exit_price / position['entry_price']) * 0.998 * 0.998
        returns.append(ret - 1)
        cash *= ret
        portfolio.append({**position, "exit_date": current_date, "exit_price": exit_price, "return": ret - 1})
        pnl_curve.append({"date": current_date, "asset": cash, "event": "sell", "label": position['name']})
        position = None
    elif best_code != position['sector_code'] and rs > position['rs']:
        exit_price = df_pos['종가'].iloc[-1]
        ret = (exit_price / position['entry_price']) * 0.998 * 0.998
        returns.append(ret - 1)
        cash *= ret
        portfolio.append({**position, "exit_date": current_date, "exit_price": exit_price, "return": ret - 1})
        pnl_curve.append({"date": current_date, "asset": cash, "event": "sell", "label": position['name']})

        position = {
            "ticker": ticker, "name": name, "entry_date": current_date,
            "entry_price": price_now, "sector_code": best_code, "rs": rs
        }
        pnl_curve.append({"date": current_date, "asset": cash, "event": "buy", "label": name})
    else:
        pnl_curve.append({"date": current_date, "asset": cash})

if position:
    df_pos = ensure_indicators_cached(position['ticker'], pd.read_csv(f"stock_data/{position['ticker']}.csv", index_col=0, parse_dates=True), kospi_df)
    df_pos = df_pos[end_date:]
    if not df_pos.empty:
        exit_price = df_pos['종가'].iloc[-1]
        ret = (exit_price / position['entry_price']) * 0.998 * 0.998
        returns.append(ret - 1)
        cash *= ret
        portfolio.append({**position, "exit_date": df_pos.index[-1], "exit_price": exit_price, "return": ret - 1})
        pnl_curve.append({"date": df_pos.index[-1], "asset": cash, "event": "sell", "label": position['name']})

## # 최종 결과 출력
    df_summary = pd.DataFrame(portfolio)
    print("\n📊 최종 성과 요약:")
    print(df_summary[['name', 'entry_date', 'exit_date', 'entry_price', 'exit_price', 'return']])

    pnl_df = pd.DataFrame(pnl_curve).drop_duplicates("date").set_index("date").sort_index()
    pnl_df = pnl_df[~pnl_df.index.duplicated(keep='first')]

    # ✅ 날짜 필터링: 포트폴리오 진입~청산 시점 기준으로 잘라줌
    backtest_start = df_summary['entry_date'].min()
    backtest_end = df_summary['exit_date'].max()
    pnl_df = pnl_df.loc[backtest_start:backtest_end]

    kospi_base_slice = kospi_df['종가'].loc[backtest_start:backtest_end]
    kospi_base_slice = kospi_base_slice / kospi_base_slice.iloc[0] * 100_000_000  # 전략과 동일 기준으로 정규화

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    ax1.plot(pnl_df.index, pnl_df['asset'], label="전략 평가자산", color='blue')
    ax1.plot(kospi_base_slice.index, kospi_base_slice, label="코스피 100 지수 (정규화)", color='gray', linestyle='--')

    for i, row in pnl_df.iterrows():
        if 'event' in row and row['event'] in ('buy', 'sell'):
            color = 'green' if row['event'] == 'buy' else 'red'
            yoffset = 5 if row['event'] == 'buy' else -10
            ax1.annotate(f"{row['event'].upper()}\n{row.get('label', '')}",
                         xy=(i, row['asset']),
                         xytext=(0, yoffset),
                         textcoords='offset points',
                         ha='center', fontsize=8, color=color,
                         arrowprops=dict(arrowstyle='->', color=color))
    ax1.set_title("전략 수익률 vs 코스피 100 비교")
    ax1.set_ylabel("자산 (KRW)")
    ax1.grid(True)
    ax1.legend()

    if returns:
        pnl_series = pd.Series(returns, name="PnL")
        ax2.plot(range(len(pnl_series)), pnl_series.cumsum(), label="누적 PnL", color='purple')
        ax2.set_title("PnL 곡선")
        ax2.set_ylabel("누적 수익률")
        ax2.grid(True)
        ax2.legend()

        mdd = (pnl_series.cumsum().cummax() - pnl_series.cumsum()).max()
        sharpe = pnl_series.mean() / pnl_series.std() * (252 ** 0.5) if pnl_series.std() != 0 else 0
        print(f"\n📉 MDD: {-mdd:.2%}")
        print(f"📈 Sharpe Ratio: {sharpe:.2f}")
# 수익률 지표 시각화
pnl_df = pd.DataFrame(pnl_curve).drop_duplicates("date").set_index("date").sort_index()
pnl_df = pnl_df[~pnl_df.index.duplicated(keep='first')]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
ax1.plot(pnl_df.index, pnl_df['asset'], label="전략 평가자산", color='blue')
ax1.set_title("자산 변화 추이")
ax1.set_ylabel("자산 (KRW)")
ax1.grid(True)
ax1.legend()

if returns:
    pnl_series = pd.Series(returns)
    cumulative = cash / 100_000_000 - 1
    win_rate = (pnl_series > 0).mean()
    mdd = (pnl_series.cumsum().cummax() - pnl_series.cumsum()).min()
    sharpe = pnl_series.mean() / pnl_series.std() * (252 ** 0.5) if pnl_series.std() > 0 else 0

    textstr = f"누적 수익률: {cumulative:.2%}\n승률: {win_rate:.2%}\nMDD: {mdd:.2%}\nSharpe: {sharpe:.2f}"
    ax1.text(0.01, 0.99, textstr, transform=ax1.transAxes, fontsize=10,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.5))

    ax2.plot(pnl_series.cumsum(), label="PnL 누적 합계", color='purple')
    ax2.set_title("누적 PnL")
    ax2.set_ylabel("수익률")
    ax2.grid(True)
    ax2.legend()

plt.xlabel("날짜")
plt.tight_layout()
plt.show()
