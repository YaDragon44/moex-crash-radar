import pytest

from moex_crash_radar.oi_flow_data_audit import (
    AuditStatus,
    DatasetAudit,
    baseline_public_audit,
    quality_coverage,
    validate_no_lookahead,
)


def test_public_baseline_is_conservative_for_intraday_positioning():
    audit = baseline_public_audit("SBRF")
    assert audit.core_price_ready is True
    assert audit.oi_ready is False
    assert audit.participant_intraday_ready is False
    assert audit.participant_daily_ready is True
    assert audit.dataset("OI_INTRADAY").status is AuditStatus.PARTIAL
    assert audit.dataset("PARTICIPANT_INTRADAY").history_from == "2020"
    assert audit.supported_models() == ("M0", "M1", "M5")


def test_daily_participant_data_requires_next_use_timing():
    row = DatasetAudit(
        instrument="SBRF",
        dataset="PARTICIPANT_DAILY",
        status=AuditStatus.DELAYED,
        granularity="1D",
        history_from=None,
        history_to=None,
        event_time_semantics="daily aggregate",
        available_time_semantics="usable immediately",
    )
    with pytest.raises(ValueError, match="next-use timing"):
        validate_no_lookahead(row)


def test_quality_coverage_marks_documented_but_unfetched_futoi_partial():
    rows = baseline_public_audit("MIX").datasets
    assert quality_coverage(rows) == 76.0


def test_full_model_requires_actual_futoi_coverage_not_documentation_only():
    audit = baseline_public_audit("GAZR")
    assert "FULL" not in audit.supported_models()
