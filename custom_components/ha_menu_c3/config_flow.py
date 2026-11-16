"""Install a Home Assistant menu controller per ESPHome node."""

from __future__ import annotations

import re
import voluptuous as vol
from homeassistant import config_entries
from .const import CONF_DEVICE_NAME, DOMAIN


class HAMenuC3ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            device = user_input[CONF_DEVICE_NAME].strip().lower()
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,48}", device):
                errors[CONF_DEVICE_NAME] = "invalid_name"
            elif any(e.data.get(CONF_DEVICE_NAME) == device for e in self._async_current_entries()):
                return self.async_abort(reason="already_configured")
            else:
                await self.async_set_unique_id(device)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"HA Menu ({device})", data={CONF_DEVICE_NAME: device})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE_NAME, default="ha-menu-c3"): str}),
            errors=errors,
        )
