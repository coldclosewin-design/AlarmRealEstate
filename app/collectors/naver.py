"""네이버 부동산 시세 수집기 (best-effort)."""

import logging

import httpx

from app.models import Property

log = logging.getLogger(__name__)

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://new.land.naver.com/",
}


def _get_complex_detail(complex_id: str) -> dict | None:
    """단지 상세 정보를 조회한다."""
    url = f"https://new.land.naver.com/api/complexes/{complex_id}"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            log.warning("네이버 단지 조회 실패 (status=%d): %s", resp.status_code, complex_id)
            return None
        return resp.json()
    except Exception as e:
        log.warning("네이버 단지 조회 에러: %s", e)
        return None


def _get_complex_prices(complex_id: str, area_no: str = "") -> dict | None:
    """단지 시세 정보를 조회한다."""
    url = f"https://new.land.naver.com/api/complexes/{complex_id}/prices"
    params = {}
    if area_no:
        params["areaNo"] = area_no
    try:
        resp = httpx.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code != 200:
            log.warning("네이버 시세 조회 실패 (status=%d): %s", resp.status_code, complex_id)
            return None
        return resp.json()
    except Exception as e:
        log.warning("네이버 시세 조회 에러: %s", e)
        return None


def _find_area_no(detail: dict, target_area: float) -> str:
    """단지 상세에서 해당 면적의 areaNo를 찾는다."""
    for area_info in detail.get("complexDetail", {}).get("pyoEngInfoList", []):
        area = float(area_info.get("exclusiveArea", 0))
        if abs(area - target_area) < 2:
            return str(area_info.get("pyoEngNo", ""))
    return ""


def fetch_prices(prop: Property) -> dict:
    """
    네이버 부동산에서 매매/전세 시세를 조회한다.

    Returns:
        {
            "매매_만원": int | None,
            "매매_prev_만원": int | None,
            "전세_만원": int | None,
            "전세_prev_만원": int | None,
        }
    """
    result: dict = {
        "매매_만원": None,
        "매매_prev_만원": None,
        "전세_만원": None,
        "전세_prev_만원": None,
    }

    if not prop.naver_complex_id:
        log.info("네이버 complex_id 미설정: %s", prop.name)
        return result

    detail = _get_complex_detail(prop.naver_complex_id)
    area_no = ""
    if detail:
        area_no = _find_area_no(detail, prop.area_m2)

    prices = _get_complex_prices(prop.naver_complex_id, area_no)
    if not prices:
        log.info("네이버 시세 데이터 없음: %s", prop.name)
        return result

    # 시세 파싱: 네이버 API 응답 구조에 따라 유연하게 처리
    market_prices = prices.get("marketPrices", {})

    for deal_type_key, result_key_prefix in [
        ("dealPrices", "매매"), ("leasePrices", "전세")
    ]:
        price_list = market_prices.get(deal_type_key, [])
        if not price_list:
            continue

        # 최신 시세
        latest = price_list[-1] if price_list else None
        if latest:
            avg_price = latest.get("averagePrice")
            if avg_price is not None:
                result[f"{result_key_prefix}_만원"] = int(avg_price)

        # 전월 시세
        if len(price_list) >= 2:
            prev = price_list[-2]
            avg_price = prev.get("averagePrice")
            if avg_price is not None:
                result[f"{result_key_prefix}_prev_만원"] = int(avg_price)

    log.info("네이버 시세 %s: 매매=%s, 전세=%s", prop.name, result["매매_만원"], result["전세_만원"])
    return result
