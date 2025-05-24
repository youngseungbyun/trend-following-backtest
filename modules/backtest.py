import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta

def simulate_buy_and_hold(ticker, buy_date, hold_days=20):
    start = pd.to_datetime(buy_date)
    end = start + timedelta(days=hold_days * 2)
    df = stock.get_market_ohlcv_by_date(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), ticker)
    df = df.reset_index()
    df = df[df['날짜'] >= start]
    if len(df) < hold_days:
        return None
    buy_price = df.iloc[0]['종가']
    sell_price = df.iloc[hold_days - 1]['종가']
    return (sell_price - buy_price) / buy_price

def run_rotation_strategy(candidates, base_date, hold_days=60):
    result_log = []
    for code, name, *_ in candidates:
        df = stock.get_market_ohlcv_by_date("20200101", "20251231", code).reset_index()
        df['MA5'] = df['종가'].rolling(5).mean()
        df['MA60'] = df['종가'].rolling(60).mean()
        df = df[df['날짜'] >= pd.to_datetime(base_date)].copy()
        df.reset_index(drop=True, inplace=True)
        if df.empty or len(df) < 70:
            continue
        entry_price = None
        for i in range(1, len(df)):
            ma5 = df.at[i, 'MA5']
            ma60 = df.at[i, 'MA60']
            date = df.at[i, '날짜']
            if entry_price is None:
                if ma5 > ma60 and df.at[i - 1, 'MA5'] <= df.at[i - 1, 'MA60']:
                    entry_price = df.at[i, '종가']
                    entry_index = i
                    entry_date = date
            else:
                if ma5 < ma60 and df.at[i - 1, 'MA5'] >= df.at[i - 1, 'MA60']:
                    exit_price = df.at[i, '종가']
                    exit_date = date
                    result_log.append({
                        "종목": name,
                        "매수일": entry_date.strftime("%Y-%m-%d"),
                        "매도일": exit_date.strftime("%Y-%m-%d"),
                        "수익률": (exit_price - entry_price) / entry_price
                    })
                    break
                if i - entry_index >= hold_days:
                    exit_price = df.at[i, '종가']
                    exit_date = date
                    result_log.append({
                        "종목": name,
                        "매수일": entry_date.strftime("%Y-%m-%d"),
                        "매도일": exit_date.strftime("%Y-%m-%d"),
                        "수익률": (exit_price - entry_price) / entry_price
                    })
                    break
    return result_log

def evaluate_backtest_results(results):
    if not results:
        return {}
    df = pd.Series(results)
    cumulative = df.sum()
    average = df.mean()
    win_rate = (df > 0).sum() / len(df)
    equity = (1 + df).cumprod()
    drawdown = (equity / equity.cummax()) - 1
    mdd = drawdown.min()
    sharpe = df.mean() / df.std() if df.std() > 0 else None
    return {
        "종목 수": len(df),
        "누적 수익률": cumulative,
        "평균 수익률": average,
        "승률": win_rate,
        "MDD": mdd,
        "Sharpe": sharpe
    }