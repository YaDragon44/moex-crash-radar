from moex_crash_radar.historical_oil import parse_fred_brent_csv


def test_parse_fred_brent_csv_skips_missing_and_invalid_rows():
    text = "observation_date,DCOILBRENTEU\n2024-01-01,75.25\n2024-01-02,.\n2024-01-03,76.10\ninvalid,80\n"
    rows = parse_fred_brent_csv(text)
    assert [x.begin for x in rows] == ["2024-01-01", "2024-01-03"]
    assert rows[0].close == 75.25
    assert rows[0].open == rows[0].high == rows[0].low == rows[0].close


def test_parse_fred_brent_csv_rejects_non_positive_values():
    text = "DATE,DCOILBRENTEU\n2024-01-01,0\n2024-01-02,-1\n2024-01-03,80\n"
    rows = parse_fred_brent_csv(text)
    assert len(rows) == 1
    assert rows[0].close == 80.0
