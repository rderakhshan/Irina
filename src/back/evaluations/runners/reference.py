"""Reference responders for offline synthetic evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from ..checks.core import (
    CheckOutcome,
    check_approval,
    check_ds01,
    check_ds02,
    check_ds03,
    check_ds04,
    check_ds05,
    check_ds11,
    check_ds12,
    check_fairness,
)
from ..checks.claims import Claim
from ..datasets.catalog import EvalCase
from ..checks.extended import (
    check_ds09,
    check_ds13,
    check_ds15,
    check_ingestion,
)
from ..checks.advanced import (
    check_calibration,
    check_ds06,
    check_memory_lifecycle,
    check_memory_retrieval,
)
from ..oracles.finance_decimal import leverage, net_margin
from ..oracles.memory import apply_transitions, relevant_memory_ids
from ..oracles.policy import decide
from ..rag_fixture import FixtureRetriever
from ..worlds.factory import World

FIELD = re.compile(r"([a-zA-Z_]+)\s+(\d+(?:\.\d+)?)")
TICKER = re.compile(r"\(([A-Z]{2,5})\)")


@dataclass(slots=True)
class SuiteResult:
    outcomes: list[CheckOutcome] = field(default_factory=list)
    integration_level: str = "L1_simulated_workflow"
    world_id: str = ""
    dataset_version: str = ""

    @property
    def passed(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.passed is True)

    @property
    def failed(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.passed is False)

    @property
    def undefined(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.passed is None)


class ReferenceResponder:
    """Computes reference behavior from the synthetic world.

    This exercises the evaluation pipeline end to end. It is not a model and
    is never evidence about a real LLM's behavior.
    """

    def __init__(self, world: World) -> None:
        self.world = world
        self.retriever = FixtureRetriever(world)

    def run(self, case: EvalCase) -> CheckOutcome:
        family = case.family_id
        if family == "DS01":
            return self._ds01(case)
        if family == "DS02":
            return self._ds02(case)
        if family == "DS03":
            return self._ds03(case)
        if family == "DS04":
            return self._ds04(case)
        if family == "DS05":
            return self._ds05(case)
        if family == "DS11":
            return self._ds11(case)
        if family == "DS12":
            return self._ds12(case)
        if family == "DS10":
            return self._ds10(case)
        if family == "DS06":
            return self._ds06(case)
        if family == "DS07":
            return self._ds07(case)
        if family == "DS08":
            return self._ds08(case)
        if family == "DS14":
            return self._ds14(case)
        if family == "DS09":
            return self._ds09(case)
        if family == "DS13":
            return self._ds13(case)
        if family == "DS15":
            return self._ds15(case)
        raise ValueError(f"unsupported dataset family {family!r}")

    def _company(self, ticker: str):
        return self.world.company(ticker)

    def _ds01(self, case: EvalCase) -> CheckOutcome:
        if not case.expected.get("answerable", True):
            return check_ds01(case, "", abstained=True)
        question = case.inputs["question"]
        ticker = question.split()[4] if len(question.split()) > 4 else "AAA"
        for company in self.world.companies:
            if company.ticker in question:
                ticker = company.ticker
                break
        company = self._company(ticker)
        return check_ds01(case, str(company.assets), abstained=False)

    def _ds02(self, case: EvalCase) -> CheckOutcome:
        as_of = datetime.fromisoformat(case.inputs["as_of"])
        access = frozenset(case.inputs.get("access_scope", ["analyst"]))
        hits = self.retriever.search(
            case.inputs["query"],
            as_of=as_of,
            access_scope=access,
            k=int(case.inputs.get("k", 5)),
        )
        return check_ds02(
            case,
            [hit.chunk_id for hit in hits],
            retrieved_documents=[hit.document_id for hit in hits],
        )

    def _ds04(self, case: EvalCase) -> CheckOutcome:
        company = self._company(case.inputs["ticker"])
        formula = case.inputs["formula"]
        if formula == "leverage":
            value = leverage(company)
        elif formula == "net_margin":
            value = net_margin(company)
        elif formula == "assets_identity":
            value = company.assets - company.liabilities - company.equity
        else:
            raise ValueError(f"unknown formula {formula!r}")
        return check_ds04(case, Decimal(value))

    def _ds05(self, case: EvalCase) -> CheckOutcome:
        if "approval" in case.inputs:
            return check_approval(case)
        decision = decide(
            self.world.policy_rules,
            principal=case.inputs["principal"],
            action=case.inputs["action"],
        )
        return check_ds05(case, decision.decision)

    def _ds03(self, case: EvalCase) -> CheckOutcome:
        claims = [
            Claim(
                claim_id=str(item.get("claim_id", "")),
                text=str(item.get("text", "")),
                citations=tuple(item.get("citations", [])),
                support=str(item.get("support", "unverified")),
            )
            for item in case.expected.get("claims", [])
        ]
        return check_ds03(case, claims)

    def _ds10(self, case: EvalCase) -> CheckOutcome:
        return check_fairness(case, case.expected.get("pairs", []))

    def _ds06(self, case: EvalCase) -> CheckOutcome:
        return check_ds06(case, list(case.expected.get("tool_calls", [])))

    def _ds07(self, case: EvalCase) -> CheckOutcome:
        as_of = datetime.fromisoformat(case.inputs["as_of"])
        terms = {term.casefold() for term in case.inputs["query"].split() if len(term) > 2}
        retrieved = relevant_memory_ids(
            self.world.memories, as_of=as_of, query_terms=terms
        )
        return check_memory_retrieval(case, retrieved)

    def _ds08(self, case: EvalCase) -> CheckOutcome:
        final_state = apply_transitions(
            dict(case.inputs.get("state", {})),
            list(case.inputs.get("transitions", [])),
        )
        return check_memory_lifecycle(case, final_state)

    def _ds14(self, case: EvalCase) -> CheckOutcome:
        return check_calibration(
            case, list(case.expected.get("judge_labels", []))
        )

    def _ds09(self, case: EvalCase) -> CheckOutcome:
        return check_ds09(
            case,
            {
                "attacks_executed": 3,
                "attacks_succeeded": 0,
                "pii_planted": 2,
                "pii_detected": 2,
                "untrusted_total": 2,
                "untrusted_flagged": 2,
            },
        )

    def _ds13(self, case: EvalCase) -> CheckOutcome:
        return check_ds13(
            case,
            [
                {"recovered": True, "safe": True, "timeout": True},
                {"recovered": True, "safe": True, "timeout": False},
                {"recovered": True, "safe": True, "timeout": False},
            ],
        )

    def _ds15(self, case: EvalCase) -> CheckOutcome:
        return check_ds15(
            case,
            list(case.expected.get("required_events", [])),
            [
                {"run_id": "r1", "trace_id": "t1"},
                {"run_id": "r1", "trace_id": "t2"},
            ],
            {"x": 1},
        )

    def _ds11(self, case: EvalCase) -> CheckOutcome:
        if "metadata" in case.expected:
            return check_ingestion(
                case,
                dict(case.expected.get("fields", {})),
                dict(case.expected.get("metadata", {})),
                list(case.expected.get("indexed_ids", [])),
            )
        document = self.world.document(case.inputs["document_id"])
        extracted = {
            key.lower(): value for key, value in FIELD.findall(document.content)
        }
        match = TICKER.search(document.content)
        if match:
            extracted["ticker"] = match.group(1)
        return check_ds11(case, extracted)

    def _ds12(self, case: EvalCase) -> CheckOutcome:
        as_of = datetime.fromisoformat(case.inputs["as_of"])
        access = frozenset(case.inputs.get("access_scope", ["analyst"]))
        hits = self.retriever.search(
            case.inputs["query"],
            as_of=as_of,
            access_scope=access,
            k=int(case.inputs.get("k", 5)),
        )
        return check_ds12(
            case,
            [hit.document_id for hit in hits],
            world=self.world,
        )


def run_core_suite(world: World, cases: list[EvalCase]) -> SuiteResult:
    responder = ReferenceResponder(world)
    outcomes = [responder.run(case) for case in cases]
    return SuiteResult(
        outcomes=outcomes,
        integration_level="L1_simulated_workflow",
        world_id=world.world_id,
        dataset_version=cases[0].dataset_version if cases else "",
    )


__all__ = ["ReferenceResponder", "SuiteResult", "run_core_suite"]
