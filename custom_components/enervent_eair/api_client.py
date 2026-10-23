"""Async client for the Enervent eAir Socket.IO API."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.parse import urlencode

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_TIMEOUT,
    API_URL,
    PRESET_WRITES,
    REGISTER_FAN_SPEED_OVERRIDE,
    REGISTER_MAX_TEMP,
    REGISTER_MIN_TEMP,
    REGISTER_TARGET_TEMP,
)

_LOGGER = logging.getLogger(__name__)
_SOCKET_PATH = "/socket.io/"
_EVENT_NAME = "message"
_ENGINE_IO_VERSION = "4"
_TEMPERATURE_SCALE = 10
_TEMPERATURE_MIN = 10
_TEMPERATURE_MAX = 35


class EnerventApiError(Exception):
    """Base exception for API failures."""


class EnerventAuthError(EnerventApiError):
    """Authentication failed."""


class EnerventConnectionError(EnerventApiError):
    """The cloud connection failed."""


class EnerventApiClient:
    """Maintain an authenticated Socket.IO session with an eAir unit."""

    def __init__(
        self,
        hass: HomeAssistant,
        serial_number: str,
        pin: str,
    ) -> None:
        self._session = async_get_clientsession(hass)
        self._serial_number = serial_number
        self._pin = pin
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._registers: dict[int, int | float] = {}
        self._state_ready = asyncio.Event()
        self._connect_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._next_id = 1
        self._device_id: str | None = None
        self._authenticated = False
        self._closing = False

    @property
    def device_id(self) -> str | None:
        """Return the device identifier received after authentication."""
        return self._device_id

    async def async_login(self) -> None:
        """Authenticate and load the model and current register snapshot."""
        async with self._connect_lock:
            if self._is_connected and self._authenticated:
                return

            await self._close_socket()
            self._closing = False
            self._registers.clear()
            self._state_ready.clear()

            try:
                await self._open_socket()
                auth_response = await self._request(
                    {
                        "type": "backend",
                        "data": {
                            "type": "auth",
                            "cmd": "loginWithPin",
                            "serialnumber": self._serial_number,
                            "pin": self._pin,
                        },
                    }
                )
                auth_data = auth_response.get("data")
                if not isinstance(auth_data, dict) or not auth_data.get("mac"):
                    raise EnerventAuthError("The server did not identify the unit")
                self._device_id = str(auth_data["mac"])
                self._authenticated = True

                await self._request(
                    {
                        "type": "ucp",
                        "data": {"type": "command", "command": "model"},
                    }
                )
                await self._async_request_dump()
            except EnerventApiError:
                await self._close_socket()
                raise
            except asyncio.CancelledError:
                await self._close_socket()
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
                await self._close_socket()
                raise EnerventConnectionError(
                    "Unable to connect to the Enervent cloud"
                ) from err

    async def login(self) -> None:
        """Authenticate the client and establish a live session."""
        await self.async_login()

    async def async_get_status(self) -> dict[int, int | float]:
        """Return the latest register snapshot, reconnecting if needed."""
        if not self._is_connected or not self._authenticated:
            await self.async_login()
        else:
            await self._async_request_dump()
        return dict(self._registers)

    async def async_set_temperature(self, temperature: float) -> None:
        """Set the supply-air temperature setpoint in degrees Celsius."""
        minimum = float(self._registers.get(REGISTER_MIN_TEMP, _TEMPERATURE_MIN))
        maximum = float(self._registers.get(REGISTER_MAX_TEMP, _TEMPERATURE_MAX))
        if not minimum <= temperature <= maximum:
            raise EnerventApiError(
                f"Temperature must be between {minimum:g} and "
                f"{maximum:g} °C"
            )
        await self._async_write_register(
            REGISTER_TARGET_TEMP, round(temperature * _TEMPERATURE_SCALE)
        )

    async def async_set_mode(self, mode: str) -> None:
        """Apply a supported operating preset."""
        if mode not in PRESET_WRITES:
            raise EnerventApiError(f"Unsupported operating mode: {mode}")

        async with self._write_lock:
            for register, value in PRESET_WRITES[mode].items():
                await self._async_write_register_unlocked(register, value)

    async def async_set_fan_speed(self, percentage: float) -> None:
        """Set the legacy shared fan-speed override in percent."""
        if not 20 <= percentage <= 100:
            raise EnerventApiError("Fan speed must be between 20 and 100 percent")
        await self._async_write_register(
            REGISTER_FAN_SPEED_OVERRIDE, round(percentage)
        )

    async def async_set_switch(self, register: int, enabled: bool) -> None:
        """Set one supported binary override."""
        await self._async_write_register(register, int(enabled))

    async def async_close(self) -> None:
        """Close the active cloud connection."""
        self._closing = True
        await self._close_socket()

    @property
    def _is_connected(self) -> bool:
        return (
            self._ws is not None
            and not self._ws.closed
            and self._reader_task is not None
            and not self._reader_task.done()
        )

    async def _open_socket(self) -> None:
        """Perform Engine.IO polling handshake and WebSocket upgrade."""
        params = {
            "EIO": _ENGINE_IO_VERSION,
            "transport": "polling",
        }
        url = f"{API_URL}{_SOCKET_PATH}?{urlencode(params)}"
        timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)

        async with self._session.get(url, timeout=timeout) as response:
            if response.status != 200:
                raise EnerventConnectionError(
                    f"Socket.IO handshake returned HTTP {response.status}"
                )
            packet = await response.text()
        if not packet.startswith("0"):
            raise EnerventConnectionError("Invalid Engine.IO handshake")
        try:
            handshake = json.loads(packet[1:])
            sid = handshake["sid"]
        except (json.JSONDecodeError, KeyError, TypeError) as err:
            raise EnerventConnectionError(
                "Invalid Engine.IO handshake payload"
            ) from err

        polling_url = f"{url}&sid={sid}"
        async with self._session.post(
            polling_url,
            data="40",
            headers={"Content-Type": "text/plain;charset=UTF-8"},
            timeout=timeout,
        ) as response:
            if response.status != 200:
                raise EnerventConnectionError(
                    f"Socket.IO connect returned HTTP {response.status}"
                )
            await response.read()
        async with self._session.get(polling_url, timeout=timeout) as response:
            if response.status != 200:
                raise EnerventConnectionError(
                    f"Socket.IO polling returned HTTP {response.status}"
                )
            connect_packet = await response.text()
        if not connect_packet.startswith("40"):
            raise EnerventConnectionError("Socket.IO namespace connection failed")

        ws_params = urlencode(
            {"EIO": _ENGINE_IO_VERSION, "transport": "websocket", "sid": sid}
        )
        ws_url = f"{API_URL}{_SOCKET_PATH}?{ws_params}"
        self._ws = await self._session.ws_connect(
            ws_url,
            timeout=API_TIMEOUT,
            autoping=False,
            heartbeat=None,
        )
        await self._ws.send_str("2probe")
        probe = await asyncio.wait_for(self._ws.receive(), timeout=API_TIMEOUT)
        if probe.type != aiohttp.WSMsgType.TEXT or probe.data != "3probe":
            raise EnerventConnectionError("Socket.IO WebSocket upgrade failed")
        await self._ws.send_str("5")
        self._reader_task = asyncio.create_task(self._async_read_messages())

    async def _request(self, message: dict[str, Any]) -> dict[str, Any]:
        """Send one Socket.IO message and await its acknowledgement."""
        ws = self._ws
        if ws is None or ws.closed:
            raise EnerventConnectionError("Socket.IO connection is closed")

        request_id = self._next_id
        self._next_id += 1
        message["_id"] = request_id
        future: asyncio.Future[dict[str, Any]] = (
            asyncio.get_running_loop().create_future()
        )
        self._pending[request_id] = future

        try:
            await ws.send_str(
                "42"
                + json.dumps(
                    [_EVENT_NAME, json.dumps(message, separators=(",", ":"))],
                    separators=(",", ":"),
                )
            )
            response = await asyncio.wait_for(future, timeout=API_TIMEOUT)
        except asyncio.TimeoutError as err:
            raise EnerventConnectionError(
                "Timed out waiting for an Enervent response"
            ) from err
        except aiohttp.ClientError as err:
            raise EnerventConnectionError(
                "Unable to send an Enervent command"
            ) from err
        finally:
            self._pending.pop(request_id, None)

        if response.get("status") not in (None, "success"):
            if message.get("type") == "backend":
                raise EnerventAuthError("The serial number or PIN was rejected")
            raise EnerventApiError("The Enervent unit rejected the command")
        return response

    async def _async_write_register(self, register: int, value: int) -> None:
        """Write a register while serializing multi-register operations."""
        async with self._write_lock:
            await self._async_write_register_unlocked(register, value)

    async def _async_request_dump(self) -> None:
        """Request a full register snapshot from the authenticated unit."""
        if self._device_id is None:
            raise EnerventConnectionError("The unit is not authenticated")
        self._state_ready.clear()
        await self._request(
            {
                "type": "ucp",
                "dst": self._device_id,
                "data": {"type": "command", "command": "dump"},
            }
        )
        try:
            await asyncio.wait_for(self._state_ready.wait(), timeout=API_TIMEOUT)
        except asyncio.TimeoutError as err:
            raise EnerventConnectionError(
                "Timed out waiting for unit status"
            ) from err

    async def _async_write_register_unlocked(
        self, register: int, value: int
    ) -> None:
        if not self._is_connected or not self._authenticated:
            await self.async_login()
        if self._device_id is None:
            raise EnerventConnectionError("The unit is not authenticated")
        await self._request(
            {
                "type": "ucp",
                "dst": self._device_id,
                "data": {
                    "type": "command",
                    "command": "write",
                    "id": register,
                    "value": value,
                },
            }
        )

    async def _async_read_messages(self) -> None:
        """Receive server events, update registers, and resolve requests."""
        ws = self._ws
        if ws is None:
            return
        try:
            async for message in ws:
                if message.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_packet(message.data)
                elif message.type in (
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.ERROR,
                ):
                    break
        except aiohttp.ClientError:
            if not self._closing:
                _LOGGER.warning("Connection to the Enervent cloud was lost")
        except asyncio.CancelledError:
            if not self._closing:
                raise
        finally:
            if not self._closing:
                self._authenticated = False
                for future in self._pending.values():
                    if not future.done():
                        future.set_exception(
                            EnerventConnectionError("Socket.IO connection closed")
                        )
                self._pending.clear()

    async def _handle_packet(self, packet: str) -> None:
        """Handle Engine.IO and Socket.IO packets."""
        if packet == "2":
            if self._ws is not None and not self._ws.closed:
                await self._ws.send_str("3")
            return
        if not packet.startswith("42"):
            return

        try:
            event = json.loads(packet[2:])
            if (
                not isinstance(event, list)
                or len(event) < 2
                or event[0] != _EVENT_NAME
                or not isinstance(event[1], str)
            ):
                return
            message = json.loads(event[1])
        except (json.JSONDecodeError, TypeError):
            _LOGGER.debug("Ignoring an unrecognized Enervent Socket.IO message")
            return

        if not isinstance(message, dict):
            return

        if message.get("type") == "ucp":
            self._merge_message_data(message.get("data"))

        ack = message.get("_ack")
        future = self._pending.pop(ack, None) if isinstance(ack, int) else None
        if future is not None and not future.done():
            future.set_result(message)

    def _merge_message_data(self, data: Any) -> None:
        """Merge snapshots and register-change notifications."""
        if isinstance(data, list):
            for item in data:
                self._merge_register_mapping(item)
            return
        if not isinstance(data, dict):
            return

        if data.get("type") == "changes":
            registers = data.get("registers")
            values = data.get("data")
            if isinstance(registers, list) and isinstance(values, list):
                for register, value in zip(registers, values, strict=False):
                    self._store_register(register, value)
            return

        if "model" in data:
            return

        snapshot = data.get("data", data)
        if isinstance(snapshot, list):
            for item in snapshot:
                self._merge_register_mapping(item)
        else:
            self._merge_register_mapping(snapshot)

    def _merge_register_mapping(self, mapping: Any) -> None:
        if not isinstance(mapping, dict):
            return
        for register, value in mapping.items():
            self._store_register(register, value)

    def _store_register(self, register: Any, value: Any) -> None:
        try:
            register_id = int(register)
        except (TypeError, ValueError):
            return
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            self._registers[register_id] = value
            self._state_ready.set()

    async def _close_socket(self) -> None:
        """Close the WebSocket and cancel its reader."""
        reader = self._reader_task
        self._reader_task = None
        if reader is not None and reader is not asyncio.current_task():
            reader.cancel()
            try:
                await reader
            except asyncio.CancelledError:
                pass
        ws = self._ws
        self._ws = None
        self._authenticated = False
        if ws is not None and not ws.closed:
            await ws.close()
