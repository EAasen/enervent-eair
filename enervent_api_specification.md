# Enervent eAir Cloud API Specification

## Scope and evidence standard

This specification describes `my.enervent.com.har` (5,301,146 bytes; 103 HAR entries; capture window 2026-10-23 12:12:13Z–12:13:34Z). Static HTML/JavaScript/CSS/images/fonts and five unrelated third-party browser telemetry/extension requests are excluded from the endpoint catalog.

The REA network-capture MCP tool was not available in this session's tool catalog. The HAR was therefore inspected locally, preserving values that may identify the account, unit, session, or PIN as redacted. HAR entry numbers below are 1-based positions in `log.entries`; WebSocket frame numbers are 0-based positions in entry 15's `_webSocketMessages`. “Observed” means directly present in the capture; “inferred” means derived from the captured device model and generic write contract; “unknown” means the capture does not establish it.

The capture contains the web client's actual Socket.IO communication, not a conventional REST login/status API. An integration using guessed `/login`, `/status`, Bearer-token, or username/password routes would not match this evidence.

## Endpoint catalog

| URL / exchange | Method / protocol | Headers and payload | Response / status | Evidence |
|---|---|---|---|---|
| `https://my.enervent.com/socket.io/?EIO=4&transport=polling` | `GET` Engine.IO polling handshake | Standard browser `Accept`, `Origin`/`Referer` on later exchanges; no `Authorization` header observed. No body. | HTTP 200, Engine.IO open packet (`0{...}`) containing a connection `sid`, upgrade list, and ping settings. | Entry 7, 2026-10-23T12:12:13.448Z |
| Same Socket.IO polling URL with `sid` | `POST` | Text packet `40` to connect the default Socket.IO namespace. | HTTP 200; empty text response. | Entry 9, 2026-10-23T12:12:13.506Z |
| Same Socket.IO polling URL with `sid` | `GET` | No body. | HTTP 200; namespace-connect packet (`40{...}`). | Entries 10 and 13, 12:12:13.507Z and 12:12:13.543Z |
| `wss://my.enervent.com/socket.io/?EIO=4&transport=websocket&sid=…` | WebSocket upgrade | Engine.IO v4 upgrade; standard WebSocket `Upgrade`, `Connection`, `Sec-WebSocket-*`, and `Origin` headers. No session-cookie or `Authorization` header observed. | HTTP 101; Engine.IO ping/pong and Socket.IO `message` events. | Entry 15, 12:12:13.560Z |
| `message` Socket.IO event | Client → server | Event packet `42["message","<JSON string>"]`. Authentication body: `{"type":"backend","data":{"type":"auth","cmd":"loginWithPin","serialnumber":"…","pin":"…"},"_id":N}`. | Ack body has `type:"backend"`, `_ack:N`, `status:"success"`, `sessid:null`, and `data` containing `mac`, `login`, and `gdprConsent`. A rejection body/status was not captured. | Entry 15, frames 3–4 |
| `message` Socket.IO event: model and snapshot | Client → server | `{"type":"ucp","data":{"type":"command","command":"model"},"_id":N}` then `{"type":"ucp","dst":"<device mac>","data":{"type":"command","command":"dump"},"_id":N}`. | Acked UCP response; model has `model.items`, `model.enumerations`, `dynamic`, and `machineType`. Snapshot data is register-ID keyed. | Entry 15, frames 5–8; initial model observed in response and stream |
| `message` Socket.IO event: live updates | Server → client | UCP change packet with `data.type:"changes"`, `data.registers:[integer,…]`, and `data.data:[number,…]`; arrays correspond positionally. | WebSocket stream; values update incrementally. No HTTP status code applies. | Entry 15, 6,200 `changes` events; representative message shape captured throughout the connection |
| `message` Socket.IO event: register write | Client → server | `{"type":"ucp","dst":"<device mac>","data":{"type":"command","command":"write","id":<register id>,"value":<integer>},"_id":N}`. | UCP ack. Successful writes were observed for register IDs 799, 10003, 10010, 10047, and 10055. Register 799 is the device's ping register, not a user control. | Entry 15, frames 635–5975; see evidence ledger |
| `https://my.enervent.com/api` | `POST` | JSON body has `q` and `p`; observed `q` is `rmi.core.UI.translation`. Standard browser JSON request headers. | HTTP 200, JSON translation dictionaries, not device state. | Entry 57, 12:12:15.138Z |
| `https://my.enervent.com/logAll.tsv` | `GET` | Query parameters observed: `opt[device]`, `opt[socketId]`, `opt[dynamic]`, `opt[time]`. Values are account/device/session-specific and omitted here. | HTTP 200, `text/tab-separated-values`; historical log export. | Entry 97, 12:13:34.664Z |

No refresh-token endpoint, cookie-based session, CSRF flow, REST telemetry endpoint, or REST write endpoint appears in the captured exchanges. Session state is the live Engine.IO/Socket.IO connection; the auth ack's `sessid` was null. The serial number and PIN are sent only in the `loginWithPin` event. Re-authentication after a disconnect is expected, but token expiry/refresh semantics were not observed.

## Request and command schemas

### Response shapes

The following schemas omit volatile identifiers and payload values. Numeric register keys and the nested model vary by unit configuration.

```jsonc
// Engine.IO open packet payload (after leading "0")
{
  "sid": "string",
  "upgrades": ["websocket"],
  "pingInterval": "integer",
  "pingTimeout": "integer",
  "maxPayload": "integer"
}
```

```jsonc
// Authentication acknowledgement, inside a Socket.IO "message" event
{
  "type": "backend",
  "_ack": "integer",
  "status": "success",
  "sessid": null,
  "data": {
    "mac": "string",
    "login": "string",
    "gdprConsent": "integer"
  }
}
```

```jsonc
// UCP model response (model.items has 825 records in this capture)
{
  "type": "ucp",
  "_ack": "integer",
  "status": "success",
  "data": {
    "model": {
      "items": [{
        "desc": "string",
        "format": "string",
        "access": "string",
        "type": "string",
        "bounds": "string",
        "ref": "string",
        "note": "string",
        "symbol": "string",
        "mbreg": "string",
        "label": "string",
        "scale": "number"
      }],
      "enumerations": {"<enum name>": {"<value>": "enum metadata"}}
    },
    "dynamic": {"ai": {"<input id>": "unit-dependent metadata"}},
    "machineType": {
      "machinetype": "unit-dependent model",
      "actions": "action map",
      "web_measurments": "register map"
    }
  }
}
```

```jsonc
// Dump snapshot acknowledgement; keys are Modbus register IDs
{
  "type": "ucp",
  "_ack": "integer",
  "data": [{
    "<register id>": "number",
    "time": "number"
  }]
}
```

```jsonc
// Live register update, inside a Socket.IO "message" event
{
  "type": "ucp",
  "src": "device identifier",
  "data": {
    "type": "changes",
    "registers": ["integer"],
    "data": ["number"]
  }
}
```

The observed `/api` translation response is shaped as `{"status":"string","data":{"dict":{"<namespace>":{"<key>":"localized string"}},"timestamp":"integer"}}`; it contains UI strings, not appliance state.

### Authentication

```json
{
  "type": "backend",
  "data": {
    "type": "auth",
    "cmd": "loginWithPin",
    "serialnumber": "<unit serial number>",
    "pin": "<unit PIN>"
  },
  "_id": 1
}
```

The response's `data.mac` is used as the `dst` for unit-directed UCP commands. The ack also contains `login` and `gdprConsent`; no auth token is returned in the observed response.

### Snapshot and updates

The client first requests the model, then a device dump. The model's 825 item records provide labels, Modbus register identifiers (`mbreg`), data type, scale, bounds, and read/write metadata. The live stream delivers register changes as aligned ID/value arrays. For temperature registers, raw integers are tenths of a degree Celsius (divide by 10); humidity, pressure, fan percent, and efficiency use scale 1 as indicated by the model's format/scale fields.

### Writes

The observed generic write contract is one integer register ID and one integer value. The following user controls are backed by the captured model dictionary; only a subset of writes themselves occurred in the recording:

| Control | Register | Wire value | Evidence level |
|---|---:|---|---|
| Supply-air temperature setpoint (`HREG_T_SETPOINT`) | 135 | °C × 10; model bounds are 0–500 raw, with setpoint min/max registers 140/141 constrained to 10–35 °C | Register and scale are model-observed; writing this register is inferred from its `RW` metadata and generic writer |
| Legacy shared fan-speed override (`HREG_FANSPEED`) | 53 | 20–100 percent, integer | Register, bounds, and `RW` metadata observed; write was not captured |
| Away | 10001 (`COIL_AWAY`) | 0/1 | Mode/control mapping from model dictionary; direct write not present |
| Away long | 10002 (`COIL_AWAYL`) | 0/1 | Mode/control mapping from model dictionary; direct write not present |
| Overpressure override | 10003 (`COIL_OVP`) | 0/1 | Register definition observed; write observed |
| Manual boost | 10010 (`COIL_M_BOOST`) | 0/1 | Register definition observed; write observed |
| Silent mode | 10047 (`COIL_SILENT_MODE`) | 0/1 | Write observed; not surfaced by this integration |
| HRC defrost enable | 10055 (`COIL_LTO_DEFROST_EN`) | 0/1 | Write observed; this is an enable setting, not a proof of active defrost |

The supported Home preset clears the Away, Away-long, Manual-boost, and Overpressure coils; this is an integration policy built from those controls, not an observed single “Home” write. No Fireplace preset or fan-speed override write was captured. The model does list a legacy shared fan-speed override register (53); the client includes a bounded write method for it, but no UI entity is exposed until its behavior is confirmed on a unit.

## Data dictionary

“Register” is the `mbreg` value from the `model.items` record. Numeric values are decoded using that record's scale. Absent values must remain unavailable; do not treat missing registers as zero.

| Register / raw key | Model symbol / field | Standard unit | Description / handling |
|---:|---|---|---|
| 1 | `HREG_T_OP1` / Room temperature sensor TE20 | °C; raw ÷ 10 | Operator-panel room temperature 1 |
| 2 | `HREG_T_OP2` / Room temperature sensor TE21 | °C; raw ÷ 10 | Operator-panel room temperature 2 |
| 3 | `HREG_EFFECTIVE_TF` | % | Current effective supply fan speed |
| 4 | `HREG_EFFECTIVE_PF` | % | Current effective extract fan speed |
| 6 | `HREG_T_FRS` / Fresh air | °C; raw ÷ 10 | Outdoor/fresh-air sensor TE01 |
| 7 | `HREG_T_SPLY_LTO` | °C; raw ÷ 10 | Supply air after heat-recovery core |
| 8 | `HREG_T_SPLY` | °C; raw ÷ 10 | Room supply-air temperature, TE10 |
| 9 | `HREG_T_WST` | °C; raw ÷ 10 | Waste/exhaust-air temperature, TE32 |
| 10 | `HREG_T_EXT` | °C; raw ÷ 10 | Room removed/extract-air temperature, TE30 |
| 11 | `HREG_T_EXT_LTO` | °C; raw ÷ 10 | Removed air before heat recovery, TE31 |
| 12 | `HREG_T_WR` | °C; raw ÷ 10 | Return-water temperature, TE45 |
| 13 | `HREG_HUM_EXT` | % RH | Extract-air relative humidity, RH30 |
| 14 | `HREG_PRES_SPLYF` | Pa | Supply-side filter differential pressure |
| 15 | `HREG_PRES_EXTF` | Pa | Extract-side filter differential pressure |
| 29 | `HREG_LTO_N_SPLY` | % | Heat-recovery efficiency, supply side |
| 30 | `HREG_LTO_N_EXT` | % | Heat-recovery efficiency, extract side |
| 35 | `HREG_RH_MEAN` | % RH | 48-hour average relative humidity |
| 44 | `HREG_MODE` | bit mask / enum | Current operation/display state. The captured enum maps Home=0, Away=16, Away long=32, Manual boost=512, Overpressure=1024, HRC defrosting=32768, among other values. |
| 46 | `HREG_ROOM_TEMP` | °C; raw ÷ 10 | Average room temperature used by the climate entity |
| 53 | `HREG_FANSPEED` | % | Legacy shared fan-speed request; writable `RW`, model bounds 20–100 |
| 135 | `HREG_T_SETPOINT` | °C; raw ÷ 10 | Writable supply-air setpoint |
| 140–141 | `HREG_SP_MIN`, `HREG_SP_MAX` | °C | Configured minimum/maximum supply-air setpoint; model bounds are 10–35 °C |
| 385–386 | `HREG_ALARM1_ALMTYPE`, `HREG_ALARM1_STATECLASS` | enumeration / packed state | Newest alarm-log entry; not proven to be a live per-alarm flag |
| 538 | `HREG_ALARM_SERVICE_TIME` | days | Days until service reminder, not confirmed as a filter-life countdown |
| 10001–10003 | `COIL_AWAY`, `COIL_AWAYL`, `COIL_OVP` | Boolean-like integer | Away, Away long, and Overpressure mode controls |
| 10010 | `COIL_M_BOOST` | Boolean-like integer | Manual boost control |
| 10041–10042 | `COIL_ALARM_A`, `COIL_ALARM_B` | Boolean-like integer | Alarm class flags; binary `problem` entities |

There are no explicit `temp_supply`, `fan_pct`, CO₂, filter-dirty, or post-heater-active JSON keys in this API. The web model uses numeric Modbus register IDs. CO₂ can be an analog input, but its sensor function is configured per unit and the HAR does not establish which input is CO₂ or give a stable ppm register mapping. Fan RPM is not present; the captured fan telemetry is effective speed in percent.

## Home Assistant entity mapping

| Home Assistant platform | Entity / source | Mapping |
|---|---|---|
| `climate` | Enervent Ventilation | Target temperature: register 135 (°C); current supply-air temperature: register 8; HVAC mode is `auto`; presets Home, Away, Away long, Boost, Overpressure derived from register 44 and the writable coils above. |
| `sensor` | Temperature sensors | Registers 1, 2, 6–12, and 46; all °C after division by 10. |
| `sensor` | Fan speeds | Registers 3 and 4; percent. |
| `sensor` | Humidity | Registers 13 and 35; percent RH. |
| `sensor` | Filter pressure | Registers 14 and 15; Pa. |
| `sensor` | Heat recovery | Registers 29 and 30; percent efficiency. |
| `sensor` | Service reminder | Register 538; days until service reminder, not a filter timer. |
| `binary_sensor` | Alarm A / Alarm B | Registers 10041 / 10042; `problem`. |
| `binary_sensor` | HRC defrosting | Bit 32768 of register 44; `running`. This reports the mode state, not the defrost-enable setting. |
| `switch` | Manual boost / Overpressure | Registers 10010 / 10003. |
| `select` | None | No separate select entity; climate presets expose captured operating overrides. |
| Unsupported pending evidence | Dirty-filter alert, post-heater active, CO₂, Fireplace, fan override UI | The capture lacks a confirmed live field/register mapping or recorded control behavior; no guessed entities are exposed. The client does expose the model-derived legacy register 53 write. |

## Evidence ledger

| Claim | Provenance | Confidence |
|---|---|---|
| The cloud API is Socket.IO / Engine.IO v4, beginning with polling and upgrading to WebSocket | HAR entry 7 open packet; entries 9–13 namespace handshake/polling; entry 15 HTTP 101 | Observed |
| Authentication uses `loginWithPin` and `serialnumber`/`pin` fields | Entry 15, frame 3 | Observed |
| Auth ack returns `mac`, `login`, `gdprConsent`; `sessid` is null | Entry 15, frame 4 (values intentionally omitted) | Observed |
| Model and dump are requested with UCP `command:"model"` and `command:"dump"` | Entry 15, frames 5 and 7 | Observed |
| Device has a model containing 825 items and an enumeration dictionary | Entry 15, initial UCP model response; inspected field names and model metadata | Observed |
| State is a stream of register-ID/value arrays in `changes` messages | Entry 15, 6,200 `message` events of type `ucp`, data type `changes` | Observed |
| Generic register writes use UCP `command:"write"` with `id` and integer `value` | Entry 15, frames 635, 1123, 1777, 1798, 1817, 2330, 2404, 2494, 2497, 2498, 2499, 2509, 3182, 3884, 4590, 5281, 5975 | Observed |
| IDs 10003/10010/10047/10055 are the listed mode/setting registers | Entry 15's write frames plus matching `model.items[].mbreg`, symbol, label, and access fields | Observed |
| Registers 53 and 135 are writable fan-speed and supply-air setpoint controls | `model.items` records for `HREG_FANSPEED` and `HREG_T_SETPOINT`: `mbreg=53`/`135`, `access=RW`, fan bounds 20–100 and setpoint scale 10 | Observed model metadata; writes to these controls are inferred from the generic write contract |
| Registers 1–15, 29–30, 35, 44, 46, 538, 10041–10042 and their units/labels | Entry 15 model item `mbreg`, `symbol`, `label`, `desc`, `format`, `scale` fields | Observed model metadata |
| `/api` is not the telemetry path | Entry 57 request `q=rmi.core.UI.translation`, response is localization dictionary | Observed |
| `/logAll.tsv` is a historical log export | Entry 97 URL path, query-key names, HTTP 200 and TSV MIME type | Observed |
| A standalone refresh token, REST status endpoint, live dirty-filter flag, post-heater state, CO₂ mapping, Fireplace control, or fan override endpoint | Not present in the captured exchanges | Unknown / not supported |

## Integration implementation notes

`custom_components/enervent_eair/` implements the observed Engine.IO polling handshake, WebSocket upgrade, PIN auth event, model/dump requests, register stream merge, and generic integer register write. The coordinator requests a fresh register dump at the configured interval (default 30 seconds) while also accepting the server's live stream. If the socket is lost, the next status update re-authenticates and reloads the model and snapshot. Credentials are serial number and PIN because those are the captured auth fields.

The integration's Away/Home presets are an evidence-based register mapping, not a captured sequence of UI mode changes. They should be validated against the installed unit before relying on them for safety-critical ventilation behavior. No live request is made against the unit by this implementation during this analysis.
