"""Runtime manager for Auto Chords."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
import re
import unicodedata
from urllib.parse import unquote
from uuid import uuid4

from homeassistant.components.media_player.const import (
    ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_TITLE,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store

from .const import (
    CONF_MEDIA_PLAYERS,
    CONF_NOTIFY_SERVICES,
    DEFAULT_MASTER_ENABLED,
    DEFAULT_NOTIFICATIONS_ENABLED,
    DEFAULT_TARGET_ENABLED,
    SIGNAL_UPDATE,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)
_SPOTIFY_TRACK_RE = re.compile(r"spotify:track:([A-Za-z0-9]+)")


@dataclass(slots=True)
class Song:
    """Current song metadata."""

    title: str
    artist: str
    source_player: str
    spotify_id: str | None
    match_key: str

    @property
    def notification_key(self) -> str:
        """Return the strongest available identity for deduplication."""
        return self.spotify_id or self.match_key


@dataclass(slots=True)
class RegisteredSong:
    """A song stored in the registry."""

    uid: str
    title: str
    artist: str
    spotify_id: str | None
    match_key: str
    url: str

    def as_dict(self) -> dict[str, str | None]:
        """Serialize for storage."""
        return {
            "uid": self.uid,
            "title": self.title,
            "artist": self.artist,
            "spotify_id": self.spotify_id,
            "match_key": self.match_key,
            "url": self.url,
        }


class AutoChordsManager:
    """Manage song tracking, storage and notifications."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the manager."""
        self.hass = hass
        self.entry = entry
        self.store: Store[dict] = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY_PREFIX}.{entry.entry_id}",
        )
        self.songs: dict[str, RegisteredSong] = {}
        self.current_song: Song | None = None
        self.registration_url = ""

        self.master_enabled = DEFAULT_MASTER_ENABLED
        self.notifications_enabled = DEFAULT_NOTIFICATIONS_ENABLED
        self.target_enabled: dict[str, bool] = {
            target: DEFAULT_TARGET_ENABLED for target in self.notify_services
        }

        self._unsub_media: Callable[[], None] | None = None
        self._last_notified_key: str | None = None
        self._started = False

    @property
    def config(self) -> dict:
        """Return merged data and options."""
        return {**self.entry.data, **self.entry.options}

    @property
    def media_players(self) -> list[str]:
        """Return selected media players."""
        return list(self.config.get(CONF_MEDIA_PLAYERS, []))

    @property
    def notify_services(self) -> list[str]:
        """Return selected notify service names without the domain."""
        return list(self.config.get(CONF_NOTIFY_SERVICES, []))

    async def async_load(self) -> None:
        """Load the song registry."""
        data = await self.store.async_load() or {}
        for raw in data.get("songs", []):
            try:
                song = RegisteredSong(
                    uid=raw["uid"],
                    title=raw["title"],
                    artist=raw["artist"],
                    spotify_id=raw.get("spotify_id"),
                    match_key=raw["match_key"],
                    url=raw["url"],
                )
            except (KeyError, TypeError):
                _LOGGER.warning("Ignoring malformed song registry entry")
                continue
            self.songs[song.uid] = song

    async def async_start(self) -> None:
        """Start runtime listeners if enabled."""
        self._started = True
        if self.master_enabled:
            self._async_subscribe_media()
            await self.async_evaluate_current_states(notify=False)

    async def async_stop(self) -> None:
        """Stop all runtime listeners."""
        self._started = False
        self._async_unsubscribe_media()

    @callback
    def set_master_enabled(self, enabled: bool) -> None:
        """Enable or disable media tracking."""
        if self.master_enabled == enabled:
            return
        self.master_enabled = enabled
        self._last_notified_key = None
        if not self._started:
            self._signal_update()
            return
        if enabled:
            self._async_subscribe_media()
            self.hass.async_create_task(self.async_evaluate_current_states(notify=True))
        else:
            self._async_unsubscribe_media()
            self.current_song = None
            self._signal_update()

    @callback
    def set_notifications_enabled(self, enabled: bool) -> None:
        """Enable or disable all outgoing notifications."""
        self.notifications_enabled = enabled
        self._signal_update()

    @callback
    def set_target_enabled(self, target: str, enabled: bool) -> None:
        """Set the runtime state for a notification target."""
        self.target_enabled[target] = enabled
        self._signal_update()

    @callback
    def set_registration_url(self, value: str) -> None:
        """Set the registration URL input value."""
        self.registration_url = value.strip()
        self._signal_update()

    async def async_register_current_song(self, url: str) -> RegisteredSong:
        """Register or update the current song."""
        if self.current_song is None:
            raise ValueError("No current song is available")
        url = validate_url(url)

        existing = self.find_registered(self.current_song)
        if existing is None:
            registered = RegisteredSong(
                uid=uuid4().hex,
                title=self.current_song.title,
                artist=self.current_song.artist,
                spotify_id=self.current_song.spotify_id,
                match_key=self.current_song.match_key,
                url=url,
            )
            self.songs[registered.uid] = registered
        else:
            existing.title = self.current_song.title
            existing.artist = self.current_song.artist
            existing.spotify_id = self.current_song.spotify_id
            existing.match_key = self.current_song.match_key
            existing.url = url
            registered = existing

        self.registration_url = ""
        await self._async_save()
        self._signal_update()
        return registered

    async def async_create_registry_song(self, summary: str, url: str) -> RegisteredSong:
        """Create a registry item manually from the to-do list."""
        artist, title = split_summary(summary)
        registered = RegisteredSong(
            uid=uuid4().hex,
            title=title,
            artist=artist,
            spotify_id=None,
            match_key=build_match_key(artist, title),
            url=validate_url(url),
        )
        self.songs[registered.uid] = registered
        await self._async_save()
        self._signal_update()
        return registered

    async def async_update_registry_song(
        self, uid: str, summary: str, url: str
    ) -> None:
        """Update a registry item from the to-do list."""
        registered = self.songs[uid]
        artist, title = split_summary(summary)
        new_match_key = build_match_key(artist, title)
        if new_match_key != registered.match_key:
            # The item now describes a different song. An old Spotify identity
            # must not continue to match the previous track.
            registered.spotify_id = None
        registered.artist = artist
        registered.title = title
        registered.match_key = new_match_key
        registered.url = validate_url(url)
        await self._async_save()
        self._signal_update()

    async def async_delete_registry_songs(self, uids: list[str]) -> None:
        """Delete registry items."""
        for uid in uids:
            self.songs.pop(uid, None)
        await self._async_save()
        self._signal_update()

    def find_registered(self, song: Song | None) -> RegisteredSong | None:
        """Find a registered match for a song."""
        if song is None:
            return None
        if song.spotify_id:
            for item in self.songs.values():
                if item.spotify_id == song.spotify_id:
                    return item
        for item in self.songs.values():
            if item.match_key == song.match_key:
                return item
        return None

    @callback
    def _async_subscribe_media(self) -> None:
        """Subscribe to selected media players."""
        if self._unsub_media is not None or not self.media_players:
            return
        self._unsub_media = async_track_state_change_event(
            self.hass,
            self.media_players,
            self._async_media_changed,
        )

    @callback
    def _async_unsubscribe_media(self) -> None:
        """Unsubscribe from media player state changes."""
        if self._unsub_media is None:
            return
        self._unsub_media()
        self._unsub_media = None

    @callback
    def _async_media_changed(self, event: Event[EventStateChangedData]) -> None:
        """Handle a selected media player state change."""
        if not self.master_enabled:
            return
        state = event.data.get("new_state")
        if state is None:
            return
        song = song_from_state(state)
        if song is None:
            return
        self.hass.async_create_task(self.async_process_song(song))

    async def async_evaluate_current_states(self, *, notify: bool) -> None:
        """Evaluate current player states, preferring an active player."""
        for entity_id in self.media_players:
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            song = song_from_state(state)
            if song is not None:
                await self.async_process_song(song, notify=notify)
                return

    async def async_process_song(self, song: Song, *, notify: bool = True) -> None:
        """Set the current song and possibly send its registered URL."""
        same_song = (
            self.current_song is not None
            and self.current_song.notification_key == song.notification_key
        )
        self.current_song = song
        self._signal_update()

        if same_song:
            return

        registered = self.find_registered(song)
        if registered is None:
            self._last_notified_key = None
            return

        if (
            not notify
            or not self.notifications_enabled
            or self._last_notified_key == song.notification_key
        ):
            return

        enabled_targets = [
            target
            for target in self.notify_services
            if self.target_enabled.get(target, DEFAULT_TARGET_ENABLED)
        ]
        if not enabled_targets:
            return

        await self._async_send_notifications(registered, enabled_targets)
        self._last_notified_key = song.notification_key

    async def _async_send_notifications(
        self, registered: RegisteredSong, targets: list[str]
    ) -> None:
        """Send the chord URL through selected mobile app notify services."""
        title = f"🎸 {registered.title}"
        message = registered.artist or "Auto Chords"
        payload = {
            "title": title,
            "message": message,
            "data": {"url": registered.url},
        }

        for target in targets:
            if not self.hass.services.has_service("notify", target):
                _LOGGER.warning("Notify action notify.%s is not available", target)
                continue
            try:
                await self.hass.services.async_call(
                    "notify",
                    target,
                    payload,
                    blocking=True,
                )
            except Exception:
                _LOGGER.exception("Failed to send chord notification via notify.%s", target)

    async def _async_save(self) -> None:
        """Persist the song registry."""
        await self.store.async_save(
            {"songs": [song.as_dict() for song in self.songs.values()]}
        )

    @callback
    def _signal_update(self) -> None:
        """Notify entities that in-memory state changed."""
        async_dispatcher_send(self.hass, SIGNAL_UPDATE, self.entry.entry_id)


def validate_url(value: str) -> str:
    """Validate and normalize a stored chord URL."""
    value = value.strip()
    if not value.startswith(("https://", "http://")):
        raise ValueError("URL must start with http:// or https://")
    return value


def normalize(value: str) -> str:
    """Normalize artist/title text for fallback matching."""
    value = unicodedata.normalize("NFKC", value).casefold()
    value = "".join(char if char.isalnum() else " " for char in value)
    return " ".join(value.split())


def build_match_key(artist: str, title: str) -> str:
    """Build the fallback song match key."""
    return f"{normalize(artist)}|{normalize(title)}"


def extract_spotify_track_id(content_id: object) -> str | None:
    """Extract a Spotify track ID from Sonos/Spotify media content IDs."""
    if not isinstance(content_id, str):
        return None
    decoded = unquote(content_id)
    match = _SPOTIFY_TRACK_RE.search(decoded)
    return match.group(1) if match else None


def song_from_state(state: State) -> Song | None:
    """Build song metadata from a media player state."""
    if state.state != MediaPlayerState.PLAYING:
        return None
    title = state.attributes.get(ATTR_MEDIA_TITLE)
    artist = state.attributes.get(ATTR_MEDIA_ARTIST)
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(artist, str):
        artist = ""
    title = title.strip()
    artist = artist.strip()
    return Song(
        title=title,
        artist=artist,
        source_player=state.entity_id,
        spotify_id=extract_spotify_track_id(
            state.attributes.get(ATTR_MEDIA_CONTENT_ID)
        ),
        match_key=build_match_key(artist, title),
    )


def split_summary(summary: str) -> tuple[str, str]:
    """Split the visible 'Artist – Title' registry summary."""
    summary = summary.strip()
    if " – " in summary:
        artist, title = summary.split(" – ", 1)
        return artist.strip(), title.strip()
    if " - " in summary:
        artist, title = summary.split(" - ", 1)
        return artist.strip(), title.strip()
    return "", summary
