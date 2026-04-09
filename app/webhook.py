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
    """RegionReport를 Discord 임베드 목록으로 변환한다."""
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")

    if not report.transactions:
        return [{
            "title": f"📊 {report.region.name} 실거래 리포트",
            "color": COLOR_DEFAULT,
            "description": "최근 3개월 실거래 데이터가 없습니다.",
            "footer": {"text": f"출처: 국토교통부 실거래가  |  {now}"},
        }]

    # 아파트별로 그룹핑
    by_apt: dict[str, list] = defaultdict(list)
    for tx in report.transactions:
        by_apt[tx.apt_name].append(tx)

    # 요약 임베드: 아파트별 최근 거래 1건씩
    summary_lines = []
    for apt_name in sorted(by_apt.keys()):
        latest = by_apt[apt_name][0]  # 이미 날짜순 정렬됨
        summary_lines.append(
            f"**{apt_name}**  {latest.area_m2:.0f}m²  {format_price(latest.price_만원)}  `{latest.date}`"
        )

    # Discord 임베드 description은 4096자 제한
    embeds = []
    chunk_size = 30  # 아파트 30개씩 한 임베드
    for i in range(0, len(summary_lines), chunk_size):
        chunk = summary_lines[i : i + chunk_size]
        embed = {
            "title": f"📊 {report.region.name} 실거래 리포트" + (f" ({i // chunk_size + 1})" if i > 0 else ""),
            "color": COLOR_DEFAULT,
            "description": "\n".join(chunk),
            "footer": {"text": f"총 {len(report.transactions)}건 (최근 3개월)  |  출처: 국토교통부  |  {now}"},
        }
        embeds.append(embed)

    return embeds


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
