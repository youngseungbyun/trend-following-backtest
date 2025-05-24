import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from modules.naver_upjong_map import naver_upjong_map
from modules.sector_map import sector_code_map

def get_sector_stocks(sector_code):
    """네이버 업종 페이지에서 종목 코드 + 이름 크롤링"""
    naver_code = naver_upjong_map.get(sector_code)
    if not naver_code:
        print(f"[SKIP] KRX 업종 코드 {sector_code}는 네이버 업종 번호로 매핑되지 않음")
        return {}

    url = f"https://finance.naver.com/sise/sise_group_detail.naver?type=upjong&no={naver_code}"
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if res.status_code != 200:
            print(f"[ERROR] 네이버 요청 실패: status {res.status_code}")
            return {}
    except Exception as e:
        print(f"[ERROR] 네이버 업종 페이지 요청 실패: {e}")
        return {}

    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.select_one("table.type_5")
    if not table:
        print(f"[ERROR] 네이버 업종 코드 {naver_code}의 종목 테이블을 찾을 수 없습니다.")
        return {}

    stock_dict = {}
    for row in table.select("tr")[2:]:
        cols = row.select("td")
        if len(cols) < 2:
            continue
        a_tag = cols[0].select_one("a")
        if a_tag and "code" in a_tag.get("href"):
            code = a_tag.get("href").split("code=")[-1]
            name = a_tag.text.strip()
            stock_dict[code] = name

    return stock_dict


def ensure_sector_stock_csv(sector_code):
    """해당 업종 코드의 종목 리스트를 sector_data/에 저장 (이미 있으면 생략)"""
    path = f"sector_data/sector_{sector_code}.csv"

    # ✅ 이미 존재하면 로딩 시도
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            if not df.empty and "code" in df.columns and "name" in df.columns:
                print(f"[SKIP] {sector_code} 업종 데이터 이미 존재 → 생략")
                return True
        except Exception as e:
            print(f"[WARN] {sector_code} CSV 검증 실패, 재다운로드 시도: {e}")

    # ✅ 실제 크롤링 진행
    stock_dict = get_sector_stocks(sector_code)
    if stock_dict:
        os.makedirs("sector_data", exist_ok=True)
        df = pd.DataFrame(list(stock_dict.items()), columns=["code", "name"])
        df.to_csv(path, index=False)
        print(f"[SAVE] {path} 저장 완료")
        return True
    else:
        print(f"[FAIL] {sector_code} 업종 종목 크롤링 실패")
        return False
