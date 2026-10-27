"""Config flow for the USEN MPX-1."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import Mpx1Client, Mpx1Error, Mpx1Status
from .const import DOMAIN, MODEL

DEFAULT_HOST = "192.168.100.29"


class Mpx1ConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _async_probe(self, host: str) -> tuple[Mpx1Status | None, dict[str, str]]:
        client = Mpx1Client(async_get_clientsession(self.hass), host)
        try:
            return await client.get_status(), {}
        except Mpx1Error:
            return None, {"base": "cannot_connect"}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            status, errors = await self._async_probe(host)
            if status is not None:
                await self.async_set_unique_id(status.mac or host)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(title=f"USEN {MODEL}", data={CONF_HOST: host})

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Required(CONF_HOST): str}),
                user_input or {CONF_HOST: DEFAULT_HOST},
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the IP address of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            status, errors = await self._async_probe(host)
            if status is not None:
                await self.async_set_unique_id(status.mac or host)
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_HOST: host}
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Required(CONF_HOST): str}),
                user_input or {CONF_HOST: entry.data[CONF_HOST]},
            ),
            errors=errors,
        )
