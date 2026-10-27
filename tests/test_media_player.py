"""Entity tests."""

from homeassistant.components.media_player import (
    ATTR_INPUT_SOURCE,
    ATTR_INPUT_SOURCE_LIST,
    ATTR_MEDIA_TITLE,
    ATTR_MEDIA_VOLUME_LEVEL,
    DOMAIN as MP_DOMAIN,
    SERVICE_SELECT_SOURCE,
    SERVICE_VOLUME_UP,
)
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, STATE_PLAYING

from custom_components.usen_mpx1.const import DOMAIN

from .conftest import BASE

ENTITY = "media_player.usen_mpx_1"


def _posts(aioclient_mock, cgi):
    return [
        data
        for method, url, data, _ in aioclient_mock.mock_calls
        if method == "POST" and str(url) == f"{BASE}/cgi-bin/{cgi}.cgi"
    ]


async def _setup(hass, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_state(hass, mock_device, config_entry):
    await _setup(hass, config_entry)
    state = hass.states.get(ENTITY)
    assert state.state == STATE_PLAYING
    assert state.attributes[ATTR_INPUT_SOURCE] == "カヴァー・ソングス"
    assert state.attributes[ATTR_INPUT_SOURCE_LIST][-1] == "AUX"
    assert len(state.attributes[ATTR_INPUT_SOURCE_LIST]) == 11
    assert state.attributes[ATTR_MEDIA_TITLE] == "ハートビート"
    assert round(state.attributes[ATTR_MEDIA_VOLUME_LEVEL], 3) == round(57 / 63, 3)
    assert hass.states.get("sensor.usen_mpx_1_next_track").state == "どんなときも。 / ＭＡＸ"


async def test_commands(hass, mock_device, config_entry):
    await _setup(hass, config_entry)

    await hass.services.async_call(
        MP_DOMAIN, SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: ENTITY, ATTR_INPUT_SOURCE: "ジャズ・スタンダード"}, blocking=True,
    )
    await hass.services.async_call(
        MP_DOMAIN, SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: ENTITY, ATTR_INPUT_SOURCE: "AUX"}, blocking=True,
    )
    assert _posts(mock_device, "chn_chg") == ["chn=6", "chn=99"]

    await hass.services.async_call(MP_DOMAIN, SERVICE_VOLUME_UP, {ATTR_ENTITY_ID: ENTITY}, blocking=True)
    assert _posts(mock_device, "vol_chg") == ["vol=1"]

    await hass.services.async_call(MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY}, blocking=True)
    assert len(_posts(mock_device, "power_off")) == 1

    await hass.services.async_call(
        DOMAIN, "play_cue", {ATTR_ENTITY_ID: ENTITY, "cue": 9, "repeat": True}, blocking=True,
    )
    assert _posts(mock_device, "cue_play") == [
        "cue=9&vol=6&rep=1&muo=0&stt=0",
        "cue=9&vol=6&rep=1&muo=0&stt=2",
    ]
