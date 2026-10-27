"""Cover art lookup tests."""

import aiohttp

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.usen_mpx1.artwork import (
    SEARCH_URL,
    ArtworkFinder,
    clean_artist,
    normalize,
)

from .conftest import ARTWORK_URL, fixture


def test_normalize_full_width():
    assert normalize("Ｂａｎｋ　Ｂａｎｄ") == "Bank Band"


def test_clean_artist_drops_group():
    assert clean_artist("仲宗根泉（ＨＹ）") == "仲宗根泉"
    assert clean_artist("Ａｃｉｄ　Ｂｌａｃｋ　Ｃｈｅｒｒｙ") == "Acid Black Cherry"


def _search_calls(aioclient_mock):
    return [c for c in aioclient_mock.mock_calls if str(c[1]).startswith(SEARCH_URL)]


async def test_prefers_same_artist_and_caches(hass, aioclient_mock):
    aioclient_mock.get(SEARCH_URL, text=fixture("itunes_search.json"))
    finder = ArtworkFinder(async_get_clientsession(hass))

    assert await finder.lookup("ハートビート", "Ｂａｎｋ　Ｂａｎｄ") == ARTWORK_URL
    assert await finder.lookup("ハートビート", "Bank Band") == ARTWORK_URL
    assert len(_search_calls(aioclient_mock)) == 1

    params = _search_calls(aioclient_mock)[0][1].query
    assert params["term"] == "ハートビート Bank Band"
    assert params["country"] == "JP"


async def test_other_artist_only_gives_no_image(hass, aioclient_mock):
    aioclient_mock.get(SEARCH_URL, text=fixture("itunes_search.json"))
    finder = ArtworkFinder(async_get_clientsession(hass))
    assert await finder.lookup("ハートビート", "Unknown Artist") is None


async def test_no_results(hass, aioclient_mock):
    aioclient_mock.get(SEARCH_URL, json={"resultCount": 0, "results": []})
    finder = ArtworkFinder(async_get_clientsession(hass))
    assert await finder.lookup("USEN オリジナル", None) is None


async def test_error_is_not_cached(hass, aioclient_mock):
    aioclient_mock.get(SEARCH_URL, exc=aiohttp.ClientError)
    finder = ArtworkFinder(async_get_clientsession(hass))
    assert await finder.lookup("ハートビート", "Bank Band") is None

    aioclient_mock.clear_requests()
    aioclient_mock.get(SEARCH_URL, text=fixture("itunes_search.json"))
    assert await finder.lookup("ハートビート", "Bank Band") == ARTWORK_URL
