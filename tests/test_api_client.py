"""Exercise the HAR-derived protocol against a real local Socket.IO peer."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import ssl
import sys
import types
import unittest
from unittest.mock import patch

import aiohttp
from aiohttp import web

# Load the standalone client without importing Home Assistant's package setup.
PACKAGE = "_enervent_protocol_test"
COMPONENT = (
    Path(__file__).resolve().parents[1] / "custom_components" / "enervent_eair"
)
package = types.ModuleType(PACKAGE)
package.__path__ = [str(COMPONENT)]
sys.modules[PACKAGE] = package
spec = importlib.util.spec_from_file_location(
    f"{PACKAGE}.api_client", COMPONENT / "api_client.py"
)
api = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = api
spec.loader.exec_module(api)


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    """The peer requires device routing and never acknowledges dump requests."""

    async def asyncSetUp(self) -> None:
        self.sent: list[dict] = []
        self.reject_auth = False
        self.respond_to_model = True
        self.respond_to_dump = True
        self.confirm_writes = True
        self.model_destination = None
        self.dump_count = 0
        self.keepalive_count = 0
        self.respond_to_keepalive = True
        self.pending_changes: dict[int, int] = {}
        self.pong_received = asyncio.Event()
        self.registers = {
            8: 205,
            44: 0,
            135: 215,
            140: 15,
            141: 25,
            10001: 0,
            10002: 0,
            10003: 0,
            10010: 0,
        }
        application = web.Application()
        application.router.add_route("*", "/socket.io/", self.handle)
        self.runner = web.AppRunner(application)
        await self.runner.setup()
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        self.url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        await web.SockSite(self.runner, listener).start()
        self.session = aiohttp.ClientSession()
        self.client = api.EnerventApiClient(
            self.session, "test-serial", "test-pin"
        )
        self.url_patch = patch.object(api, "API_URL", self.url)
        self.timeout_patch = patch.object(api, "API_TIMEOUT", 0.5)
        self.url_patch.start()
        self.timeout_patch.start()

    async def asyncTearDown(self) -> None:
        await self.client.async_close()
        await self.session.close()
        await self.runner.cleanup()
        self.timeout_patch.stop()
        self.url_patch.stop()

    async def handle(self, request: web.Request) -> web.StreamResponse:
        if request.query.get("transport") == "websocket":
            return await self.websocket(request)
        if request.method == "POST":
            self.assertEqual(await request.text(), "40")
            return web.Response(text="ok")
        if "sid" in request.query:
            return web.Response(text='40{"sid":"test-namespace"}')
        return web.Response(
            text="0"
            + json.dumps(
                {
                    "sid": "test-engine",
                    "upgrades": ["websocket"],
                    "pingInterval": 25000,
                    "pingTimeout": 20000,
                    "maxPayload": 1000000,
                }
            )
        )

    async def send(self, ws: web.WebSocketResponse, message: dict) -> None:
        await ws.send_str("42" + json.dumps(["message", json.dumps(message)]))

    async def changes(
        self, ws: web.WebSocketResponse, registers: dict
    ) -> None:
        await self.send(
            ws,
            {
                "type": "ucp",
                "src": "test-device",
                "data": {
                    "type": "changes",
                    "registers": list(registers),
                    "data": list(registers.values()),
                },
            },
        )

    async def websocket(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for frame in ws:
            if frame.type != aiohttp.WSMsgType.TEXT:
                continue
            if frame.data == "2probe":
                await ws.send_str("3probe")
                continue
            if frame.data == "5":
                await ws.send_str("2")
                continue
            if frame.data == "3":
                self.pong_received.set()
                continue
            if not frame.data.startswith("42"):
                continue
            event = json.loads(frame.data[2:])
            self.assertEqual(event[0], "message")
            self.assertIsInstance(event[1], str)
            message = json.loads(event[1])
            self.sent.append(message)
            data = message["data"]
            if message["type"] == "backend":
                self.assertEqual(data["serialnumber"], "test-serial")
                self.assertEqual(data["pin"], "test-pin")
                await self.send(
                    ws,
                    {
                        "type": "backend",
                        "_ack": message["_id"],
                        "status": "error" if self.reject_auth else "success",
                        "sessid": None,
                        "data": {"mac": "test-device"},
                    },
                )
            elif data["command"] == "model":
                self.model_destination = message.get("dst")
                if (
                    self.respond_to_model
                    and self.model_destination == "test-device"
                ):
                    await self.send(
                        ws,
                        {
                            "type": "ucp",
                            "_ack": message["_id"],
                            "status": "success",
                            "data": {"model": {"items": []}},
                        },
                    )
            elif data["command"] == "dump":
                self.dump_count += 1
                self.assertEqual(message["dst"], "test-device")
                self.assertEqual(data.get("device"), "test-device")
                await self.changes(ws, {753: 1})
                if self.respond_to_dump:
                    await self.changes(ws, {8: self.registers[8]})
                    await self.changes(
                        ws, {k: v for k, v in self.registers.items() if k != 8}
                    )
            elif data["command"] == "write" and data["id"] == 799:
                self.keepalive_count += 1
                if self.respond_to_keepalive:
                    # HAR frame: the live-view write is acked with a change.
                    await self.send(
                        ws,
                        {
                            "type": "ucp",
                            "src": "test-device",
                            "_ack": message["_id"],
                            "data": {
                                "type": "changes",
                                "registers": [799],
                                "data": [1],
                            },
                        },
                    )
                    for register, value in self.pending_changes.items():
                        self.registers[register] = value
                    if self.pending_changes:
                        await self.changes(ws, self.pending_changes)
                    self.pending_changes = {}
            elif data["command"] == "write":
                self.registers[data["id"]] = data["value"]
                # The capture confirms control writes by unacked changes.
                if self.confirm_writes:
                    await self.changes(ws, {data["id"]: data["value"]})
        return ws

    async def test_login_routes_model_and_accepts_unacked_dump(self) -> None:
        await self.client.login()
        self.assertEqual(self.model_destination, "test-device")
        self.assertEqual(self.client.device_id, "test-device")
        self.assertEqual(self.client._registers[135], 215)
        self.assertEqual(self.dump_count, 1)
        self.assertFalse(self.client._pending)
        await asyncio.wait_for(self.pong_received.wait(), timeout=1)

    async def test_all_handshake_requests_use_the_verified_context(self) -> None:
        with (
            patch.object(
                self.session, "get", wraps=self.session.get
            ) as get,
            patch.object(
                self.session, "post", wraps=self.session.post
            ) as post,
            patch.object(
                self.session, "ws_connect", wraps=self.session.ws_connect
            ) as ws_connect,
        ):
            await self.client.login()
        self.assertEqual(get.call_count, 2)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(ws_connect.call_count, 1)
        for call in [*get.call_args_list, *post.call_args_list,
                     *ws_connect.call_args_list]:
            self.assertIs(call.kwargs["ssl"], self.client._ssl_context)
            self.assertTrue(call.kwargs["ssl"].check_hostname)
            self.assertEqual(call.kwargs["ssl"].verify_mode, ssl.CERT_REQUIRED)

    async def test_bad_certificate_fails_before_credentials_are_sent(self) -> None:
        connection = types.SimpleNamespace(
            host="my.enervent.com", port=443, is_ssl=True
        )
        error = aiohttp.ClientConnectorCertificateError(
            connection, ssl.SSLCertVerificationError(1, "Untrusted issuer")
        )
        with patch.object(self.client, "_open_socket", side_effect=error):
            with self.assertRaisesRegex(
                api.EnerventCertificateError, "TLS certificate validation failed"
            ):
                await self.client.login()
        self.assertFalse(self.sent)
        self.assertIsNone(self.client._ws)

    async def test_signed_setting_write_uses_twos_complement(self) -> None:
        await self.client.login()
        await self.client.async_write_register(157, -50)
        write = [m for m in self.sent if m["data"].get("id") == 157][-1]
        self.assertEqual(write["data"]["value"], 65486)
        self.assertEqual(self.client.registers[157], -50)

    async def test_bit_write_keeps_other_weekdays(self) -> None:
        self.registers[97] = 127
        await self.client.login()
        await self.client.async_set_bit(97, 4, False)
        self.assertEqual(self.client.registers[97], 123)
        await self.client.async_set_bit(97, 4, True)
        self.assertEqual(self.client.registers[97], 127)

    async def test_week_program_write_and_read(self) -> None:
        for register in range(216, 222):
            self.registers[register] = 0
        await self.client.login()
        await self.client.async_set_week_program(2, 0b0111110, 7, 30, 16, 0, 1)
        self.assertEqual(
            self.client.get_week_program(2),
            {
                "slot": 2,
                "weekdays": 62,
                "start_hour": 7,
                "start_minute": 30,
                "stop_hour": 16,
                "stop_minute": 0,
                "action": 1,
            },
        )
        ids = [m["data"]["id"] for m in self.sent if m["data"].get("command") == "write"]
        self.assertEqual(ids[-1], 221)
        with self.assertRaises(api.EnerventApiError):
            await self.client.async_set_week_program(21, 1, 0, 0, 1, 0, 1)
        with self.assertRaises(api.EnerventApiError):
            await self.client.async_set_week_program(1, 1, 0, 0, 1, 0, 2)

    async def test_polling_keeps_stream_alive_without_new_dump(self) -> None:
        await self.client.login()
        self.pending_changes = {8: 220}
        status = await self.client.async_get_status()
        await asyncio.sleep(0.05)
        status = await self.client.async_get_status()
        self.assertEqual(status[8], 220)
        self.assertEqual(self.dump_count, 1)
        self.assertEqual(self.keepalive_count, 2)
        auth_requests = [m for m in self.sent if m["type"] == "backend"]
        self.assertEqual(len(auth_requests), 1)

    async def test_missing_keepalive_ack_reconnects_within_same_poll(self) -> None:
        await self.client.login()
        self.respond_to_keepalive = False
        status = await self.client.async_get_status()
        self.assertEqual(status[135], 215)
        auth_requests = [m for m in self.sent if m["type"] == "backend"]
        self.assertEqual(len(auth_requests), 2)
        self.assertEqual(self.dump_count, 2)

    async def test_stale_stream_reconnects(self) -> None:
        await self.client.login()
        self.client._last_device_message -= api.STREAM_STALE_TIMEOUT + 1
        await self.client.async_get_status()
        self.assertEqual(self.keepalive_count, 0)
        self.assertEqual(self.dump_count, 2)

    async def test_poll_reports_error_when_reconnect_fails(self) -> None:
        await self.client.login()
        self.respond_to_keepalive = False
        self.respond_to_dump = False
        with self.assertRaises(api.EnerventConnectionError):
            await self.client.async_get_status()
        self.assertIsNone(self.client._ws)
        self.respond_to_dump = True
        status = await self.client.async_get_status()
        self.assertEqual(status[135], 215)

    async def test_signed_int16_registers_are_decoded(self) -> None:
        self.registers[11] = 65174
        self.registers[46] = 65535
        self.registers[53] = 65000
        await self.client.login()
        self.assertEqual(self.client._registers[11], -362)
        self.assertEqual(self.client._registers[46], -1)
        self.assertEqual(self.client._registers[53], 65000)

    async def test_model_types_control_signed_decoding(self) -> None:
        self.client._load_model(
            {
                "data": {
                    "model": {
                        "items": [
                            {"mbreg": 900, "type": "int16"},
                            {"mbreg": 901, "type": "uint16"},
                        ]
                    }
                }
            }
        )
        self.client._store_register(900, 65534)
        self.client._store_register(901, 65534)
        self.client._store_register(11, 65174)
        self.assertEqual(self.client._registers[900], -2)
        self.assertEqual(self.client._registers[901], 65534)
        self.assertEqual(self.client._registers[11], -362)

    async def test_rejected_credentials_are_auth_error(self) -> None:
        self.reject_auth = True
        with self.assertRaises(api.EnerventAuthError):
            await self.client.login()
        self.assertIsNone(self.client._ws)
        self.assertIsNone(self.client._reader_task)

    async def test_model_timeout_identifies_stage(self) -> None:
        self.respond_to_model = False
        with self.assertRaisesRegex(
            api.EnerventConnectionError, "device model request"
        ):
            await self.client.login()
        self.assertIsNone(self.client._ws)

    async def test_ping_register_cannot_count_as_device_status(self) -> None:
        self.respond_to_dump = False
        with self.assertRaisesRegex(
            api.EnerventConnectionError, "device status stream"
        ):
            await self.client.login()
        self.assertFalse(self.client._pending)

    async def test_controls_accept_unacked_register_confirmation(self) -> None:
        await self.client.login()
        await self.client.async_set_temperature(22)
        await self.client.async_set_mode("Away")
        self.assertEqual(self.client._registers[135], 220)
        self.assertEqual(self.client._registers[10001], 1)
        writes = [m for m in self.sent if m["data"].get("command") == "write"]
        self.assertEqual(len(writes), 2)
        self.assertFalse(self.client._pending)

    async def test_temperature_respects_unit_bounds(self) -> None:
        await self.client.login()
        with self.assertRaises(api.EnerventApiError):
            await self.client.async_set_temperature(26)

    async def test_unconfirmed_write_reports_failure(self) -> None:
        await self.client.login()
        self.confirm_writes = False
        with self.assertRaisesRegex(
            api.EnerventConnectionError, "register write confirmation"
        ):
            await self.client.async_set_temperature(22)
        self.assertFalse(self.client._pending)
        self.assertFalse(self.client._write_confirmations)

    async def test_malformed_changes_are_an_explicit_protocol_error(self) -> None:
        await self.client.login()
        packet = "42" + json.dumps(
            [
                "message",
                json.dumps(
                    {
                        "type": "ucp",
                        "src": "test-device",
                        "data": {
                            "type": "changes",
                            "registers": [8, 135],
                            "data": [220],
                        },
                    }
                ),
            ]
        )
        with self.assertRaisesRegex(
            api.EnerventConnectionError, "Invalid device register update"
        ):
            await self.client._handle_packet(packet)


class CertificateContextTests(unittest.TestCase):
    """Keep the intermediate as a chain aid, never an independent trust root."""

    def test_context_requires_hostname_and_a_trusted_root(self) -> None:
        context = api._create_ssl_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertFalse(context.verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN)
        fingerprints = {
            hashlib.sha256(der).hexdigest()
            for der in context.get_ca_certs(binary_form=True)
        }
        self.assertIn(
            "ec9d6bcab9818b7dd59ed61da23a658a96a9c4e950edee0d2da93e7cf2174780",
            fingerprints,
        )


if __name__ == "__main__":
    unittest.main()
