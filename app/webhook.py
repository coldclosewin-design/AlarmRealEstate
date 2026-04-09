"""Discord 웹훅 전송 + 임베드 빌더."""

import logging
from datetime import datetime, timezone, timedelta

import httpx

from app.config import DISCORD_WEBHOOK_URL
from app.models import PriceReport

log = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

COLOR_UP = 0x2ECC71      # 초록
COLOR_DOWN = 0xE74C3C     # 빨강
COLOR_STABLE = 0x95A5A6   # 회색


def format_price(만원: int) -> str:
    """만원 단위를 한국식으로 포맷한다. 예: 345000 → '34억 5,000만원'"""
    if 만원 >= 10000:
        억 = 만원 // 10000
        나머지 = 만원 % 10000
        if 나머지 == 0:
            return f"{억}억"
        return f"{억}억 {나머지:,}만원"
    return f"{만원:,}만원"


def _embed_color(report: PriceReport) -> int:
    """최근 거래가 있으면 초록, 없으면 회색."""
    if report.recent_transactions:
        return COLOR_UP
    return COLOR_STABLE


def build_embed(report: PriceReport) -> dict:
    """PriceReport를 Discord 임베드 dict로 변환한다."""
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    fields = []

    if report.recent_transactions:
        lines = []
        for tx in report.recent_transactions[:5]:
            lines.append(
                f"`{tx.date}`  {tx.area_m2:.0f}m²  {tx.floor}층  **{format_price(tx.price_만원)}**"
            )
        fields.append({
            "name": "최근 실거래 (국토교통부)",
            "value": "\n".join(lines),
            "inline": False,
        })
    else:
        fields.append({
            "name": "알림",
            "value": "최근 3개월 실거래 데이터가 없습니다.",
            "inline": False,
        })

    return {
        "title": f"🏠 {report.prop.name}",
        "color": _embed_color(report),
        "fields": fields,
        "footer": {
            "text": f"출처: 국토교통부 실거래가  |  {now}"
        },
    }


def send_report(reports: list[PriceReport]) -> None:
    """Discord 웹훅으로 리포트를 전송한다."""
    if not DISCORD_WEBHOOK_URL:
        log.error("DISCORD_WEBHOOK_URL이 설정되지 않았습니다")
        return

    embeds = [build_embed(r) for r in reports]

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
