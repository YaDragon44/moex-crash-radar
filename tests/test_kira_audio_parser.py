from moex_crash_radar.kira_audio_parser import TranscriptSegment, parse_transcript


def test_known_asset_and_action():
    r = parse_transcript([TranscriptSegment(10, 15, "На этой неделе докупаю Озон Фармацевтику")], "https://t.me/kira_pronira/1")
    assert len(r) == 1
    assert r[0].action == "ADD"
    assert r[0].asset == "OZPH"
    assert r[0].quantity is None
    assert r[0].price is None
    assert r[0].amount is None


def test_unknown_asset_is_not_invented():
    r = parse_transcript([TranscriptSegment(1, 2, "Сегодня покупаю одну компанию")], "src")
    assert r[0].action == "BUY"
    assert r[0].asset is None
    assert r[0].confidence < 0.8


def test_analysis_without_operation_is_ignored():
    r = parse_transcript([TranscriptSegment(1, 2, "Мне нравится отчет Интер РАО")], "src")
    assert r == []


def test_specific_ozon_pharma_beats_ozon_alias():
    r = parse_transcript([TranscriptSegment(1, 2, "Докупаю Ozon Pharma")], "src")
    assert r[0].asset == "OZPH"


def test_sell():
    r = parse_transcript([TranscriptSegment(1, 2, "Полностью продаю Яндекс")], "src")
    assert r[0].action == "SELL"
    assert r[0].asset == "YDEX"
