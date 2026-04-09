"""부동산 시세 자동 알람 - 엔트리포인트."""

import logging

from app.config import load_properties
from app.models import Property, PriceReport
from app.collectors import molit, naver
from app.webhook import send_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def build_report(prop: Property) -> PriceReport:
    """하나의 부동산에 대해 데이터를 수집하고 리포트를 생성한다."""
    # 국토부 실거래가 수집
    transactions = molit.fetch_trades(prop)

    # 네이버 시세 수집
    naver_prices = naver.fetch_prices(prop)

    return PriceReport(
        prop=prop,
        naver_price_만원=naver_prices["매매_만원"],
        naver_prev_price_만원=naver_prices["매매_prev_만원"],
        jeonse_price_만원=naver_prices["전세_만원"],
        jeonse_prev_price_만원=naver_prices["전세_prev_만원"],
        recent_transactions=transactions,
    )


def main() -> None:
    log.info("부동산 시세 알람 시작")

    raw_properties = load_properties()
    log.info("관심 부동산 %d건 로드", len(raw_properties))

    properties = [
        Property(
            name=p["name"],
            region_code=p["region_code"],
            complex_name=p["complex_name"],
            area_m2=p["area_m2"],
            naver_complex_id=p.get("naver_complex_id", ""),
        )
        for p in raw_properties
    ]

    reports = []
    for prop in properties:
        try:
            report = build_report(prop)
            reports.append(report)
        except Exception:
            log.exception("리포트 생성 실패: %s", prop.name)

    if reports:
        send_report(reports)
    else:
        log.warning("전송할 리포트가 없습니다")

    log.info("부동산 시세 알람 완료")


if __name__ == "__main__":
    main()
