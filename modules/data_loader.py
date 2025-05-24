import pandas as pd, os
from pykrx import stock

def load_sector_stock_csv(filepath):
    try:
        df = pd.read_csv(filepath, dtype={"code": str})
        return dict(zip(df['code'], df['name']))
    except Exception as e:
        print(f"[ERROR] CSV 로딩 실패: {e}")
        return {}

    
def get_sector_index_ohlcv(code: str, start: str, end: str) -> pd.DataFrame:
    try:
        df = stock.get_index_ohlcv_by_date(start, end, code)
        df.columns.name = None
        return df
    except Exception as e:
        print(f"[ERROR] 업종 코드 {code} 데이터 로딩 실패: {e}")
        return pd.DataFrame()


def get_stock_ohlcv(code, start, end):
    try:
        df = stock.get_market_ohlcv_by_date(start, end, code)
        df.columns.name = None
        return df
    except Exception as e:
        print(f"[ERROR] 종목 코드 {code} 데이터 로딩 실패: {e}")
        return pd.DataFrame()

def extract_sector_code_from_filename(filename):
    basename = os.path.basename(filename)
    parts = basename.replace(".csv", "").split("_")
    if len(parts) >= 2:
        return parts[1]
    return None

# import pandas as pd
# import os
# from pykrx import stock
# from modules.sector_map import valid_sector_codes

# def load_sector_stock_csv(filepath):
#     try:
#         df = pd.read_csv(filepath, dtype={"code": str})
#         return dict(zip(df['code'], df['name']))
#     except Exception as e:
#         print(f"[ERROR] CSV 로딩 실패: {filepath} | {e}")
#         return {}

# def get_sector_index_ohlcv(code: str, start: str, end: str) -> pd.DataFrame:
#     try:
#         df = stock.get_index_ohlcv_by_date(start, end, code)
#         df.columns.name = None
#         return df
#     except Exception as e:
#         print(f"[ERROR] 업종 코드 {code} 데이터 로딩 실패: {e}")
#         return pd.DataFrame()

# def get_stock_ohlcv(code, start, end):
#     local_path = f"stock_data/{code}.csv"
#     if os.path.exists(local_path):
#         try:
#             df = pd.read_csv(local_path, index_col=0, parse_dates=True)
#             df = df[start:end]
#             return df
#         except Exception as e:
#             print(f"[ERROR] 로컬 파일 {code} 로딩 실패: {e}")
#     # fallback to API
#     try:
#         df = stock.get_market_ohlcv_by_date(start, end, code)
#         df.columns.name = None
#         return df
#     except Exception as e:
#         print(f"[ERROR] 종목 코드 {code} API 호출 실패: {e}")
#         return pd.DataFrame()

# def extract_sector_code_from_filename(filename):
#     basename = os.path.basename(filename)
#     parts = basename.replace(".csv", "").split("_")
#     if len(parts) >= 2:
#         return parts[1]
#     return None

# def is_valid_sector_file(filepath):
#     code = extract_sector_code_from_filename(filepath)
#     return code in valid_sector_codes if code else False

# def load_all_valid_sector_files(directory="data"):
#     import glob
#     sector_files = glob.glob(f"{directory}/index_*.csv")
#     sector_data_dict = {}
#     for path in sector_files:
#         if not is_valid_sector_file(path):
#             continue
#         code = extract_sector_code_from_filename(path)
#         try:
#             df = pd.read_csv(path, index_col=0, parse_dates=True)
#             sector_data_dict[code] = df
#         except Exception as e:
#             print(f"[ERROR] 섹터 파일 로딩 실패: {path} | {e}")
#     return sector_data_dict
