"""GUI installation for HA Menu C3."""

from __future__ import annotations

import re

import voluptuous as vol
from homeassistant import config_entries

from .const import CONF_DEVICE_NAME, DOMAIN


class HAMenuC3ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create a single HA Menu C3 integration instance."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Configure the ESPHome node name (not the friendly name)."""
        await self.async_set_unique_id("main")
        self._abort_if_unique_id_configured()

        errors = {}
        if user_input is not None:
            device = user_input[CONF_DEVICE_NAME].strip().lower()
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,48}", device):
                errors[CONF_DEVICE_NAME] = "invalid_name"
            else:
                return self.async_create_entry(
                    title=f"HA Menu ({device})",
                    data={CONF_DEVICE_NAME: device},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_NAME, default="ha-menu-c3"): str,
            }),
            errors=errors,
        )
