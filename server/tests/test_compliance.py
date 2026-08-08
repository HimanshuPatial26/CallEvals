from app.compliance import compute_compliance
from app.schemas import ComplianceCheckResult, Speaker, TranscriptSegment


def seg(speaker, start, end, text=""):
    return TranscriptSegment(speaker=speaker, start=start, end=end, text=text)


def _check(report, name):
    return next(c for c in report.checks if c.rule == name)


def test_empty_transcript_is_fully_compliant_by_default():
    report = compute_compliance([])
    assert report.adherence_pct == 100.0
    assert all(c.result == ComplianceCheckResult.NOT_APPLICABLE for c in report.checks)


def test_required_introduction_passes_when_rep_states_it_in_window():
    transcript = [
        seg(Speaker.REP, 0.0, 3.0, "Hi, this is Sarah calling from Emaar Properties."),
        seg(Speaker.CUSTOMER, 3.0, 5.0, "Hi Sarah."),
    ]
    report = compute_compliance(transcript)
    check = _check(report, "Required introduction")
    assert check.result == ComplianceCheckResult.PASS
    assert "Sarah" in check.evidence


def test_required_introduction_fails_when_missing():
    transcript = [
        seg(Speaker.REP, 0.0, 3.0, "So tell me about what you're looking for."),
        seg(Speaker.CUSTOMER, 3.0, 5.0, "A two bedroom in Marina."),
    ]
    report = compute_compliance(transcript)
    check = _check(report, "Required introduction")
    assert check.result == ComplianceCheckResult.FAIL


def test_required_introduction_ignores_keyword_outside_window():
    transcript = [
        seg(Speaker.REP, 0.0, 3.0, "Let's get started on the details."),
        seg(Speaker.REP, 120.0, 123.0, "This is Sarah, by the way."),  # after the 60s window
    ]
    report = compute_compliance(transcript)
    check = _check(report, "Required introduction")
    # rep did speak in-window (applicable), but the intro phrase only appears
    # after the window closes, so it doesn't count
    assert check.result == ComplianceCheckResult.FAIL


def test_prohibited_claim_detected():
    transcript = [
        seg(Speaker.REP, 0.0, 3.0, "This is a guaranteed return investment."),
    ]
    report = compute_compliance(transcript)
    check = _check(report, "Prohibited guaranteed-return claim")
    assert check.result == ComplianceCheckResult.DETECTED


def test_prohibited_claim_not_detected_when_absent():
    transcript = [
        seg(Speaker.REP, 0.0, 3.0, "Prices in this area have historically appreciated well."),
    ]
    report = compute_compliance(transcript)
    check = _check(report, "Prohibited guaranteed-return claim")
    assert check.result == ComplianceCheckResult.NOT_DETECTED


def test_rule_not_applicable_when_no_rep_segments():
    transcript = [seg(Speaker.CUSTOMER, 0.0, 3.0, "Hello?")]
    report = compute_compliance(transcript)
    assert _check(report, "Required introduction").result == ComplianceCheckResult.NOT_APPLICABLE
    assert _check(report, "Prohibited guaranteed-return claim").result == ComplianceCheckResult.NOT_APPLICABLE


def test_adherence_pct_reflects_mixed_results():
    transcript = [
        seg(Speaker.REP, 0.0, 3.0, "Hi, this is Sarah calling from Emaar Properties."),
        seg(Speaker.REP, 3.0, 6.0, "We're recording this call for quality and training."),
        seg(Speaker.REP, 6.0, 9.0, "This is a guaranteed return investment, honestly."),
        seg(Speaker.REP, 9.0, 12.0, "We could do a 10% off deal, let me check."),
    ]
    report = compute_compliance(transcript)
    # 4 applicable checks: intro=pass, disclosure=pass, guaranteed-claim=detected(bad), discount=detected(bad)
    assert report.adherence_pct == 50.0
