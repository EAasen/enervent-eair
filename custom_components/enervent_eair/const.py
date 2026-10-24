"""Constants for the Enervent eAir integration."""

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
REGISTER_KEEPALIVE = 799
STREAM_STALE_TIMEOUT = 180
# int16 registers from the captured eAir model; used if the model lacks types.
SIGNED_REGISTERS = frozenset(
    {
        1, 2, 6, 7, 8, 9, 10, 11, 12, 16, 31, 32, 33, 46, 47, 48, 49, 93, 94,
        95, 96, 101, 103, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131,
        132, 133, 134, 135, 137, 138, 139, 145, 157, 159, 160, 164, 170, 172,
        173, 174, 177, 178, 196, 591, 592, 593, 601, 626, 627, 628, 629, 630,
        633, 694, 695, 696, 697, 700, 716,
    }
)

# Weekly time programs WC1..WC20: six registers each, starting at 210:
# weekday mask (Sun=1 .. Sat=64), start hour, start minute, stop hour,
# stop minute, action (model enumeration "actions").
WEEK_PROGRAM_FIRST_REGISTER = 210
WEEK_PROGRAM_SLOTS = 20
WEEK_PROGRAM_ACTIONS = {
    0: "No action",
    1: "Away",
    3: "Heating forbidden",
    4: "Cooling forbidden",
    5: "Temperature drop",
    6: "Max heating",
    7: "Max cooling",
    16: "Time relay",
    17: "Boost",
    18: "Circulation air",
    30: "Run time",
}
WEEKDAY_BITS = {
    "sun": 1,
    "mon": 2,
    "tue": 4,
    "wed": 8,
    "thu": 16,
    "fri": 32,
    "sat": 64,
}

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
