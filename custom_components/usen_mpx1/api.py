"""Client for the USEN MPX-1 web remote (http://<host>/cgi-bin/*.cgi)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import re

import aiohttp

VOLUME_MAX = 63
CHANNEL_AUX = 99

_TIMEOUT = aiohttp.ClientTimeout(total=10)
_FORM = {"Content-Type": "application/x-www-form-urlencoded"}

_MAC_RE = re.compile(r"([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})")
_VERSION_RE = re.compile(r"Ver[\d.]+")
_CH_STR_RE = re.compile(r'id="ch(\d+)_str"[^>]*>(.*?)</li>', re.S)
_CH_NUM_RE = re.compile(r'id="ch(\d+)_num"[^>]*>\s*(\d+)\s*</li>', re.S)


class Mpx1Error(Exception):
    """Communication with the tuner failed."""


@dataclass
class Mpx1Status:
    """Parsed /data/home.csv."""

    power: bool
    volume: int
    preset: int
    channel_name: str
    last_track: str
    now_playing: str
    next_tracks: list[str]
    info: list[str]

    @property
    def title(self) -> str:
        return self.now_playing.split(" / ", 1)[0]

    @property
    def artist(self) -> str | None:
        parts = self.now_playing.split(" / ", 1)
        return parts[1] if len(parts) > 1 else None

    def _info_value(self, keyword: str) -> str | None:
        for item in self.info:
            if keyword in item and ":" in item:
                return item.split(":", 1)[1].strip()
        return None

    @property
    def mac(self) -> str | None:
        for item in self.info:
            if match := _MAC_RE.search(item):
                return match.group(1).lower()
        return None

    @property
    def firmware(self) -> str | None:
        for item in self.info:
            if match := _VERSION_RE.search(item):
                return match.group(0)
        return None

    @property
    def serial(self) -> str | None:
        return self._info_value("ｼﾘｱﾙ")

    @property
    def line_status(self) -> str | None:
        return self._info_value("回線状態")

    @classmethod
    def parse(cls, text: str) -> Mpx1Status:
        fields = text.strip().split(",")
        if len(fields) < 11:
            raise Mpx1Error(f"Unexpected home.csv: {text[:100]!r}")
        return cls(
            power=fields[0].strip() == "1",
            volume=int(fields[1] or 0),
            preset=int(fields[2] or 0),
            channel_name=fields[3],
            last_track=fields[4],
            now_playing=fields[5],
            next_tracks=fields[6:11],
            info=fields[11:],
        )


@dataclass
class Mpx1Preset:
    """A channel preset (1-10) from the CHANNEL list page."""

    number: int
    name: str
    channel_id: str = field(default="")


def parse_presets(html: str) -> list[Mpx1Preset]:
    """Extract presets that are actually set (channel number > 0)."""
    names = {int(n): re.sub(r"<[^>]+>", "", s).strip() for n, s in _CH_STR_RE.findall(html)}
    ids = dict((int(n), v) for n, v in _CH_NUM_RE.findall(html))
    return [
        Mpx1Preset(number=n, name=names[n], channel_id=ids[n])
        for n in sorted(names)
        if n in ids and int(ids[n]) > 0
    ]


class Mpx1Client:
    """Talks to one MPX-1."""

    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        self._session = session
        self.host = host
        # The tuner is a small embedded box; do not hit it concurrently.
        self._lock = asyncio.Lock()

    @property
    def base_url(self) -> str:
        return f"http://{self.host}"

    async def _request(self, method: str, path: str, data: str | None = None) -> str:
        async with self._lock:
            try:
                async with self._session.request(
                    method,
                    f"{self.base_url}{path}",
                    data=data,
                    headers=_FORM if method == "POST" else None,
                    timeout=_TIMEOUT,
                ) as resp:
                    resp.raise_for_status()
                    return await resp.text(encoding="utf-8", errors="replace")
            except (aiohttp.ClientError, TimeoutError) as err:
                raise Mpx1Error(f"{method} {path} failed: {err}") from err

    async def _post(self, path: str, data: str = "") -> str:
        return await self._request("POST", path, data)

    async def get_status(self) -> Mpx1Status:
        return Mpx1Status.parse(await self._request("GET", "/data/home.csv"))

    async def get_presets(self) -> list[Mpx1Preset]:
        return parse_presets(await self._request("GET", "/cgi-bin/channel_print.cgi"))

    async def power_on(self) -> None:
        await self._post("/cgi-bin/power_on.cgi")

    async def power_off(self) -> None:
        await self._post("/cgi-bin/power_off.cgi")

    async def volume_step(self, up: bool) -> int | None:
        """Change volume by one step. Returns the new volume if the tuner reports it."""
        text = (await self._post("/cgi-bin/vol_chg.cgi", f"vol={1 if up else 0}")).strip()
        # The web UI treats a response >= 100 as an error code.
        if text.isdigit() and int(text) <= VOLUME_MAX:
            return int(text)
        return None

    async def set_volume(self, target: int, current: int) -> int:
        """Step from current to target (the tuner has no absolute volume command)."""
        target = max(0, min(VOLUME_MAX, target))
        while current != target:
            new = await self.volume_step(target > current)
            if new is None or new == current:
                break
            current = new
        return current

    async def select_channel(self, chn: int) -> None:
        """chn: 1-10 = preset, 99 = AUX."""
        await self._post("/cgi-bin/chn_chg.cgi", f"chn={chn}")

    async def cue(
        self, cue: int, state: int, volume: int = 6, repeat: bool = False, mute_bgm: bool = False
    ) -> None:
        """state: 0 = set, 1 = mute BGM, 2 = play, 3 = end. volume: 0-12 (6 = +/-0)."""
        await self._post(
            "/cgi-bin/cue_play.cgi",
            f"cue={cue}&vol={volume}&rep={int(repeat)}&muo={int(mute_bgm)}&stt={state}",
        )
