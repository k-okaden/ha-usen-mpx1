"""Fixtures for USEN MPX-1 tests."""

from pathlib import Path

import pytest

from homeassistant.const import CONF_HOST

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.usen_mpx1.artwork import SEARCH_URL
from custom_components.usen_mpx1.const import DOMAIN

HOST = "192.168.100.29"
BASE = f"http://{HOST}"
MAC = "00:0d:79:00:00:01"
FIXTURES = Path(__file__).parent / "fixtures"
ARTWORK_URL = "https://is1-ssl.mzstatic.com/image/thumb/Music/bankband/600x600bb.jpg"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_device(aioclient_mock):
    """A powered-on MPX-1."""
    aioclient_mock.get(f"{BASE}/data/home.csv", text=fixture("home_on.csv"))
    aioclient_mock.get(f"{BASE}/cgi-bin/channel_print.cgi", text=fixture("channel_print.html"))
    for cgi in ("power_on", "power_off", "chn_chg", "cue_play"):
        aioclient_mock.post(f"{BASE}/cgi-bin/{cgi}.cgi", text="OK")
    aioclient_mock.post(f"{BASE}/cgi-bin/vol_chg.cgi", text="58")
    aioclient_mock.get(SEARCH_URL, text=fixture("itunes_search.json"))
    return aioclient_mock


@pytest.fixture
def config_entry(hass):
    entry = MockConfigEntry(domain=DOMAIN, unique_id=MAC, data={CONF_HOST: HOST})
    entry.add_to_hass(hass)
    return entry
