import os, glob, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import dates as mdates
from tqdm import tqdm
from modules.data_loader import load_sector_stock_csv
from modules.strategy import should_exit_stock, save_stock_ohlcv
from modules.indicators import calculate_indicators
from modules.sector_map import sector_code_map
from modules.stock_filter import get_golden_supertrend_stock

# 전략 설정
MA_SHORT = 5
MA_LONG = 60
GOLDEN_LOOKBACK_DAYS = 14

start_date = "20181231"
end_date = "20241231"
initial_cash = 100000000
cash = initial_cash
fee_rate = 0.002

excluded_sector_codes = {
    "1002", "1003", "1004", "1028", "1034", "1035",
    "1150", "1151", "1152", "1153", "1154", "1155", "1156", "1157", "1158", "1159", "1160", "1167",
    "1182", "1224", "1227", "1232", "1244", "1894"
}

kospi_df = pd.read_csv("data/index_1001_코스피.csv", index_col=0, parse_dates=True)
kospi_df = kospi_df[start_date:end_date]
kospi_returns = kospi_df['종가'] / kospi_df['종가'].iloc[0] * 100
kospi_returns.index = kospi_returns.index.normalize()

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
    if sector_code in excluded_sector_codes:
        continue
    
    if position is not None:
        try:
            df_slice = position["df"].loc[:date]

            if df_slice.empty:
                print(f"⚠️ {date} 날짜에 대한 데이터가 없습니다: {position['name']}")
                continue

            # ✅ 지표 다시 계산
            df_ind = calculate_indicators(
                df_slice,
                kospi_df.loc[:date],
                ma_short=MA_SHORT,
                ma_long=MA_LONG
            )

            entry_date_normalized = pd.to_datetime(position["entry_date"]).normalize()
            current_date_normalized = date.normalize()
            holding_days = len(pd.bdate_range(entry_date_normalized, current_date_normalized)) - 1

            if holding_days < 14:
                continue

            if should_exit_stock(df_ind):
                exit_price = df_ind['종가'].iloc[-1]
                net_ret = (exit_price / position["entry_price"]) * (1 - fee_rate)**2
                cash *= net_ret
                pnl.append(cash)
                dates.append(date)
                summary_results.append({
                    "종목": position["name"],
                    "매수일": position["entry_date"],
                    "매도일": date,
                    "보유일": holding_days,
                    "수익률": net_ret - 1
                })
                pnl_events.append((date, cash, 'sell', position["name"]))
                print(f"✅ 매도 완료: {position['name']} (보유일: {holding_days}일, 수익률: {(net_ret-1)*100:.2f}%)")
                position = None

        except Exception as e:
            print(f"⚠️ 매도 처리 중 오류 발생: {position['name']} at {date} - {str(e)}")
            continue
        continue


    # 비보유 상태일 때만 진입
    try:
        sector_path = f"sector_data/sector_{sector_code}.csv"
        if not os.path.exists(sector_path):
            continue
            
        stock_dict = load_sector_stock_csv(sector_path)

        top_stock = get_golden_supertrend_stock(
            stock_dict,
            date,
            kospi_df,
            lookback_days=GOLDEN_LOOKBACK_DAYS,
            ma_short=MA_SHORT,
            ma_long=MA_LONG
        )
        
        if not top_stock:
            continue

        # ✅ 7. entry_date가 올바르게 설정되었는지 확인
        if 'entry_date' not in top_stock or pd.isna(top_stock['entry_date']):
            print(f"⚠️ entry_date가 없습니다: {top_stock.get('name', 'Unknown')}")
            continue
            
        position = top_stock
        pnl_events.append((position['entry_date'], cash, 'buy', position['name']))
        print(f"✅ 매수 완료: {position['name']} at {position['entry_date']}")
        
    except Exception as e:
        print(f"⚠️ 매수 처리 중 오류 발생: sector {sector_code} at {date} - {str(e)}")
        continue

# ✅ 마지막 날 기준 보유 종목 강제 청산
if position is not None:
    try:
        final_date = pd.to_datetime(end_date)
        final_df = position["df"].loc[:final_date]
        
        if not final_df.empty:
            exit_price = final_df['종가'].iloc[-1]
            net_ret = (exit_price / position["entry_price"]) * (1 - fee_rate)**2
            cash *= net_ret
            pnl.append(cash)
            dates.append(final_df.index[-1])
            
            # 최종 보유일 계산
            entry_date_normalized = pd.to_datetime(position["entry_date"]).normalize()
            final_date_normalized = final_date.normalize()
            final_holding_days = len(pd.bdate_range(entry_date_normalized, final_date_normalized)) - 1
            
            summary_results.append({
                "종목": position["name"],
                "매수일": position["entry_date"],
                "매도일": final_df.index[-1],
                "보유일": final_holding_days,
                "수익률": net_ret - 1
            })
            print(f"🧮 {position['name']} | 매수일: {position['entry_date']} | 매도가격: {exit_price:.2f} | 매수가격: {position['entry_price']:.2f} | 수익률: {(net_ret-1)*100:.2f}%")

            pnl_events.append((final_df.index[-1], cash, 'final-sell', position["name"]))
            print(f"✅ 최종 청산: {position['name']} (보유일: {final_holding_days}일, 수익률: {(net_ret-1)*100:.2f}%)")
        else:
            print(f"⚠️ 최종 청산 실패: {position['name']} - 데이터 없음")
            
        position = None
        
    except Exception as e:
        print(f"⚠️ 최종 청산 중 오류 발생: {position['name']} - {str(e)}")

# 결과 출력 및 그래프
if summary_results:
    summary_df = pd.DataFrame(summary_results)
    summary_df.set_index("종목", inplace=True)
    print("\n📈 수익률 종합 요약:")
    print(summary_df)

    returns = summary_df['수익률']
    cumulative_return = cash / initial_cash - 1
    win_rate = (returns > 0).sum() / len(returns)
    avg_holding_days = summary_df['보유일'].mean()
    
    # MDD 계산 (안전하게)
    mdd = 0
    if pnl:
        peak = pnl[0]
        for value in pnl:
            if value > peak:
                peak = value
            drawdown = (value - peak) / peak
            if drawdown < mdd:
                mdd = drawdown
    
    # Sharpe Ratio 계산 (안전하게)
    sharpe = 0
    if len(returns) > 1 and returns.std() > 0:
        sharpe = returns.mean() / returns.std() * (252 ** 0.5)

    print(f"\n💼 총 누적 수익률: {cumulative_return:.2%}")
    print(f"✅ 승률: {win_rate:.2%}")
    print(f"📅 평균 보유일: {avg_holding_days:.1f}일")
    print(f"📉 MDD: {mdd:.2%}")
    print(f"📈 Sharpe Ratio: {sharpe:.2f}")
    print(f"🔢 총 거래 횟수: {len(summary_results)}회")

    # 그래프 그리기
    if dates and pnl:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
        strategy_df = pd.DataFrame({"날짜": dates, "자산": pnl}).drop_duplicates(subset="날짜").sort_values("날짜").set_index("날짜")
        strategy_df.index = strategy_df.index.normalize()
        strategy_df = strategy_df.reindex(kospi_returns.index, method='ffill')
        strategy_returns = strategy_df['자산'] / initial_cash * 100

        ax1.plot(strategy_returns.index, strategy_returns, label="전략 누적 수익률", color='red')
        ax1.plot(kospi_returns.index, kospi_returns, label="KOSPI", color='gray')
        
        # 매수/매도 이벤트 표시
        for ev_date, ev_cash, ev_type, stock in pnl_events:
            ev_date = pd.to_datetime(ev_date).normalize()
            if ev_date not in strategy_returns.index:
                continue
            color = 'blue' if 'buy' in ev_type else 'green'
            yoffset = 5 if 'buy' in ev_type else -10
            ax1.annotate(f"{ev_type.upper()}\n{stock}",
                         xy=(ev_date, strategy_returns.loc[ev_date]),
                         xytext=(0, yoffset),
                         textcoords='offset points',
                         ha='center', color=color, fontsize=8,
                         arrowprops=dict(arrowstyle='->', color=color))
                         
        ax1.set_title("누적 수익률 비교: 전략 vs KOSPI")
        ax1.set_ylabel("누적 수익률 (%)")
        ax1.grid(True)
        ax1.legend()

        ax2.plot(strategy_df.index, strategy_df['자산'], label="자산 PnL", color='blue')
        ax2.set_title("총 자산 변화 (PnL)")
        ax2.set_ylabel("자산 (KRW)")
        ax2.grid(True)
        ax2.legend()

        plt.tight_layout()
        plt.show()
    else:
        print("⚠️ 그래프를 그릴 데이터가 없습니다.")
else:
    print("⚠️ 매도 조건 충족 종목이 없습니다.")