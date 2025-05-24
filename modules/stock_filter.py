from modules.data_loader import get_stock_ohlcv
from modules.indicators import calculate_indicators
import pandas as pd

def filter_first_golden_cross_stock(stock_dict, start_date, end_date, kospi_df):
    first_cross = None

    for code, name in stock_dict.items():
        df = get_stock_ohlcv(code, start_date, end_date)
        if df.empty or len(df) < 100:
            continue

        df = calculate_indicators(df, kospi_df)
        if 'MA5' not in df or 'MA60' not in df:
            continue

        for i in range(1, len(df)):
            prev_ma5 = df['MA5'].iloc[i - 1]
            prev_ma60 = df['MA60'].iloc[i - 1]
            curr_ma5 = df['MA5'].iloc[i]
            curr_ma60 = df['MA60'].iloc[i]

            if pd.notna(prev_ma5) and pd.notna(prev_ma60) and pd.notna(curr_ma5) and pd.notna(curr_ma60):
                if prev_ma5 <= prev_ma60 and curr_ma5 > curr_ma60:
                    cross_date = df.index[i]
                    if (first_cross is None) or (cross_date < first_cross['date']):
                        first_cross = {
                            'code': code,
                            'name': name,
                            'date': cross_date,
                            'ma5': curr_ma5,
                            'ma60': curr_ma60
                        }
                    break  # 종목당 첫 골든크로스만 확인

    if first_cross:
        print(f"[SELECT] ✅ 골든크로스 가장 빠른 종목: {first_cross['code']} | {first_cross['name']} | 날짜: {first_cross['date'].date()}")
        return [(first_cross['code'], first_cross['name'], first_cross['ma5'], first_cross['ma60'])]
    else:
        print("[FILTER] ❌ 골든크로스 발생 종목 없음")
        return []
