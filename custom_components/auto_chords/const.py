"""Constants for Auto Chords."""

from homeassistant.const import Platform

DOMAIN = "auto_chords"

CONF_MEDIA_PLAYERS = "media_players"
CONF_NOTIFY_SERVICES = "notify_services"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
    Platform.BUTTON,
    Platform.TODO,
]

STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = DOMAIN

DEFAULT_MASTER_ENABLED = False
DEFAULT_NOTIFICATIONS_ENABLED = True
DEFAULT_TARGET_ENABLED = True

SIGNAL_UPDATE = f"{DOMAIN}_update"
