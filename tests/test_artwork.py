"""Cover art lookup tests."""

import aiohttp

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.usen_mpx1.artwork import (
    SEARCH_URL,
    ArtworkFinder,
    artist_names,
    normalize,
    pick_result,
    search_terms,
)

from .conftest import ARTWORK_URL, fixture


def test_normalize_full_width():
    assert normalize("Ｂａｎｋ　Ｂａｎｄ") == "Bank Band"


def test_artist_names():
    assert artist_names("Ａｃｉｄ　Ｂｌａｃｋ　Ｃｈｅｒｒｙ") == ["Acid Black Cherry"]
    assert artist_names("仲宗根泉（ＨＹ）") == ["仲宗根泉", "HY"]
    assert artist_names("ゴジュウウルフ／遠野吠（冬野心央）") == ["ゴジュウウルフ", "遠野吠", "冬野心央"]
    assert artist_names("アーリャ(CV:上坂すみれ)") == ["アーリャ", "上坂すみれ"]
    assert artist_names("Ａ　ｆｅａｔ．　Ｂ") == ["A", "B"]
    assert artist_names("Ａｂｂｙ，Ｓｕｙ　Ａｎｄ　Ｊｅｓｓａ") == ["Abby", "Suy", "Jessa"]


def test_normalize_curly_quotes():
    assert normalize("Ｃａｎ’ｔ　Ｂｕｙ") == "Can't Buy"


def test_search_terms_fall_back_to_title():
    assert search_terms("影を連れて", "ゴジュウウルフ／遠野吠（冬野心央）") == [
        "影を連れて ゴジュウウルフ",
        "影を連れて 遠野吠",
        "影を連れて 冬野心央",
        "影を連れて",
    ]
    assert search_terms("ＴＲＵＥ　ＬＯＶＥ", None) == ["TRUE LOVE"]


def _result(artist):
    return {"artistName": artist, "artworkUrl100": f"https://example/{artist}/100x100bb.jpg"}


def test_pick_result_matches_any_credited_name():
    results = [_result("水乃余韻"), _result("ゴジュウウルフ/遠野吠 (冬野心央)")]
    assert pick_result(results, "ゴジュウウルフ／遠野吠（冬野心央）") is results[1]
    assert pick_result(results, "遠野吠") is results[1]


def test_pick_result_ignores_other_singers():
    assert pick_result([_result("小田 和正")], "鈴木鈴木") is None
    # Without a known artist, take the top hit.
    assert pick_result([_result("小田 和正")], None)["artistName"] == "小田 和正"


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


async def test_tries_each_name_then_gives_up(hass, aioclient_mock):
    aioclient_mock.get(SEARCH_URL, text=fixture("itunes_search.json"))
    finder = ArtworkFinder(async_get_clientsession(hass))

    assert await finder.lookup("ハートビート", "山田／佐藤") is None
    queries = [(c[1].query["term"], c[1].query["country"]) for c in _search_calls(aioclient_mock)]
    assert queries == [
        ("ハートビート 山田", "JP"),
        ("ハートビート 佐藤", "JP"),
        ("ハートビート", "JP"),
    ]

    # A miss is cached too.
    assert await finder.lookup("ハートビート", "山田／佐藤") is None
    assert len(_search_calls(aioclient_mock)) == 3


async def test_latin_artist_also_tries_us_store(hass, aioclient_mock):
    aioclient_mock.get(SEARCH_URL, json={"resultCount": 0, "results": []})
    finder = ArtworkFinder(async_get_clientsession(hass))

    assert await finder.lookup("Ｓｈａｐｅ　ｏｆ　Ｙｏｕ", "Ｅｄ　Ｓｈｅｅｒａｎ") is None
    queries = [(c[1].query["term"], c[1].query["country"]) for c in _search_calls(aioclient_mock)]
    assert queries == [
        ("Shape of You Ed Sheeran", "JP"),
        ("Shape of You", "JP"),
        ("Shape of You Ed Sheeran", "US"),
        ("Shape of You", "US"),
    ]


async def test_no_results(hass, aioclient_mock):
    aioclient_mock.get(SEARCH_URL, json={"resultCount": 0, "results": []})
    finder = ArtworkFinder(async_get_clientsession(hass))
    assert await finder.lookup("USEN オリジナル", None) is None


async def test_error_pauses_then_retries(hass, aioclient_mock):
    aioclient_mock.get(SEARCH_URL, exc=aiohttp.ClientError)
    finder = ArtworkFinder(async_get_clientsession(hass))
    assert await finder.lookup("ハートビート", "Bank Band") is None

    aioclient_mock.clear_requests()
    aioclient_mock.get(SEARCH_URL, text=fixture("itunes_search.json"))
    # Still pausing after the error: no request.
    assert await finder.lookup("ハートビート", "Bank Band") is None
    assert not _search_calls(aioclient_mock)

    finder._retry_at = 0
    assert await finder.lookup("ハートビート", "Bank Band") == ARTWORK_URL
