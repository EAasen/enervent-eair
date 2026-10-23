"""Data update coordinator for Enervent eAir."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api_client import EnerventApiClient, EnerventApiError
from .const import DOMAIN


class EnerventDataUpdateCoordinator(
    DataUpdateCoordinator[dict[int, int | float]]
):
    """Coordinate updates from the Enervent cloud connection."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EnerventApiClient,
        scan_interval: int,
    ) -> None:
        self.client = client
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[int, int | float]:
        try:
            return await self.client.async_get_status()
        except EnerventApiError as err:
            raise UpdateFailed(
                f"Unable to retrieve Enervent unit status: {err}"
            ) from err
