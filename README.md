# Enervent eAir for Home Assistant

Custom Home Assistant integration for Enervent eAir ventilation units using
the Enervent cloud service.

## Install with HACS

1. In Home Assistant, open **HACS**.
2. Open the **⋮** menu and choose **Custom repositories**.
3. Add `https://github.com/EAasen/enervent-eair` and select **Integration**.
4. Select **Add**, find **Enervent eAir** in HACS, and install it.
5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration**, search for
   **Enervent eAir**, then enter the unit's serial number and cloud PIN.

The repository must be accessible to HACS. For the standard HACS setup, make
the GitHub repository public. A private repository requires a Home Assistant
and HACS setup that can access it.

## Local installation

Copy `custom_components/enervent_eair` into the Home Assistant configuration
directory's `custom_components` folder, restart Home Assistant, and add
**Enervent eAir** from **Settings → Devices & services**.

## Entities

- A climate entity for supply-air temperature and supported operating presets.
- An **Operating mode** select: Home, Away, Away long, Boost, Overpressure.
- Sensors for captured temperatures, fan percentages, humidity, filter
  pressure, heat-recovery efficiency, and the service reminder.
- Binary sensors for alarm A, alarm B, HRC defrosting, and active time program.
- Switches for manual boost, overpressure, Away, Away long, and silent mode.

### Settings (0.1.4)

These appear under the device's **Configuration** section. The device must
report the setting before it can be changed.

| Area | Entities |
|---|---|
| Defrost | Heat recovery defrosting (switch) |
| Winter | Winter boost limit temperature, Summer/winter limit temperature |
| Summer night cooling | On/off; active cooling blocked; start, stop, and lowest outdoor temperature; min temperature difference; supply/extract air %; start/stop hour; one switch per weekday |
| Humidity boost | On/off, limit value % RH, 48 h threshold % RH |
| CO₂ boost | On/off, limit value ppm |
| Temperature boost | On/off, measurement select (extract air / room average) |
| Away / Boost / Overpressure / Silent | Fan speeds, Away temperature drops, overpressure and silent durations |

**System info** (diagnostic sensors): software version, hardware version,
unit family, heat recovery type, heater type, cooling unit type, and a
**Weekly time programs** sensor. It shows the number of active slots, and
its `programs` attribute lists them.

### Weekly time programs

The unit has 20 weekly program slots. Edit them with services, for example in
**Developer tools → Actions**:

```yaml
action: enervent_eair.set_week_program
data:
  slot: 1
  weekdays: [mon, tue, wed, thu, fri]
  start: "08:00"
  stop: "16:00"
  action: Away   # Away, Boost, Temperature drop, Max heating, ...
```

```yaml
action: enervent_eair.clear_week_program
data:
  slot: 1
```

Settings and program writes use the same generic register write as the
Enervent web app. The register numbers, scales, and limits come from the
unit's own model data. However, most of these setting writes were not
captured, so check the result in the Enervent app the first time. A write that
the unit does not confirm is reported as an error in Home Assistant.

The integration uses the observed serial-number/PIN login flow and the cloud
Socket.IO connection. It does not provide a username/password login. Some
features (including filter-dirty status, Fireplace mode, and post-heater
state) are not exposed because their mappings were not established from the
capture. See [the API specification](enervent_api_specification.md) for the
captured protocol, register mappings, and evidence notes.


## Support

### Very large temperatures or repeated status timeouts

Update to **0.1.3 or later** in HACS and restart Home Assistant.

- **Large temperature values:** Values such as `6517.4 °C` came from
  negative temperatures being read as unsigned numbers. Version 0.1.3
  decodes signed `int16` registers from the device model. For example, a raw
  value of `65174` is now shown as `-36.2 °C`. A constant value around
  `-36 °C` usually means that the sensor is not connected or not used on
  that unit.
- **`Timed out waiting for the device status stream`:** Earlier versions
  requested a full device dump on every poll. The cloud sends a full dump
  only once, then sends changes only, so those requests timed out. Version
  0.1.3 does what the Enervent web app does: each poll sends the live-view
  keepalive (register 799) and uses the live register stream. If the
  keepalive is not acknowledged, or if the stream is silent for 3 minutes,
  the integration reconnects within the same poll.

### `ClientConnectorCertificateError` during setup

Update to **0.1.2 or later** in HACS, restart Home Assistant, and retry setup.
On 2026-10-24 the Enervent cloud server was found to omit its intermediate
certificate. Version 0.1.2 bundles the public **ZeroSSL RSA DV SSL CA 2**
intermediate so that HTTPS polling and WebSocket connections can build a
complete certificate chain.

Certificate verification remains enabled: the cloud hostname, certificate
validity, and chain to a locally trusted root must still pass validation.
The integration does not trust the intermediate as a standalone root and
does not disable SSL verification or modify Home Assistant's global trust
store. Only the Enervent client's requests use the supplied chain.

If a certificate error persists, check Home Assistant's system clock and
install available Home Assistant updates (including its CA trust store).
The logs include the certificate validation reason, without credentials.
Do not use an insecure SSL bypass.

### Setup reports `cannot_connect`

If you installed version 0.1.0, update to **0.1.1 or later** in HACS and
restart Home Assistant before trying to add the integration again. Version
0.1.1 fixes device routing and status-stream handling during setup.

To update, open **HACS → Enervent eAir** and select **Update** if offered.
If no update appears, use the repository's **⋮ → Redownload** action and
select the latest version, then restart Home Assistant.

If setup still fails, go to **Settings → System → Logs**, find an entry
from `custom_components.enervent_eair`, and include its
`Enervent setup failed` message when reporting the problem. The message
identifies whether the failure happened during the Socket.IO handshake,
authentication, model request, or device status stream. Do not share your
serial number or PIN. Also check whether the unit is online in the Enervent
web portal.

Please include your Home Assistant version and relevant redacted logs when
reporting a problem. Never include your serial number, PIN, session IDs, or
unredacted network captures.
