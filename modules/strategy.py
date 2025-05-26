import pandas as pd
from pykrx import stock
import os

def should_exit_stock(df, rsi_threshold=75):
    """보유 중인 종목의 매도 조건 판단 (RSI 과매수 + MA 데드크로스)"""
    if len(df) < 2:
        return False

    is_dead_cross = df['MA5'].iloc[-1] < df['MA60'].iloc[-1] and df['MA5'].iloc[-2] >= df['MA60'].iloc[-2]
    is_rsi_overbought = df['RSI'].iloc[-1] > rsi_threshold

    if is_dead_cross:
        print(f"[EXIT] 데드크로스 발생")
        return True
    if is_rsi_overbought:
        print(f"[EXIT] RSI 과매수 ({df['RSI'].iloc[-1]:.2f}) > {rsi_threshold}")
        return True

    return False


def save_stock_ohlcv(ticker, start="20200101", end="20250101", path="stock_data"):
    """종목 시세 저장 (캐싱)"""
    df = stock.get_market_ohlcv_by_date(start, end, ticker)
    if df is not None and not df.empty:
        os.makedirs(path, exist_ok=True)
        df.to_csv(f"{path}/{ticker}.csv")
        print(f"[SAVE] {ticker} 저장 완료")
        return True
    else:
        print(f"[FAIL] {ticker} 저장 실패")
        return False
