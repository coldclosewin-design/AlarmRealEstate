"""국토교통부 아파트 실거래가 API 수집기."""

import logging
from datetime import datetime, timedelta

import httpx
import xmltodict

from app.config import MOLIT_API_KEY
from app.models import Property, Transaction

log = logging.getLogger(__name__)

BASE_URL = (
    "https://apis.data.go.kr"
    "/1613000/RTMSDataSvcAptTradeDev"
    "/getRTMSDataSvcAptTradeDev"
)


def _deal_months(months: int = 3) -> list[str]:
    """최근 N개월의 YYYYMM 목록을 반환한다."""
    now = datetime.now()
    result = []
    for i in range(months):
        dt = now - timedelta(days=30 * i)
        result.append(dt.strftime("%Y%m"))
    return list(dict.fromkeys(result))  # 중복 제거, 순서 유지


def _parse_items(xml_text: str) -> list[dict]:
    """XML 응답에서 item 목록을 추출한다."""
    parsed = xmltodict.parse(xml_text)
    body = parsed.get("response", {}).get("body", {})
    items = body.get("items", {})
    if items is None:
        return []
    item = items.get("item", [])
    if isinstance(item, dict):
        return [item]
    return item


def fetch_trades(prop: Property, months: int = 3) -> list[Transaction]:
    """특정 부동산의 최근 실거래 내역을 조회한다."""
    transactions: list[Transaction] = []

    for ym in _deal_months(months):
        # serviceKey는 이미 URL 인코딩된 상태이므로 URL에 직접 삽입
        url = (
            f"{BASE_URL}"
            f"?serviceKey={MOLIT_API_KEY}"
            f"&LAWD_CD={prop.region_code}"
            f"&DEAL_YMD={ym}"
            f"&pageNo=1"
            f"&numOfRows=9999"
        )
        try:
            resp = httpx.get(url, timeout=30)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("국토부 API 요청 실패 (%s %s): %s", prop.region_code, ym, e)
            continue

        for item in _parse_items(resp.text):
            apt_name = str(item.get("아파트", "")).strip()
            area = float(item.get("전용면적", 0))

            # 단지명 포함 여부 + 면적 ±5㎡ 필터
            if prop.complex_name not in apt_name:
                continue
            if abs(area - prop.area_m2) > 5:
                continue

            year = str(item.get("년", "")).strip()
            month = str(item.get("월", "")).strip().zfill(2)
            day = str(item.get("일", "")).strip().zfill(2)
            price_str = str(item.get("거래금액", "0")).strip().replace(",", "")

            transactions.append(
                Transaction(
                    property_name=prop.name,
                    price_만원=int(price_str),
                    date=f"{year}-{month}-{day}",
                    floor=str(item.get("층", "")).strip(),
                    area_m2=area,
                    source="molit",
                    deal_type="매매",
                )
            )

    transactions.sort(key=lambda t: t.date, reverse=True)
    log.info(
        "국토부 실거래 %s: %d건 수집",
        prop.name,
        len(transactions),
    )
    return transactions
