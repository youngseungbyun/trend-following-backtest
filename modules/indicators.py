# indicators.py

import pandas as pd
import os
def calculate_ma(df, short, long):
    df = df.copy()
    df[f'MA{short}'] = df['종가'].rolling(short).mean()
    df[f'MA{long}'] = df['종가'].rolling(long).mean()
    
    # ✅ MA60은 항상 추가 (매도 조건용)
    if 'MA60' not in df.columns:
        df['MA60'] = df['종가'].rolling(60).mean()

    df['GoldenCross'] = (df[f'MA{short}'] > df[f'MA{long}']) & \
                        (df[f'MA{short}'].shift(1) <= df[f'MA{long}'].shift(1))

    df['DeadCross'] = (df[f'MA{short}'] < df['MA60']) & \
                      (df[f'MA{short}'].shift(1) >= df['MA60'].shift(1))
    return df

def calculate_supertrend(df, period=10, multiplier=3):
    df = df.copy()
    hl2 = (df['고가'] + df['저가']) / 2
    tr = pd.concat([
        df['고가'] - df['저가'],
        abs(df['고가'] - df['종가'].shift()),
        abs(df['저가'] - df['종가'].shift())
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    upperband = hl2 + multiplier * atr
    lowerband = hl2 - multiplier * atr

    supertrend = [True] * len(df)
    for i in range(1, len(df)):
        curr_close = df['종가'].iloc[i]
        if curr_close > upperband.iloc[i - 1]:
            supertrend[i] = True
        elif curr_close < lowerband.iloc[i - 1]:
            supertrend[i] = False
        else:
            supertrend[i] = supertrend[i - 1]
            if supertrend[i] and lowerband.iloc[i] < lowerband.iloc[i - 1]:
                lowerband.iloc[i] = lowerband.iloc[i - 1]
            if not supertrend[i] and upperband.iloc[i] > upperband.iloc[i - 1]:
                upperband.iloc[i] = upperband.iloc[i - 1]

    df['Supertrend'] = supertrend
    return df

def calculate_rs(sector_df, kospi_df):
    rs_raw = sector_df['종가'] / kospi_df['종가']
    rs_index = rs_raw / rs_raw.rolling(20).mean()
    return rs_index

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_indicators(df, kospi_df, ma_short=5, ma_long=60):
    """
    전체 지표 계산 함수 (파라미터로 MA 기준 설정 가능)
    - ma_short: 골든/데드크로스용 단기 이동평균
    - ma_long: 골든/데드크로스용 장기 이동평균
    """
    df = df.copy()
    df = calculate_supertrend(df)
    df = calculate_ma(df, ma_short, ma_long)
    df['RSI'] = calculate_rsi(df['종가'])
    df['RS'] = calculate_rs(df, kospi_df)
    return df

def ensure_indicators_cached(ticker, df, kospi_df, path='indicators'):
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, f"{ticker}.csv")
    if os.path.exists(file_path):
        return pd.read_csv(file_path, index_col=0, parse_dates=True)
    df_ind = calculate_indicators(df, kospi_df)
    df_ind.to_csv(file_path)
    return df_ind
