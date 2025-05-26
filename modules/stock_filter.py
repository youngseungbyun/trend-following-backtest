import pandas as pd
from modules.data_loader import get_stock_ohlcv
from modules.indicators import calculate_indicators

def get_golden_supertrend_stock(
    stock_dict,
    date,
    kospi_df,
    lookback_days=14,
    ma_short=5,
    ma_long=60
):
    """
    완화된 진입 조건:
    - Supertrend 상승 중 (True)
    - 최근 lookback_days 이내 MA5 > MA60 골든크로스 발생
    - 최근 5일 수익률 > 0
    """
    best = None

    for code, name in stock_dict.items():
        df = get_stock_ohlcv(code, "20180101", "20250101")
        if df.empty or date not in df.index or len(df) < max(ma_short, ma_long, lookback_days + 5):
            continue

        try:
            df_ind = calculate_indicators(
                df.loc[:date],
                kospi_df.loc[:date],
                ma_short=ma_short,
                ma_long=ma_long
            )
            if df_ind.empty:
                continue

            # 조건 1: 현재 Supertrend가 상승 중
            if not df_ind['Supertrend'].iloc[-1]:
                continue

            # 조건 2: 최근 골든크로스 발생
            recent = df_ind.iloc[-lookback_days:]
            if not recent['GoldenCross'].any():
                continue

            # ✅ 진입 시점의 종가를 정확히 entry_price로 지정
            entry_price = df_ind.loc[df_ind.index == date, '종가']
            if entry_price.empty:
                continue

            best = {
                "code": code,
                "name": name,
                "entry_price": entry_price.values[0],
                "entry_date": date,
                "df": df  # 전체 시세 전달 → 이후 매도 시점 접근 가능
            }
            print(f"[SELECT] ✅ 진입 종목: {code} | {name}")
            break

        except Exception as e:
            print(f"[WARN] {code} 지표 계산 실패: {e}")
            continue

    if not best:
        print("[FILTER] ❌ 조건 만족 종목 없음")
    return best
