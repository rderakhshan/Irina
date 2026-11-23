"""Independent financial calculation oracles."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from ..metrics.calculators import numeric_correct
from ..worlds.factory import Company


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def leverage(company: Company, extra_debt: Decimal = Decimal("0")) -> Decimal:
    if company.equity == 0:
        raise ValueError("equity must be non-zero")
    return _q((company.total_debt + extra_debt) / company.equity)


def net_margin(company: Company) -> Decimal:
    if company.revenue == 0:
        raise ValueError("revenue must be non-zero")
    return _q(company.net_income / company.revenue)


def assets_identity_residual(company: Company) -> Decimal:
    return _q(company.assets - company.liabilities - company.equity)


def cash_to_debt(company: Company) -> Decimal:
    if company.total_debt == 0:
        raise ValueError("debt must be non-zero")
    return _q(company.cash / company.total_debt)


@dataclass(frozen=True, slots=True)
class NumericCase:
    case_id: str
    metric: str
    company_ticker: str
    extra_debt: Decimal = Decimal("0")
    expected: Decimal = Decimal("0")
    tolerance: Decimal = Decimal("0.0001")


def check_numeric(case: NumericCase, company: Company, predicted: Decimal) -> bool:
    return numeric_correct(
        predicted,
        case.expected,
        atol=case.tolerance,
        rtol=Decimal("0"),
    )


__all__ = [
    "NumericCase",
    "assets_identity_residual",
    "cash_to_debt",
    "check_numeric",
    "leverage",
    "net_margin",
]
