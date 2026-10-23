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
- Sensors for captured temperatures, fan percentages, humidity, filter
  pressure, heat-recovery efficiency, and the service reminder.
- Binary sensors for alarm A, alarm B, and HRC defrosting.
- Switches for manual boost and overpressure mode.

The integration uses the observed serial-number/PIN login flow and the cloud
Socket.IO connection. It does not provide a username/password login. Some
features (including CO₂, filter-dirty status, Fireplace mode, and post-heater
state) are not exposed because their mappings were not established from the
capture. See [the API specification](enervent_api_specification.md) for the
captured protocol, register mappings, and evidence notes.

## Credentials and capture files

The serial number and PIN belong in the Home Assistant integration setup,
not in source files, documentation, issues, or screenshots. The original HAR
capture is intentionally not included in this repository: it may contain
authentication data and session identifiers. HAR files and common local
secret files are excluded by `.gitignore`.

## Support

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
