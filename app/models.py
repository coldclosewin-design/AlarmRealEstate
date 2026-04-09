from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Property:
    name: str
    region_code: str  # 법정동코드 5자리
    complex_name: str
    area_m2: float
    naver_complex_id: str = ""


@dataclass
class Transaction:
    property_name: str
    price_만원: int
    date: str  # YYYY-MM-DD
    floor: str = ""
    area_m2: float = 0.0
    source: str = ""  # "molit" | "naver"
    deal_type: str = "매매"


@dataclass
class PriceReport:
    prop: Property
    naver_price_만원: int | None = None
    naver_prev_price_만원: int | None = None
    jeonse_price_만원: int | None = None
    jeonse_prev_price_만원: int | None = None
    recent_transactions: list[Transaction] = field(default_factory=list)
