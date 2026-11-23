"""Deterministic synthetic world for finance and RAG evaluation."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from ..metrics.calculators import sha256_hex


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class Company:
    company_id: str
    ticker: str
    name: str
    fiscal_year: int
    currency: str
    assets: Decimal
    liabilities: Decimal
    equity: Decimal
    revenue: Decimal
    net_income: Decimal
    total_debt: Decimal
    cash: Decimal

    def as_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "ticker": self.ticker,
            "name": self.name,
            "fiscal_year": self.fiscal_year,
            "currency": self.currency,
            "assets": str(self.assets),
            "liabilities": str(self.liabilities),
            "equity": str(self.equity),
            "revenue": str(self.revenue),
            "net_income": str(self.net_income),
            "total_debt": str(self.total_debt),
            "cash": str(self.cash),
        }


@dataclass(frozen=True, slots=True)
class Document:
    document_id: str
    company_id: str
    kind: str
    title: str
    content: str
    published_at: datetime
    available_at: datetime
    effective_at: datetime
    ingested_at: datetime
    classification: str = "internal"
    superseded_at: datetime | None = None
    source_hash: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "company_id": self.company_id,
            "kind": self.kind,
            "title": self.title,
            "content": self.content,
            "published_at": self.published_at.isoformat(),
            "available_at": self.available_at.isoformat(),
            "effective_at": self.effective_at.isoformat(),
            "ingested_at": self.ingested_at.isoformat(),
            "classification": self.classification,
            "superseded_at": (
                self.superseded_at.isoformat() if self.superseded_at else None
            ),
            "source_hash": self.source_hash,
        }


@dataclass(frozen=True, slots=True)
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    page: int
    relevance: float = 0.0
    acl: tuple[str, ...] = ("analyst",)

    def as_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "page": self.page,
            "relevance": self.relevance,
            "acl": list(self.acl),
        }


@dataclass(frozen=True, slots=True)
class MemoryItem:
    memory_id: str
    text: str
    valid_from: datetime
    valid_to: datetime | None = None
    source_document_id: str = ""


@dataclass(frozen=True, slots=True)
class PolicyRule:
    principal: str
    action: str
    decision: str
    reason: str
    requires_approval: bool = False


@dataclass(frozen=True, slots=True)
class World:
    world_id: str
    seed: int
    as_of: datetime
    companies: tuple[Company, ...]
    documents: tuple[Document, ...]
    chunks: tuple[Chunk, ...]
    memories: tuple[MemoryItem, ...]
    policy_rules: tuple[PolicyRule, ...]
    manifest: dict[str, Any] = field(default_factory=dict)

    def company(self, ticker: str) -> Company:
        for company in self.companies:
            if company.ticker == ticker:
                return company
        raise KeyError(ticker)

    def document(self, document_id: str) -> Document:
        for document in self.documents:
            if document.document_id == document_id:
                return document
        raise KeyError(document_id)

    def visible_documents(
        self,
        as_of: datetime,
        *,
        access_scope: frozenset[str] = frozenset({"analyst"}),
    ) -> tuple[Document, ...]:
        visible = []
        for document in self.documents:
            if document.available_at > as_of:
                continue
            if document.superseded_at is not None and document.superseded_at <= as_of:
                continue
            if document.classification not in {"internal", *access_scope}:
                continue
            visible.append(document)
        return tuple(visible)

    def visible_chunks(
        self,
        as_of: datetime,
        *,
        access_scope: frozenset[str] = frozenset({"analyst"}),
    ) -> tuple[Chunk, ...]:
        allowed_docs = {doc.document_id for doc in self.visible_documents(as_of, access_scope=access_scope)}
        return tuple(
            chunk
            for chunk in self.chunks
            if chunk.document_id in allowed_docs
            and set(chunk.acl).issubset(access_scope)
        )


class WorldFactory:
    """Build a reproducible fictional finance world from a seed."""

    def build(
        self,
        seed: int,
        *,
        world_id: str = "world-001",
        as_of: datetime | None = None,
    ) -> World:
        rng = random.Random(seed)
        decision_time = as_of or _utc(2024, 12, 31)
        companies = (
            self._company(rng, "AAA", "Aurora Analytics", 2024, decision_time),
            self._company(rng, "BBB", "Borealis Systems", 2024, decision_time),
        )
        documents = self._documents(companies, decision_time)
        chunks = self._chunks(documents)
        memories = self._memories(companies, documents)
        rules = (
            PolicyRule("analyst", "read_filing", "allow", "read-only research"),
            PolicyRule("analyst", "export_confidential", "reject", "classification block"),
            PolicyRule("analyst", "submit_order", "reject", "trading is out of scope"),
            PolicyRule("analyst", "send_client_memo", "escalate", "requires approval", True),
            PolicyRule("portfolio_manager", "send_client_memo", "allow", "authorized role"),
        )
        world = World(
            world_id=world_id,
            seed=seed,
            as_of=decision_time,
            companies=companies,
            documents=documents,
            chunks=chunks,
            memories=memories,
            policy_rules=rules,
        )
        manifest = {
            "world_id": world_id,
            "seed": seed,
            "as_of": decision_time.isoformat(),
            "companies_hash": sha256_hex([c.as_dict() for c in companies]),
            "documents_hash": sha256_hex([d.as_dict() for d in documents]),
            "chunks_hash": sha256_hex([c.as_dict() for c in chunks]),
            "memories_hash": sha256_hex([asdict(m) for m in memories]),
            "policy_hash": sha256_hex([asdict(r) for r in rules]),
        }
        manifest["world_hash"] = sha256_hex(
            {key: value for key, value in manifest.items() if key != "world_hash"}
        )
        return World(
            world_id=world.world_id,
            seed=world.seed,
            as_of=world.as_of,
            companies=world.companies,
            documents=world.documents,
            chunks=world.chunks,
            memories=world.memories,
            policy_rules=world.policy_rules,
            manifest=manifest,
        )

    @staticmethod
    def _company(
        rng: random.Random,
        ticker: str,
        name: str,
        fiscal_year: int,
        as_of: datetime,
    ) -> Company:
        assets = Decimal(rng.randrange(800_000, 1_200_000))
        liabilities = Decimal(rng.randrange(300_000, 600_000))
        equity = assets - liabilities
        revenue = Decimal(rng.randrange(500_000, 900_000))
        net_income = Decimal(rng.randrange(40_000, 120_000))
        total_debt = liabilities - Decimal(rng.randrange(50_000, 100_000))
        cash = Decimal(rng.randrange(80_000, 200_000))
        return Company(
            company_id=f"co-{ticker.lower()}",
            ticker=ticker,
            name=name,
            fiscal_year=fiscal_year,
            currency="USD",
            assets=assets,
            liabilities=liabilities,
            equity=equity,
            revenue=revenue,
            net_income=net_income,
            total_debt=total_debt,
            cash=cash,
        )

    @staticmethod
    def _documents(
        companies: tuple[Company, ...],
        as_of: datetime,
    ) -> tuple[Document, ...]:
        documents: list[Document] = []
        for company in companies:
            base_text = (
                f"{company.name} ({company.ticker}) fiscal year {company.fiscal_year}. "
                f"Total assets {company.assets} {company.currency}; liabilities "
                f"{company.liabilities}; equity {company.equity}; revenue "
                f"{company.revenue}; net income {company.net_income}; total debt "
                f"{company.total_debt}; cash {company.cash}. "
                f"Leverage ratio is total debt divided by equity."
            )
            documents.append(
                Document(
                    document_id=f"{company.ticker}-10K-2024",
                    company_id=company.company_id,
                    kind="annual_report",
                    title=f"{company.name} 2024 Annual Report",
                    content=base_text,
                    published_at=_utc(2024, 11, 15),
                    available_at=_utc(2024, 11, 15),
                    effective_at=_utc(2024, 11, 15),
                    ingested_at=_utc(2024, 11, 16),
                    source_hash=sha256_hex(base_text),
                )
            )
            amendment_text = (
                f"{company.name} amendment: a subsequent debt issuance increased "
                f"total debt by 50000 {company.currency}. Updated leverage must use "
                f"the amended debt figure."
            )
            documents.append(
                Document(
                    document_id=f"{company.ticker}-10K-A-2025",
                    company_id=company.company_id,
                    kind="amendment",
                    title=f"{company.name} debt amendment",
                    content=amendment_text,
                    published_at=_utc(2025, 1, 10),
                    available_at=_utc(2025, 1, 12),
                    effective_at=_utc(2025, 1, 10),
                    ingested_at=_utc(2025, 1, 13),
                    source_hash=sha256_hex(amendment_text),
                )
            )
            future_text = (
                f"{company.name} preliminary 2025 results are not yet public. "
                f"Future-only content used to test lookahead exclusion."
            )
            documents.append(
                Document(
                    document_id=f"{company.ticker}-PRELIM-2025",
                    company_id=company.company_id,
                    kind="future_filing",
                    title=f"{company.name} preliminary 2025 results",
                    content=future_text,
                    published_at=_utc(2025, 2, 20),
                    available_at=_utc(2025, 2, 20),
                    effective_at=_utc(2025, 2, 20),
                    ingested_at=_utc(2025, 2, 21),
                    source_hash=sha256_hex(future_text),
                )
            )
            confidential_text = (
                f"{company.name} confidential internal credit review. "
                f"Restricted to credit committee."
            )
            documents.append(
                Document(
                    document_id=f"{company.ticker}-CREDIT-INTERNAL",
                    company_id=company.company_id,
                    kind="internal_memo",
                    title=f"{company.name} credit review",
                    content=confidential_text,
                    published_at=_utc(2024, 12, 1),
                    available_at=_utc(2024, 12, 1),
                    effective_at=_utc(2024, 12, 1),
                    ingested_at=_utc(2024, 12, 2),
                    classification="credit_committee",
                    source_hash=sha256_hex(confidential_text),
                )
            )
        return tuple(documents)

    @staticmethod
    def _chunks(documents: tuple[Document, ...]) -> tuple[Chunk, ...]:
        chunks: list[Chunk] = []
        for document in documents:
            sentences = [part.strip() for part in document.content.split(".") if part.strip()]
            for index, sentence in enumerate(sentences):
                chunks.append(
                    Chunk(
                        chunk_id=f"{document.document_id}#p{index + 1}",
                        document_id=document.document_id,
                        text=sentence + ".",
                        page=index + 1,
                        relevance=1.0 if index == 0 else 0.5,
                        acl=(document.classification,)
                        if document.classification != "internal"
                        else ("analyst",),
                    )
                )
        return tuple(chunks)

    @staticmethod
    def _memories(
        companies: tuple[Company, ...],
        documents: tuple[Document, ...],
    ) -> tuple[MemoryItem, ...]:
        items: list[MemoryItem] = []
        for company in companies:
            items.append(
                MemoryItem(
                    memory_id=f"mem-{company.ticker}-debt",
                    text=f"{company.ticker} total debt was {company.total_debt} before the 2025 amendment.",
                    valid_from=_utc(2024, 11, 15),
                    valid_to=_utc(2025, 1, 12),
                    source_document_id=f"{company.ticker}-10K-2024",
                )
            )
            items.append(
                MemoryItem(
                    memory_id=f"mem-{company.ticker}-debt-amended",
                    text=f"{company.ticker} total debt increased by 50000 after the 2025 amendment.",
                    valid_from=_utc(2025, 1, 12),
                    source_document_id=f"{company.ticker}-10K-A-2025",
                )
            )
        return tuple(items)


__all__ = [
    "Chunk",
    "Company",
    "Document",
    "MemoryItem",
    "PolicyRule",
    "World",
    "WorldFactory",
]
