"""All data contracts. Graph state stores model_dump(mode='json') of these; nodes re-validate on read."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

Tone = Literal["professional", "friendly", "direct"]
Branch = Literal["identity", "person", "company", "hiring", "broadened", "targeted"]
ClaimType = Literal[
    "person_role", "employer", "leadership_statement", "funding", "product_launch", "partnership", "expansion",
    "hiring", "acquisition", "financial_results", "customer_win", "layoffs", "legal", "security_incident", "other",
]
VerificationStatus = Literal["verified", "uncertain", "disputed", "rejected"]
Credibility = Literal["high", "medium", "low"]


# ---------------------------------------------------------------- input
class SellerContext(BaseModel):
    product: str = Field(min_length=2, max_length=200)
    value_proposition: str = Field(min_length=10, max_length=1000)
    target_audience: str | None = Field(None, max_length=300)
    pain_points: str | None = Field(None, max_length=600)

    def as_text(self) -> str:
        parts = [f"Product: {self.product}", f"Value proposition: {self.value_proposition}"]
        if self.target_audience:
            parts.append(f"Target audience: {self.target_audience}")
        if self.pain_points:
            parts.append(f"Pain points solved: {self.pain_points}")
        return "\n".join(parts)


class ProspectInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    company: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=2, max_length=120)
    profile_url: HttpUrl | None = None
    seller: SellerContext
    tone: Tone = "professional"

    @field_validator("name", "company", "title")
    @classmethod
    def _squash(cls, v: str) -> str:
        return " ".join(v.split())


# ---------------------------------------------------------------- research
class ResearchRecord(BaseModel):
    id: str
    branch: Branch
    query: str
    title: str
    url: str
    domain: str
    content: str
    published_date: str | None = None
    tavily_score: float | None = None
    injection_flagged: bool = False


# ---------------------------------------------------------------- identity (Phase 9A)
class IdentityCandidate(BaseModel):
    id: str
    name: str
    title: str | None = None
    company: str | None = None
    source_url: str
    snippet: str = ""
    matches_company: bool = False
    matches_title: bool = False


class IdentityResolution(BaseModel):
    status: Literal["confirmed", "ambiguous", "unconfirmed"]
    candidates: list[IdentityCandidate] = Field(default_factory=list)
    selected_id: str | None = None
    explanation: str


class IdentityChoice(BaseModel):
    candidate_id: str | None = None
    company_only: bool = False
    abort: bool = False

    @model_validator(mode="after")
    def _exactly_one(self):
        if sum([bool(self.candidate_id), self.company_only, self.abort]) != 1:
            raise ValueError("Choose exactly one: candidate_id, company_only or abort")
        return self


# ---------------------------------------------------------------- evidence (Phase 4)
class Evidence(BaseModel):
    id: str
    claim: str
    claim_type: ClaimType
    subject: Literal["person", "company"]
    key: str
    value: str | None = None
    quote: str
    source_url: str
    source_title: str
    source_domain: str
    publication_date: str | None = None
    event_date: str | None = None
    association: Literal["prospect", "company", "unclear", "unrelated"]
    base_status: VerificationStatus
    verification_status: VerificationStatus
    credibility: Credibility
    credibility_reason: str
    corroborating_urls: list[str] = Field(default_factory=list)
    is_sensitive: bool = False
    sensitive_category: str | None = None
    notes: list[str] = Field(default_factory=list)


class Conflict(BaseModel):
    id: str
    claim_type: ClaimType
    key: str
    values: list[str]
    evidence_ids: list[str]
    status: Literal["unresolved", "resolved", "excluded", "user_resolved"] = "unresolved"
    note: str = ""


class ConflictDecision(BaseModel):
    resolutions: dict[str, str] = Field(default_factory=dict)  # conflict_id -> winning evidence_id | "exclude"
    abort: bool = False


# ---------------------------------------------------------------- ranking (Phase 5)
class DimensionScores(BaseModel):
    business_relevance: float = Field(ge=0, le=10)
    specificity: float = Field(ge=0, le=10)
    credibility: float = Field(ge=0, le=10)
    recency: float = Field(ge=0, le=10)
    outreach_usefulness: float = Field(ge=0, le=10)


class RankedSignal(BaseModel):
    evidence_id: str
    claim: str
    source_url: str
    source_title: str
    publication_date: str | None = None
    scores: DimensionScores
    total: float
    explanation: str
    is_sensitive: bool = False
    sensitive_category: str | None = None
    eligible_for_hook: bool
    ineligible_reason: str | None = None


# ---------------------------------------------------------------- drafting & quality (Phases 6-7)
class ClaimRef(BaseModel):
    text: str
    evidence_id: str


class Draft(BaseModel):
    subject: str
    body: str
    hook_evidence_id: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    claims_used: list[ClaimRef] = Field(default_factory=list)
    word_count: int
    version: int = 1
    tone: Tone = "professional"
    edited_by_human: bool = False


class QualityIssue(BaseModel):
    check: str
    severity: Literal["fail", "warn"]
    message: str


class QualityReport(BaseModel):
    passed: bool
    needs_human: bool = False
    issues: list[QualityIssue] = Field(default_factory=list)
    checks: dict[str, bool] = Field(default_factory=dict)
    revision_feedback: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- human decisions (Phases 9-10)
class ContextDecision(BaseModel):
    action: Literal["add_context", "abstain"]
    context: str | None = Field(None, max_length=500)


class ReviewDecision(BaseModel):
    action: Literal["approve", "reject", "edit", "choose_signal", "regenerate"]
    subject: str | None = Field(None, max_length=150)
    body: str | None = Field(None, max_length=3000)
    evidence_id: str | None = None
    instructions: str | None = Field(None, max_length=500)
    tone: Tone | None = None
    reason: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def _requirements(self):
        if self.action == "edit" and not (self.subject or self.body):
            raise ValueError("edit requires subject and/or body")
        if self.action == "choose_signal" and not self.evidence_id:
            raise ValueError("choose_signal requires evidence_id")
        return self
