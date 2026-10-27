"""Cover art lookup via the iTunes Search API (no API key needed)."""

from __future__ import annotations

from collections import OrderedDict
import logging
import re
import unicodedata

import aiohttp

_LOGGER = logging.getLogger(__name__)

SEARCH_URL = "https://itunes.apple.com/search"
_TIMEOUT = aiohttp.ClientTimeout(total=10)
_CACHE_SIZE = 200
_SIZE_RE = re.compile(r"/\d+x\d+bb\.")
_PAREN_RE = re.compile(r"\([^)]*\)|\[[^\]]*\]")


def normalize(text: str) -> str:
    """The tuner reports names in full-width characters (e.g. 'Ｂａｎｋ　Ｂａｎｄ')."""
    return " ".join(unicodedata.normalize("NFKC", text).split())


def clean_artist(artist: str) -> str:
    """'仲宗根泉（ＨＹ）' -> '仲宗根泉': iTunes lists the singer without the group."""
    return normalize(_PAREN_RE.sub("", normalize(artist))) or normalize(artist)


def _key(text: str) -> str:
    return re.sub(r"\s+", "", normalize(text)).casefold()


class ArtworkFinder:
    """Looks up and caches cover art URLs per (title, artist)."""

    def __init__(self, session: aiohttp.ClientSession, size: int = 600) -> None:
        self._session = session
        self._size = size
        self._cache: OrderedDict[tuple[str, str], str | None] = OrderedDict()

    async def lookup(self, title: str, artist: str | None) -> str | None:
        if not title:
            return None
        cache_key = (_key(title), _key(artist or ""))
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        try:
            url = await self._search(normalize(title), clean_artist(artist or ""))
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            # Not cached, so the next poll retries.
            _LOGGER.debug("Artwork lookup failed for %s / %s: %s", title, artist, err)
            return None

        self._cache[cache_key] = url
        if len(self._cache) > _CACHE_SIZE:
            self._cache.popitem(last=False)
        return url

    async def _search(self, title: str, artist: str) -> str | None:
        params = {
            "term": f"{title} {artist}".strip(),
            "country": "JP",
            "media": "music",
            "entity": "song",
            "limit": "10",
        }
        async with self._session.get(SEARCH_URL, params=params, timeout=_TIMEOUT) as resp:
            resp.raise_for_status()
            # iTunes answers with text/javascript.
            data = await resp.json(content_type=None)

        results = [r for r in data.get("results", []) if r.get("artworkUrl100")]
        if not results:
            return None

        # Prefer the same artist: the same title often exists as many covers.
        want = _key(artist)
        best = next(
            (r for r in results if want and _key(r.get("artistName", "")) == want),
            None,
        ) or next(
            (r for r in results if want and want in _key(r.get("artistName", ""))),
            None,
        )
        if best is None:
            if want:
                return None
            best = results[0]
        return _SIZE_RE.sub(f"/{self._size}x{self._size}bb.", best["artworkUrl100"])
