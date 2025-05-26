# stock_filter.py

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
    Supertrend가 상승(True)이고,
    최근 lookback_days 이내에 MA[short] vs MA[long] 골든크로스 발생한 종목 중
    첫 번째 종목을 반환

    파라미터:
    - ma_short: 단기 이동평균 기간 (기본 5)
    - ma_long: 장기 이동평균 기간 (기본 60)
    - lookback_days: 골든크로스 발생 여부 확인 기간
    """
    best = None

    for code, name in stock_dict.items():
        df = get_stock_ohlcv(code, "20200101", "20250101")
        if df.empty or date not in df.index or len(df) < max(ma_short, ma_long, lookback_days):
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

            if not df_ind['Supertrend'].iloc[-1]:
                continue

            recent = df_ind.iloc[-lookback_days:]
            if recent['GoldenCross'].any():
                best = {
                    "code": code,
                    "name": name,
                    "entry_price": df_ind['종가'].iloc[-1],
                    "entry_date": df_ind.index[-1],
                    "df": df_ind
                }
                print(f"[SELECT] ✅ 골든크로스 + Supertrend 종목: {code} | {name}")
                break

        except Exception as e:
            print(f"[WARN] {code} 지표 계산 실패: {e}")
            continue

    if not best:
        print("[FILTER] ❌ 조건 만족 종목 없음")
    return best
