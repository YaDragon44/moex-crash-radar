from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

from .futures_data import fetch_futures_history
from .moex import Candle

MONTH_CODES = {3: "H", 6: "M", 9: "U", 12: "Z"}


@dataclass(frozen=True)
class RollContract:
    family: str
    secid: str
    year: int
    month: int
    expiry: str
    roll_date: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RollBar:
    candle: Candle
    secid: str
    family: str
    expiry: str


@dataclass(frozen=True)
class RollChainResult:
    family: str
    bars: tuple[RollBar, ...]
    contracts: tuple[RollContract, ...]
    missing_contracts: tuple[str, ...]
    duplicate_timestamps: int

    @property
    def candles(self) -> list[Candle]:
        return [row.candle for row in self.bars]

    def diagnostics(self) -> dict:
        secids = sorted({row.secid for row in self.bars})
        return {
            "family": self.family,
            "bars": len(self.bars),
            "contracts_used": secids,
            "contracts_planned": [c.secid for c in self.contracts],
            "missing_contracts": list(self.missing_contracts),
            "duplicate_timestamps": self.duplicate_timestamps,
            "first_bar": self.bars[0].candle.begin if self.bars else None,
            "last_bar": self.bars[-1].candle.begin if self.bars else None,
        }


def _third_thursday(year: int, month: int) -> date:
    d = date(year, month, 1)
    while d.weekday() != 3:
        d += timedelta(days=1)
    return d + timedelta(days=14)


def _subtract_weekdays(value: date, n: int) -> date:
    d = value
    remaining = max(n, 0)
    while remaining:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            remaining -= 1
    return d


def quarterly_contracts(
    family: str,
    *,
    start: str,
    end: str,
    secid_prefix: str | None = None,
    roll_business_days: int = 5,
) -> list[RollContract]:
    """Generate deterministic quarterly MOEX contract identifiers.

    The identifier convention is <prefix><H/M/U/Z><last-year-digit>. The
    function only describes the intended chain; availability is verified by
    actual candle retrieval and missing contracts are reported explicitly.
    """
    start_d, end_d = date.fromisoformat(start), date.fromisoformat(end)
    prefix = secid_prefix or family
    contracts: list[RollContract] = []
    for year in range(start_d.year - 1, end_d.year + 2):
        for month, code in MONTH_CODES.items():
            expiry = _third_thursday(year, month)
            roll = _subtract_weekdays(expiry, roll_business_days)
            # Keep enough neighboring contracts to cover the initial and final roll.
            if expiry < start_d - timedelta(days=120) or roll > end_d + timedelta(days=120):
                continue
            contracts.append(RollContract(
                family=family.upper(),
                secid=f"{prefix}{code}{str(year)[-1]}",
                year=year,
                month=month,
                expiry=expiry.isoformat(),
                roll_date=roll.isoformat(),
            ))
    return sorted(contracts, key=lambda c: (c.year, c.month))


def active_contract_for_day(day: date, contracts: Iterable[RollContract]) -> RollContract | None:
    ordered = sorted(contracts, key=lambda c: c.roll_date)
    for contract in ordered:
        if day <= date.fromisoformat(contract.roll_date):
            return contract
    return ordered[-1] if ordered else None


def build_roll_chain(
    family: str,
    *,
    start: str,
    end: str,
    secid_prefix: str | None = None,
    roll_business_days: int = 5,
    interval: int = 60,
    fetcher=fetch_futures_history,
) -> RollChainResult:
    contracts = quarterly_contracts(
        family, start=start, end=end, secid_prefix=secid_prefix,
        roll_business_days=roll_business_days,
    )
    start_d, end_d = date.fromisoformat(start), date.fromisoformat(end)
    raw: dict[str, dict[str, Candle]] = {}
    missing: list[str] = []

    for contract in contracts:
        expiry = date.fromisoformat(contract.expiry)
        # Contracts are intentionally fetched only around their relevant quarter.
        fetch_start = max(start_d, expiry - timedelta(days=130))
        fetch_end = min(end_d, expiry + timedelta(days=7))
        if fetch_start > fetch_end:
            continue
        candles = fetcher(
            contract.secid,
            start=fetch_start.isoformat(),
            end=fetch_end.isoformat(),
            interval=interval,
        )
        if not candles:
            missing.append(contract.secid)
            continue
        raw[contract.secid] = {c.begin: c for c in candles}

    all_times = sorted({ts for rows in raw.values() for ts in rows})
    bars: list[RollBar] = []
    duplicates = 0
    for ts in all_times:
        dt = datetime.fromisoformat(ts)
        if dt.date() < start_d or dt.date() > end_d:
            continue
        active = active_contract_for_day(dt.date(), contracts)
        if active is None:
            continue
        candle = raw.get(active.secid, {}).get(ts)
        if candle is None:
            # Fail closed: never backfill a missing active-contract bar with a
            # different maturity, which would create hidden roll contamination.
            continue
        if bars and bars[-1].candle.begin == ts:
            duplicates += 1
            continue
        bars.append(RollBar(candle=candle, secid=active.secid, family=family.upper(), expiry=active.expiry))

    return RollChainResult(
        family=family.upper(), bars=tuple(bars), contracts=tuple(contracts),
        missing_contracts=tuple(sorted(set(missing))), duplicate_timestamps=duplicates,
    )
