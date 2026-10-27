"""Parser tests."""

from custom_components.usen_mpx1.api import Mpx1Status, parse_presets

from .conftest import MAC, fixture


def test_parse_status():
    status = Mpx1Status.parse(fixture("home_on.csv"))
    assert status.power is True
    assert status.volume == 57
    assert status.preset == 2
    assert status.channel_name == "カヴァー・ソングス"
    assert status.title == "ハートビート"
    assert status.artist == "Ｂａｎｋ　Ｂａｎｄ"
    assert len(status.next_tracks) == 5
    assert status.mac == MAC
    assert status.firmware == "Ver2.4.8"
    assert status.serial == "DM000000000"
    assert status.line_status == "24.8M 10/27 02:56"


def test_parse_status_off():
    assert Mpx1Status.parse(fixture("home_off.csv")).power is False


def test_parse_presets():
    presets = parse_presets(fixture("channel_print.html"))
    assert len(presets) == 10
    assert presets[0].number == 1
    assert presets[0].name == "週間 USEN HIT J-POPランキング"
    assert presets[1].name == "カヴァー・ソングス"
