"""Constants for the Enervent eAir integration."""

from homeassistant.const import Platform

DOMAIN = "enervent_eair"
API_URL = "https://my.enervent.com"

CONF_SERIAL_NUMBER = "serial_number"
CONF_PIN = "pin"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 300
API_TIMEOUT = 15

REGISTER_SUPPLY_TEMP = 8
REGISTER_TARGET_TEMP = 135
REGISTER_MODE = 44
REGISTER_MIN_TEMP = 140
REGISTER_MAX_TEMP = 141
REGISTER_FAN_SPEED_OVERRIDE = 53

MODE_PRESETS = {
    "Home": 0,
    "Away": 16,
    "Away long": 32,
    "Boost": 512,
    "Overpressure": 1024,
}

PRESET_WRITES = {
    "Home": {10001: 0, 10002: 0, 10010: 0, 10003: 0},
    "Away": {10001: 1, 10002: 0, 10010: 0, 10003: 0},
    "Away long": {10001: 0, 10002: 1, 10010: 0, 10003: 0},
    "Boost": {10001: 0, 10002: 0, 10010: 1, 10003: 0},
    "Overpressure": {10001: 0, 10002: 0, 10010: 0, 10003: 1},
}

PLATFORMS = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
]
