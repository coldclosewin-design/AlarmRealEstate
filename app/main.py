"""부동산 시세 자동 알람 - 엔트리포인트."""

import logging

from app.config import load_properties
from app.models import Region, RegionReport
from app.collectors import molit
from app.webhook import send_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def main() -> None:
    log.info("부동산 시세 알람 시작")

    raw = load_properties()
    log.info("관심 지역 %d건 로드", len(raw))

    regions = [
        Region(
            name=r["name"],
            region_code=r["region_code"],
            apt_filter=r.get("apt_filter", []),
            area_m2=r.get("area_m2", 0),
        )
        for r in raw
    ]

    reports = []
    for region in regions:
        try:
            transactions = molit.fetch_region_trades(region)
            reports.append(RegionReport(region=region, transactions=transactions))
        except Exception:
            log.exception("리포트 생성 실패: %s", region.name)

    if reports:
        send_report(reports)
    else:
        log.warning("전송할 리포트가 없습니다")

    log.info("부동산 시세 알람 완료")


if __name__ == "__main__":
    main()
