"""Draft generator: one personalised, evidence-backed email for human review (never sent)."""
from pydantic import BaseModel, Field

from app.drafting.prompts import DRAFT_SYSTEM, DRAFT_USER, TONES
from app.llm import groq_client  # call via module so tests can swap it
from app.models import ClaimRef, Draft, Evidence, ProspectInput
from app.utils.text import body_without_signoff, word_count

MIN_WORDS, MAX_WORDS = 70, 110


class DraftOutput(BaseModel):
    subject: str = Field(max_length=120)
    body: str = Field(max_length=2500)
    claims_used: list[ClaimRef] = Field(default_factory=list)


def build_prompts(p: ProspectInput, hook: Evidence, supporting: list[Evidence], *, tone: str,
                  feedback: list[str] | None = None, instructions: str | None = None) -> tuple[str, str]:
    sup = "".join(f"\nSUPPORTING evidence_id={e.id}: {e.claim} (source: {e.source_domain})" for e in supporting[:1])
    user = DRAFT_USER.format(
        name=p.name, title=p.title, company=p.company, seller=p.seller.as_text(),
        hook_id=hook.id, hook_claim=hook.claim, hook_quote=hook.quote[:300], hook_source=hook.source_domain,
        hook_date=hook.event_date or hook.publication_date or "date unknown",
        supporting=("Optional supporting evidence (use at most one):" + sup + "\n") if sup else "",
        instructions=(f"\nREVIEWER INSTRUCTIONS (follow unless they conflict with the hard rules): {instructions}\n"
                      if instructions else ""),
        feedback=("\nFIX THESE ISSUES FROM THE QUALITY CHECK:\n- " + "\n- ".join(feedback) + "\n") if feedback else "",
    )
    system = DRAFT_SYSTEM.format(min_words=MIN_WORDS, max_words=MAX_WORDS, first_name=p.name.split()[0],
                                 tone=TONES.get(tone, TONES["professional"]))
    return system, user


def generate_draft(p: ProspectInput, hook: Evidence, supporting: list[Evidence], *, tone: str = "professional",
                   version: int = 1, feedback: list[str] | None = None,
                   instructions: str | None = None) -> tuple[Draft, dict]:
    system, user = build_prompts(p, hook, supporting, tone=tone, feedback=feedback, instructions=instructions)
    out, usage = groq_client.chat_json_patient(DraftOutput, system=system, user=user, temperature=0.6, max_tokens=1500)
    draft = Draft(
        subject=out.subject.strip(), body=out.body.strip(), hook_evidence_id=hook.id,
        supporting_evidence_ids=[e.id for e in supporting[:1]], claims_used=out.claims_used,
        word_count=word_count(body_without_signoff(out.body)), version=version, tone=tone,
    )
    return draft, usage.as_dict()
