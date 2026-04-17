"""부동산 시세 자동 알람 - 엔트리포인트."""

import logging

from app.config import load_properties
from app.models import Region, RegionReport
from app.collectors import molit
from app.state import load_seen_keys, save_seen_keys, filter_new_transactions, mark_as_seen
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

    seen = load_seen_keys()
    log.info("이전 전송 기록: %d건", len(seen))

    reports = []
    all_new_transactions = []

    for region in regions:
        try:
            transactions = molit.fetch_region_trades(region)
            new_txs = filter_new_transactions(transactions, seen)
            if new_txs:
                reports.append(RegionReport(region=region, transactions=new_txs))
                all_new_transactions.extend(new_txs)
                log.info("%s: 새 거래 %d건 감지", region.name, len(new_txs))
            else:
                log.info("%s: 새 거래 없음", region.name)
        except Exception:
            log.exception("리포트 생성 실패: %s", region.name)

    if reports:
        send_report(reports)
        seen = mark_as_seen(all_new_transactions, seen)
        save_seen_keys(seen)
    else:
        log.info("새 거래가 없어 전송하지 않습니다")

    log.info("부동산 시세 알람 완료")


if __name__ == "__main__":
    main()
