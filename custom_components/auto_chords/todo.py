"""To-do platform exposing the Auto Chords song registry."""

from __future__ import annotations

from homeassistant.components.todo import TodoItem, TodoListEntity
from homeassistant.components.todo.const import TodoItemStatus, TodoListEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AutoChordsConfigEntry
from .entity import AutoChordsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutoChordsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up song registry to-do entity."""
    async_add_entities([AutoChordsSongRegistry(entry.runtime_data)])


class AutoChordsSongRegistry(AutoChordsEntity, TodoListEntity):
    """Editable view of registered songs."""

    _attr_translation_key = "registered_songs"
    _attr_icon = "mdi:playlist-music"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(self, manager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{manager.entry.entry_id}_registered_songs"

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return songs as editable to-do items."""
        return [
            TodoItem(
                uid=song.uid,
                summary=_summary(song.artist, song.title),
                status=TodoItemStatus.NEEDS_ACTION,
                description=song.url,
            )
            for song in self.manager.songs.values()
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a song from the to-do UI."""
        if not item.summary:
            raise HomeAssistantError("A song name is required")
        url = (item.description or "").strip()
        if url and not url.startswith(("https://", "http://")):
            raise HomeAssistantError("URL must start with http:// or https://")
        await self.manager.async_create_registry_song(item.summary, url)

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a registered song."""
        if not item.uid or item.uid not in self.manager.songs:
            raise HomeAssistantError("Registered song was not found")
        if not item.summary:
            raise HomeAssistantError("A song name is required")
        url = (item.description or "").strip()
        if url and not url.startswith(("https://", "http://")):
            raise HomeAssistantError("URL must start with http:// or https://")
        await self.manager.async_update_registry_song(item.uid, item.summary, url)

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete registered songs."""
        await self.manager.async_delete_registry_songs(uids)


def _summary(artist: str, title: str) -> str:
    """Return visible registry summary."""
    return f"{artist} – {title}" if artist else title
