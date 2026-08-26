"""Constants for the YouTube Pro integration."""

import logging
from datetime import timedelta

DOMAIN = "youtube_pro"
LOGGER = logging.getLogger(__package__)

CONF_TOKEN = "token"
CONF_CONFIG_ENTRY_ID = "config_entry_id"
CONF_DEFAULT_ENTITY_ID = "default_entity_id"
ADDON_PORT = 2032
ADDON_SLUG = "youtube_pro_addon"
AUTO_URL = "auto"
DEFAULT_URL = AUTO_URL
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=15)

SERVICE_PLAY = "play"
SERVICE_PLAY_PLAYLIST = "play_playlist"
SERVICE_ENQUEUE = "enqueue"
SERVICE_SET_TIMER = "set_timer"

REPEAT_MODES = ("off", "all", "one")
TIMER_TYPES = ("play", "stop")
