"""Discord 웹훅 전송 + 임베드 빌더."""

import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import httpx

from app.config import DISCORD_WEBHOOK_URL
from app.models import RegionReport

log = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

COLOR_DEFAULT = 0x3498DB  # 파란색


def format_price(만원: int) -> str:
    """만원 단위를 한국식으로 포맷한다. 예: 345000 → '34억 5,000만원'"""
    if 만원 >= 10000:
        억 = 만원 // 10000
        나머지 = 만원 % 10000
        if 나머지 == 0:
            return f"{억}억"
        return f"{억}억 {나머지:,}만원"
    return f"{만원:,}만원"


def build_embeds(report: RegionReport) -> list[dict]:
    """RegionReport를 단지별 최근 5건씩 Discord 임베드로 변환한다."""
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")

    if not report.transactions:
        return [{
            "title": f"📊 {report.region.name} — 새 거래 없음",
            "color": COLOR_DEFAULT,
            "description": "새로운 실거래 데이터가 없습니다.",
            "footer": {"text": f"출처: 국토교통부 실거래가  |  {now}"},
        }]

    # 아파트별로 그룹핑
    by_apt: dict[str, list] = defaultdict(list)
    for tx in report.transactions:
        by_apt[tx.apt_name].append(tx)

    # 단지별 최근 5건씩 fields로 구성 (최신 거래가 있는 단지가 위로)
    fields = []
    sorted_apts = sorted(by_apt.keys(), key=lambda name: by_apt[name][0].date, reverse=True)
    for apt_name in sorted_apts:
        txs = by_apt[apt_name][:5]
        lines = []
        for tx in txs:
            lines.append(f"`{tx.date}`  {tx.area_m2:.0f}m²  {tx.floor}층  **{format_price(tx.price_만원)}**")
        fields.append({
            "name": f"🏠 {apt_name} ({len(by_apt[apt_name])}건)",
            "value": "\n".join(lines),
            "inline": False,
        })

    # Discord 임베드는 fields 최대 25개, 단지 4개면 충분
    return [{
        "title": f"🆕 {report.region.name} 새 실거래 감지",
        "color": COLOR_DEFAULT,
        "fields": fields,
        "footer": {"text": f"새 거래 {len(report.transactions)}건  |  출처: 국토교통부  |  {now}"},
    }]


def send_report(reports: list[RegionReport]) -> None:
    """Discord 웹훅으로 리포트를 전송한다."""
    if not DISCORD_WEBHOOK_URL:
        log.error("DISCORD_WEBHOOK_URL이 설정되지 않았습니다")
        return

    embeds = []
    for r in reports:
        embeds.extend(build_embeds(r))

    for i in range(0, len(embeds), 10):
        batch = embeds[i : i + 10]
        payload = {
            "username": "부동산 시세 알리미",
            "embeds": batch,
        }
        try:
            resp = httpx.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
            resp.raise_for_status()
            log.info("Discord 전송 완료 (%d개 임베드)", len(batch))
        except httpx.HTTPError as e:
            log.error("Discord 웹훅 전송 실패: %s", e)
