"""Rule-based, deterministic compliance/script-adherence checks (analytics
doc section 14) — keyword/phrase matching over transcript text, no LLM call,
no added inference cost, no new precision risk. Same "objective,
transcript-derived, zero marginal cost" pattern as app/insights.py.

The rule set below is an illustrative example for the PRD's real-estate
brokerage ICP (PRD section 3), not a compliance guarantee. A real deployment
would let each org supply its own required/prohibited phrases, per doc
section 14: "Create configurable rules based on the company's sales
process." The recording-disclosure rule specifically exists because PRD
section 10 calls out UAE PDPL consent as a product requirement, not a legal
footnote — this is the automated-disclosure-support check that risk implies.
"""

from dataclasses import dataclass

from app.schemas import ComplianceCheck, ComplianceCheckResult, ComplianceReport, Speaker, TranscriptSegment


@dataclass(frozen=True)
class _Rule:
    name: str
    keywords: tuple[str, ...]
    speaker: Speaker | None  # None = either speaker
    kind: str  # "required" | "prohibited"
    window_seconds: float | None = None  # None = whole call


RULES: tuple[_Rule, ...] = (
    _Rule(
        name="Required introduction",
        keywords=("this is", "my name is", "calling from", "calling on behalf of"),
        speaker=Speaker.REP,
        kind="required",
        window_seconds=60.0,
    ),
    _Rule(
        name="Required recording disclosure",
        keywords=("recorded", "recording this call", "for quality and training"),
        speaker=None,
        kind="required",
        window_seconds=90.0,
    ),
    _Rule(
        name="Prohibited guaranteed-return claim",
        keywords=("guaranteed return", "guaranteed profit", "risk-free investment", "can't lose"),
        speaker=Speaker.REP,
        kind="prohibited",
    ),
    _Rule(
        name="Unapproved discount mention",
        keywords=("% off", "percent off", "discount", "waive the fee", "throw in for free"),
        speaker=Speaker.REP,
        kind="prohibited",
    ),
)


def _find_hit(candidates: list[TranscriptSegment], keywords: tuple[str, ...]) -> TranscriptSegment | None:
    for seg in candidates:
        text_lower = seg.text.lower()
        if any(kw in text_lower for kw in keywords):
            return seg
    return None


def _in_scope(segment: TranscriptSegment, rule: _Rule) -> bool:
    if rule.speaker is not None and segment.speaker != rule.speaker:
        return False
    if rule.window_seconds is not None and segment.start > rule.window_seconds:
        return False
    return True


def compute_compliance(transcript: list[TranscriptSegment]) -> ComplianceReport:
    checks: list[ComplianceCheck] = []
    applicable = 0
    good = 0

    for rule in RULES:
        candidates = [seg for seg in transcript if _in_scope(seg, rule)]
        if not candidates:
            checks.append(
                ComplianceCheck(
                    rule=rule.name,
                    result=ComplianceCheckResult.NOT_APPLICABLE,
                    evidence="No matching speaker segments in scope for this call",
                )
            )
            continue

        applicable += 1
        hit = _find_hit(candidates, rule.keywords)

        if rule.kind == "required":
            if hit:
                good += 1
                checks.append(ComplianceCheck(rule=rule.name, result=ComplianceCheckResult.PASS, evidence=f'"{hit.text}"'))
            else:
                checks.append(ComplianceCheck(rule=rule.name, result=ComplianceCheckResult.FAIL, evidence=None))
        else:
            if hit:
                checks.append(ComplianceCheck(rule=rule.name, result=ComplianceCheckResult.DETECTED, evidence=f'"{hit.text}"'))
            else:
                good += 1
                checks.append(ComplianceCheck(rule=rule.name, result=ComplianceCheckResult.NOT_DETECTED, evidence=None))

    adherence_pct = (good / applicable * 100.0) if applicable else 100.0
    return ComplianceReport(checks=checks, adherence_pct=adherence_pct)
