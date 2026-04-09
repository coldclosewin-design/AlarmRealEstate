from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Region:
    name: str           # 표시 이름 (예: "성남시 중원구")
    region_code: str    # 법정동코드 5자리
    apt_filter: list[str] = field(default_factory=list)  # 빈 리스트면 전체


@dataclass
class Transaction:
    apt_name: str
    price_만원: int
    date: str           # YYYY-MM-DD
    floor: str = ""
    area_m2: float = 0.0
    deal_type: str = "매매"


@dataclass
class RegionReport:
    region: Region
    transactions: list[Transaction] = field(default_factory=list)
