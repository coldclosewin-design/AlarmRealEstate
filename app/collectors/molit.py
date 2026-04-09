"""국토교통부 아파트 실거래가 API 수집기."""

import logging
from datetime import datetime, timedelta

import httpx
import xmltodict

from app.config import MOLIT_API_KEY
from app.models import Region, Transaction

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
    return list(dict.fromkeys(result))


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


def fetch_region_trades(region: Region, months: int = 6) -> list[Transaction]:
    """지역의 최근 실거래 내역을 조회한다. apt_filter가 있으면 해당 단지만."""
    transactions: list[Transaction] = []

    for ym in _deal_months(months):
        url = (
            f"{BASE_URL}"
            f"?serviceKey={MOLIT_API_KEY}"
            f"&LAWD_CD={region.region_code}"
            f"&DEAL_YMD={ym}"
            f"&pageNo=1"
            f"&numOfRows=9999"
        )
        try:
            resp = httpx.get(url, timeout=30)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("국토부 API 요청 실패 (%s %s): %s", region.region_code, ym, e)
            continue

        for item in _parse_items(resp.text):
            apt_name = str(item.get("aptNm", "")).strip()

            # 필터가 있으면 해당 단지만 수집
            if region.apt_filter:
                if not any(f in apt_name for f in region.apt_filter):
                    continue

            price_str = str(item.get("dealAmount", "0")).strip().replace(",", "")
            year = str(item.get("dealYear", "")).strip()
            month = str(item.get("dealMonth", "")).strip().zfill(2)
            day = str(item.get("dealDay", "")).strip().zfill(2)

            transactions.append(
                Transaction(
                    apt_name=apt_name,
                    price_만원=int(price_str),
                    date=f"{year}-{month}-{day}",
                    floor=str(item.get("floor", "")).strip(),
                    area_m2=float(item.get("excluUseAr", 0)),
                    deal_type="매매",
                )
            )

    transactions.sort(key=lambda t: t.date, reverse=True)
    log.info("국토부 실거래 %s: %d건 수집", region.name, len(transactions))
    return transactions
