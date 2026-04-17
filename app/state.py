"""이전 전송 상태 관리 — 새 거래만 감지하기 위한 모듈."""

import json
import logging
from pathlib import Path

from app.config import PROJECT_ROOT
from app.models import Transaction

log = logging.getLogger(__name__)

STATE_PATH = PROJECT_ROOT / "data" / "sent_transactions.json"


def _tx_key(tx: Transaction) -> str:
    """거래를 고유하게 식별하는 키."""
    return f"{tx.apt_name}|{tx.date}|{tx.floor}|{tx.area_m2:.0f}|{tx.price_만원}"


def load_seen_keys() -> set[str]:
    """이전에 전송한 거래 키 목록을 로드한다."""
    if not STATE_PATH.exists():
        return set()
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, TypeError):
        log.warning("상태 파일 파싱 실패, 초기화합니다")
        return set()


def save_seen_keys(keys: set[str]) -> None:
    """전송한 거래 키 목록을 저장한다."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(keys), f, ensure_ascii=False)
    log.info("상태 저장 완료: %d건", len(keys))


def filter_new_transactions(
    transactions: list[Transaction],
    seen: set[str],
) -> list[Transaction]:
    """이미 전송한 거래를 제외하고 새 거래만 반환한다."""
    return [tx for tx in transactions if _tx_key(tx) not in seen]


def mark_as_seen(
    transactions: list[Transaction],
    seen: set[str],
) -> set[str]:
    """거래 목록을 seen에 추가한 새 set을 반환한다."""
    return seen | {_tx_key(tx) for tx in transactions}
