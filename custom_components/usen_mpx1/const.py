"""Constants for the USEN MPX-1 integration."""

from datetime import timedelta

DOMAIN = "usen_mpx1"
MANUFACTURER = "USEN"
MODEL = "MPX-1"

SCAN_INTERVAL = timedelta(seconds=10)
# The preset list rarely changes; re-read it every N status polls.
PRESET_REFRESH_POLLS = 60

SOURCE_AUX = "AUX"

SERVICE_PLAY_CUE = "play_cue"
SERVICE_STOP_CUE = "stop_cue"

CONF_ARTWORK = "artwork"
DEFAULT_ARTWORK = True
