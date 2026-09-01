from moex_crash_radar.oi_flow_quality import QualityStatus, SourceCoverage, assess_quality


def test_quality_ready_requires_all_mandatory_sources():
    report = assess_quality([
        SourceCoverage("OHLCV_1H", 100, 100),
        SourceCoverage("OHLCV_4H", 100, 100),
        SourceCoverage("FUTOI", 100, 98),
    ], point_in_time_safe=True)
    assert report.status is QualityStatus.DATA_READY
    assert report.coverage > 0.99


def test_quality_is_not_ready_when_one_source_is_under_threshold():
    report = assess_quality([
        SourceCoverage("OHLCV_1H", 100, 100),
        SourceCoverage("OHLCV_4H", 100, 100),
        SourceCoverage("FUTOI", 100, 90),
    ], point_in_time_safe=True)
    assert report.status is not QualityStatus.DATA_READY
    assert "FUTOI" in report.missing_sources


def test_lookahead_forces_no_go_even_with_complete_coverage():
    report = assess_quality([
        SourceCoverage("OHLCV_1H", 100, 100),
        SourceCoverage("FUTOI", 100, 100),
    ], point_in_time_safe=False)
    assert report.status is QualityStatus.NO_GO
    assert report.point_in_time_safe is False
