# data_loader.py

import os
import pandas as pd
from pykrx import stock

def load_sector_stock_csv(filepath):
    """
    sector_data/ 경로에 저장된 업종별 종목 리스트 CSV 로딩
    """
    try:
        df = pd.read_csv(filepath, dtype={"code": str})
        return dict(zip(df['code'], df['name']))
    except Exception as e:
        print(f"[ERROR] CSV 로딩 실패: {e}")
        return {}

def get_sector_index_ohlcv(code: str, start: str, end: str) -> pd.DataFrame:
    """
    업종별 시계열 데이터 로컬 CSV에서 로딩
    파일 경로: data/index_{code}.csv
    """
    path = f"data/index_{code}.csv"
    if not os.path.exists(path):
        print(f"[ERROR] 업종 코드 {code} CSV 없음 → {path}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        df = df[start:end]
        return df
    except Exception as e:
        print(f"[ERROR] 업종 코드 {code} CSV 로딩 실패: {e}")
        return pd.DataFrame()

def get_stock_ohlcv(code: str, start: str, end: str) -> pd.DataFrame:
    """
    종목 시세 데이터 로컬 → fallback으로 pykrx API
    파일 경로: stock_data/{code}.csv
    """
    local_path = f"stock_data/{code}.csv"
    if os.path.exists(local_path):
        try:
            df = pd.read_csv(local_path, index_col=0, parse_dates=True)
            df = df[start:end]
            return df
        except Exception as e:
            print(f"[WARN] 로컬 파일 로딩 실패, API 재시도: {e}")

    # fallback to API
    try:
        df = stock.get_market_ohlcv_by_date(start, end, code)
        df.columns.name = None
        os.makedirs("stock_data", exist_ok=True)
        df.to_csv(local_path)
        print(f"[SAVE] {code} 시세 저장 완료")
        return df
    except Exception as e:
        print(f"[ERROR] 종목 코드 {code} API 호출 실패: {e}")
        return pd.DataFrame()

def extract_sector_code_from_filename(filename):
    basename = os.path.basename(filename)
    parts = basename.replace(".csv", "").split("_")
    if len(parts) >= 2:
        return parts[1]
    return None
