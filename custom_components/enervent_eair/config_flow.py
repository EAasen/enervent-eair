"""Config flow for Enervent eAir."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api_client import (
    EnerventApiClient,
    EnerventApiError,
    EnerventAuthError,
    EnerventCertificateError,
    EnerventConnectionError,
)
from .const import (
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL_NUMBER,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class EnerventConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Enervent eAir config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str | int] | None = None
    ) -> config_entries.FlowResult:
        """Validate the serial number and PIN."""
        errors: dict[str, str] = {}
        if user_input is not None:
            serial_number = str(user_input[CONF_SERIAL_NUMBER]).strip()
            pin = str(user_input[CONF_PIN]).strip()
            client = EnerventApiClient(
                async_get_clientsession(self.hass),
                serial_number,
                pin,
            )
            try:
                await client.async_login()
            except EnerventAuthError:
                errors["base"] = "invalid_auth"
            except EnerventCertificateError as err:
                _LOGGER.warning("Enervent setup failed: %s", err)
                errors["base"] = "certificate_error"
            except (EnerventConnectionError, EnerventApiError) as err:
                _LOGGER.warning("Enervent setup failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(
                    client.device_id or serial_number.casefold()
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Enervent eAir ({serial_number[-4:]})",
                    data={
                        CONF_SERIAL_NUMBER: serial_number,
                        CONF_PIN: pin,
                        CONF_SCAN_INTERVAL: int(
                            user_input.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            )
                        ),
                    },
                )
            finally:
                await client.async_close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SERIAL_NUMBER): TextSelector(
                        TextSelectorConfig()
                    ),
                    vol.Required(CONF_PIN): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
            errors=errors,
        )
