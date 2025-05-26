# strategy.py

import pandas as pd
from pykrx import stock
import os

def should_exit_stock(df, rsi_threshold=86, trailing_stop_pct=0.18):
    """
    보유 중인 종목의 매도 조건 판단
    조건:
    - RSI > rsi_threshold
    - MA5 < MA60 데드크로스
    - 고점 대비 trailing_stop_pct 이상 하락 시 매도
    """
    if len(df) < 2:
        return False

    # ✅ 데드크로스 체크
    is_dead_cross = df['MA5'].iloc[-1] < df['MA60'].iloc[-1] and df['MA5'].iloc[-2] >= df['MA60'].iloc[-2]

    # ✅ RSI 과매수 체크
    is_rsi_overbought = df['RSI'].iloc[-1] > rsi_threshold

    # ✅ 트레일링 스탑 체크
    max_price = df['종가'].max()
    current_price = df['종가'].iloc[-1]
    stop_price = max_price * (1 - trailing_stop_pct)
    is_trailing_stop = current_price < stop_price

    # 출력 로그
    if is_dead_cross:
        print(f"[EXIT] MA 데드크로스 발생")
        return True
    if is_rsi_overbought:
        print(f"[EXIT] RSI 과매수: {df['RSI'].iloc[-1]:.2f} > {rsi_threshold}")
        return True
    if is_trailing_stop:
        print(f"[EXIT] 트레일링 스탑 발동: 종가 {current_price:.2f} < {stop_price:.2f} (고점 {max_price:.2f})")
        return True

    return False

def save_stock_ohlcv(ticker, start="20181231", end="20241231", path="stock_data"):
    """
    종목 시세 저장 (캐싱)
    """
    df = stock.get_market_ohlcv_by_date(start, end, ticker)
    if df is not None and not df.empty:
        os.makedirs(path, exist_ok=True)
        df.to_csv(f"{path}/{ticker}.csv")
        print(f"[SAVE] {ticker} 저장 완료")
        return True
    else:
        print(f"[FAIL] {ticker} 저장 실패")
        return False
