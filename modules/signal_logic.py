from modules.indicators import calculate_indicators
from modules.sector_map import sector_code_map

def find_leading_sectors(sector_data_dict, kospi_df):
    leading_sectors = []

    for code, df in sector_data_dict.items():
        try:
            df_ind = calculate_indicators(df, kospi_df)
            if len(df_ind) < 21:
                continue

            latest = df_ind.iloc[-1]
            prev = df_ind.iloc[-6]

            is_supertrend = latest['Supertrend']
            is_rs_strong = latest['RS'] > 1.05
            is_rs_growing = latest['RS'] > prev['RS']

            if is_supertrend and is_rs_strong and is_rs_growing:
                name = sector_code_map.get(code, f"업종코드 {code}")
                leading_sectors.append((code, name, latest['RS']))

        except Exception as e:
            print(f"[ERROR] 업종 코드 {code} 계산 실패: {e}")

    return sorted(leading_sectors, key=lambda x: x[2], reverse=True)
