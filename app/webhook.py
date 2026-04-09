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


def _trend(current: int | None, prev: int | None) -> tuple[str, float | None]:
    """변동 화살표와 변동률을 반환한다."""
    if current is None or prev is None or prev == 0:
        return "─", None
    change_pct = (current - prev) / prev * 100
    if change_pct > 0.1:
        return "▲", change_pct
    elif change_pct < -0.1:
        return "▼", change_pct
    return "─", 0.0


def _embed_color(report: PriceReport) -> int:
    """시세 변동에 따른 임베드 색상을 결정한다."""
    arrow, _ = _trend(report.naver_price_만원, report.naver_prev_price_만원)
    if arrow == "▲":
        return COLOR_UP
    elif arrow == "▼":
        return COLOR_DOWN
    return COLOR_STABLE


def build_embed(report: PriceReport) -> dict:
    """PriceReport를 Discord 임베드 dict로 변환한다."""
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    fields = []

    # 매매 시세 (네이버)
    if report.naver_price_만원 is not None:
        arrow, pct = _trend(report.naver_price_만원, report.naver_prev_price_만원)
        value = f"현재: **{format_price(report.naver_price_만원)}**"
        if report.naver_prev_price_만원 is not None:
            diff = report.naver_price_만원 - report.naver_prev_price_만원
            sign = "+" if diff >= 0 else ""
            value += f"\n전월: {format_price(report.naver_prev_price_만원)}"
            value += f"\n변동: {arrow} {sign}{pct:.1f}% ({sign}{format_price(abs(diff))})" if pct is not None else ""
        fields.append({"name": "매매 시세", "value": value, "inline": True})

    # 전세 시세 (네이버)
    if report.jeonse_price_만원 is not None:
        arrow, pct = _trend(report.jeonse_price_만원, report.jeonse_prev_price_만원)
        value = f"현재: **{format_price(report.jeonse_price_만원)}**"
        if report.jeonse_prev_price_만원 is not None:
            diff = report.jeonse_price_만원 - report.jeonse_prev_price_만원
            sign = "+" if diff >= 0 else ""
            value += f"\n전월: {format_price(report.jeonse_prev_price_만원)}"
            value += f"\n변동: {arrow} {sign}{pct:.1f}% ({sign}{format_price(abs(diff))})" if pct is not None else ""
        fields.append({"name": "전세 시세", "value": value, "inline": True})

    # 최근 실거래 (국토부)
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

    # 데이터 없는 경우
    if not fields:
        fields.append({
            "name": "알림",
            "value": "수집된 시세 데이터가 없습니다.",
            "inline": False,
        })

    sources = []
    if report.recent_transactions:
        sources.append("국토교통부 실거래가")
    if report.naver_price_만원 is not None:
        sources.append("네이버 부동산")

    return {
        "title": f"🏠 {report.prop.name}",
        "color": _embed_color(report),
        "fields": fields,
        "footer": {
            "text": f"출처: {' / '.join(sources) or '없음'}  |  {now}"
        },
    }


def send_report(reports: list[PriceReport]) -> None:
    """Discord 웹훅으로 리포트를 전송한다."""
    if not DISCORD_WEBHOOK_URL:
        log.error("DISCORD_WEBHOOK_URL이 설정되지 않았습니다")
        return

    embeds = [build_embed(r) for r in reports]

    # Discord 웹훅은 한 번에 최대 10개 임베드
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
