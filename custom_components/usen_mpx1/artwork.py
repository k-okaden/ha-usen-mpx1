"""Cover art lookup via the iTunes Search API (no API key needed)."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable
import logging
import re
import time
from typing import Any
import unicodedata

import aiohttp

_LOGGER = logging.getLogger(__name__)

SEARCH_URL = "https://itunes.apple.com/search"
_TIMEOUT = aiohttp.ClientTimeout(total=10)
_CACHE_SIZE = 200
_RETRY_AFTER = 300  # seconds to wait after a network error
_SIZE_RE = re.compile(r"/\d+x\d+bb\.")
_PAREN_RE = re.compile(r"\(([^)]*)\)|\[([^\]]*)\]")
# Separators between performers, applied after NFKC (so '／' is already '/').
_SPLIT_RE = re.compile(
    r"\s*(?:/|,|、|&|×|\bfeat\.?|\bfeaturing\b|\bwith\b|\band\b|\bCV:?)\s*", re.I
)
_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})
_LATIN_RE = re.compile(r"[A-Za-z]")


def normalize(text: str) -> str:
    """The tuner reports names in full-width characters (e.g. 'Ｂａｎｋ　Ｂａｎｄ')."""
    return " ".join(unicodedata.normalize("NFKC", text).translate(_QUOTES).split())


def artist_names(artist: str) -> list[str]:
    """Split a credit into individual names, most specific first.

    'ゴジュウウルフ／遠野吠（冬野心央）' -> ['ゴジュウウルフ', '遠野吠', '冬野心央']
    '仲宗根泉（ＨＹ）' -> ['仲宗根泉', 'HY']
    """
    text = normalize(artist)
    bracketed = [a or b for a, b in _PAREN_RE.findall(text)]
    outside = _PAREN_RE.sub(" ", text)
    names: list[str] = []
    for part in [*_SPLIT_RE.split(outside), *(p for b in bracketed for p in _SPLIT_RE.split(b))]:
        part = normalize(part)
        if part and part not in names:
            names.append(part)
    return names


def search_terms(title: str, artist: str | None) -> list[str]:
    """Queries to try in order; iTunes finds nothing for long multi-name credits."""
    title = normalize(title)
    names = artist_names(artist or "")
    terms = [f"{title} {name}" for name in names]
    terms.append(title)
    return terms


def _key(text: str) -> str:
    return re.sub(r"\s+", "", normalize(text)).casefold()


def pick_result(results: Iterable[dict[str, Any]], artist: str | None) -> dict[str, Any] | None:
    """Return the first result by the same artist (any of the credited names).

    The same title often exists as many covers by other singers, so a
    result by someone else is never used when an artist is known.
    """
    results = [r for r in results if r.get("artworkUrl100")]
    keys = [_key(n) for n in artist_names(artist or "") if len(_key(n)) >= 2]
    if not keys:
        return results[0] if results else None
    for result in results:
        theirs = _key(result.get("artistName", ""))
        if len(theirs) >= 2 and any(k in theirs or theirs in k for k in keys):
            return result
    return None


class ArtworkFinder:
    """Looks up and caches cover art URLs per (title, artist)."""

    def __init__(self, session: aiohttp.ClientSession, size: int = 600) -> None:
        self._session = session
        self._size = size
        self._cache: OrderedDict[tuple[str, str], str | None] = OrderedDict()
        self._retry_at = 0.0

    async def lookup(self, title: str, artist: str | None) -> str | None:
        if not title:
            return None
        cache_key = (_key(title), _key(artist or ""))
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]
        if time.monotonic() < self._retry_at:
            return None

        try:
            url = await self._find(title, artist)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            # Not cached, so it is retried after a pause.
            _LOGGER.debug("Artwork lookup failed for %s / %s: %s", title, artist, err)
            self._retry_at = time.monotonic() + _RETRY_AFTER
            return None

        self._cache[cache_key] = url
        if len(self._cache) > _CACHE_SIZE:
            self._cache.popitem(last=False)
        return url

    async def _find(self, title: str, artist: str | None) -> str | None:
        # The JP store lists Western artists in katakana ('Ed Sheeran' -> 'エド・シーラン'),
        # so a Latin-script artist is also tried against the US store.
        countries = ["JP"]
        if artist and _LATIN_RE.search(normalize(artist)):
            countries.append("US")
        for country in countries:
            for term in search_terms(title, artist):
                if result := pick_result(await self._search(term, country), artist):
                    return _SIZE_RE.sub(
                        f"/{self._size}x{self._size}bb.", result["artworkUrl100"]
                    )
        return None

    async def _search(self, term: str, country: str) -> list[dict[str, Any]]:
        params = {
            "term": term,
            "country": country,
            "media": "music",
            "entity": "song",
            "limit": "10",
        }
        async with self._session.get(SEARCH_URL, params=params, timeout=_TIMEOUT) as resp:
            resp.raise_for_status()
            # iTunes answers with text/javascript.
            data = await resp.json(content_type=None)
        return data.get("results", [])
