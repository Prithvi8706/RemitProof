from app.services.baseline_matcher import baseline_match


def test_baseline_resolves_explicit_parent_mapping(bundle_factory):
    result = baseline_match(bundle_factory("SPIKE_01"))

    assert result.status == "matched"
    assert result.customer_id == "CUS_S01"
    assert result.matched_invoices == ["INV_S01A"]


def test_baseline_resolves_known_payer_record(bundle_factory):
    result = baseline_match(bundle_factory("SPIKE_02"))

    assert result.status == "matched"
    assert result.customer_id == "CUS_S02"


def test_baseline_does_not_guess_between_numeric_allocations(bundle_factory):
    result = baseline_match(bundle_factory("SPIKE_05"))

    assert result.status == "unresolved"
    assert result.reason == "multiple_financial_allocations"
    assert result.candidate_count == 2


def test_baseline_does_not_apply_unreferenced_credit(bundle_factory):
    result = baseline_match(bundle_factory("SPIKE_07"))

    assert result.status == "unresolved"
    assert result.reason == "no_unique_safe_allocation"


def test_baseline_does_not_discard_credit_backed_alternative(bundle_factory):
    result = baseline_match(bundle_factory("SPIKE_10"))

    assert result.status == "unresolved"
    assert result.reason == "multiple_financial_allocations"
    assert result.candidate_count == 2
