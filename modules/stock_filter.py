# stock_filter.py

import pandas as pd
from modules.data_loader import get_stock_ohlcv
from modules.indicators import calculate_indicators

def get_top_supertrend_stock(stock_dict, date, kospi_df):
    """
    업종 내 종목 중:
        - Supertrend가 상승 중(True)
        - 시세 100일 이상 존재
        - 해당 날짜까지 데이터 존재
        - ATR이 가장 높은 종목 1개 선정
    """
    top_atr = -float("inf")
    best = None

    for code, name in stock_dict.items():
        df = get_stock_ohlcv(code, "20200101", "20250101")
        if df.empty or date not in df.index or len(df) < 100:
            continue
        try:
            df_ind = calculate_indicators(df.loc[:date], kospi_df.loc[:date])
            if df_ind.empty or "Supertrend" not in df_ind.columns:
                continue

            # Supertrend가 상승 중인 종목만 후보로 인정
            if not df_ind["Supertrend"].iloc[-1]:
                continue

            # ATR 계산 (calculate_indicators에서 같이 계산되도록 해야 함)
            if "ATR" not in df_ind.columns:
                continue  # 안전망

            atr = df_ind["ATR"].iloc[-1]
            if pd.notna(atr) and atr > top_atr:
                top_atr = atr
                best = {
                    "code": code,
                    "name": name,
                    "entry_price": df_ind['종가'].iloc[-1],
                    "entry_date": df_ind.index[-1],
                    "df": df_ind
                }
        except Exception as e:
            print(f"[WARN] {code} 처리 실패: {e}")
            continue

    if best:
        print(f"[SELECT] ✅ Supertrend 상승 + ATR 최고 종목: {best['code']} | {best['name']} | ATR: {top_atr:.4f}")
    else:
        print("[SELECT] ❌ 조건 만족하는 종목 없음")

    return best
