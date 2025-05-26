# generate_leading_sectors.py

import os
import pandas as pd
from tqdm import tqdm
from modules.data_loader import get_sector_index_ohlcv
from modules.indicators import calculate_indicators
from modules.sector_map import sector_code_map
from modules.signal_logic import find_leading_sectors

# 기본 설정
start_date = "2020-01-01"
end_date = "2025-01-01"
kospi_path = "data/index_1001_코스피.csv"
sector_dir = "data/"
output_path = "outputs/leading_sectors_timeseries.csv"
excluded_sector_codes = {"1003", "1005", "1045"}

# KOSPI 지수 불러오기
kospi_df = pd.read_csv(kospi_path, index_col=0, parse_dates=True)
kospi_df = kospi_df[start_date:end_date]

# 업종 파일 목록
files = [f for f in os.listdir(sector_dir) if f.startswith("index_") and f.endswith(".csv")]
sector_data_dict = {}
for f in files:
    code = f.split("_")[1]
    if code in excluded_sector_codes:
        continue
    df = pd.read_csv(os.path.join(sector_dir, f), index_col=0, parse_dates=True)
    df = df[start_date:end_date]
    sector_data_dict[code] = df

# 날짜 리스트 생성
date_list = kospi_df.index.strftime("%Y-%m-%d").tolist()
results = []

# 날짜별 루프
for date in tqdm(date_list):
    daily_data = {}
    for code, df in sector_data_dict.items():
        if date not in df.index or len(df.loc[:date]) < 21:
            continue
        sector_slice = df.loc[:date]
        kospi_slice = kospi_df.loc[:date]
        try:
            indicators = calculate_indicators(sector_slice, kospi_slice)
            latest = indicators.iloc[-1]
            prev = indicators.iloc[-6]

            is_supertrend = latest['Supertrend']
            is_rs_strong = latest['RS'] > 1.015
            is_rs_growing = latest['RS'] > prev['RS']

            if is_supertrend and is_rs_strong and is_rs_growing:
                daily_data[code] = latest['RS']

        except Exception as e:
            print(f"[ERROR] {code} {date} 처리 실패: {e}")
            continue

    if daily_data:
        best_sector = max(daily_data.items(), key=lambda x: x[1])
        code = best_sector[0]
        rs_value = best_sector[1]
        name = sector_code_map.get(code, f"업종코드 {code}")
        results.append({
            "date": date,
            "sector_code": code,
            "sector_name": name,
            "RS": rs_value
        })

# CSV 저장
os.makedirs("outputs", exist_ok=True)
df_result = pd.DataFrame(results)
df_result.to_csv(output_path, index=False)
print(f"\n✅ 주도 업종 시계열 저장 완료 → {output_path}")
