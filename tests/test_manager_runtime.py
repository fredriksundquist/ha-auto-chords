"""Focused runtime tests for Auto Chords manager behavior."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.auto_chords import async_unload_entry
from custom_components.auto_chords.manager import AutoChordsManager, RegisteredSong, Song


def _manager_with_song() -> tuple[AutoChordsManager, RegisteredSong]:
    manager = object.__new__(AutoChordsManager)
    manager.hass = SimpleNamespace()
    manager.entry = SimpleNamespace(
        data={"notify_services": ["mobile_app_test"], "media_players": []},
        options={},
        entry_id="test-entry",
    )
    registered = RegisteredSong(
        uid="registry-1",
        title="Lofotbrev",
        artist="Ola Bremnes",
        spotify_id="23wea78hoXqfnOE9JciIXy",
        match_key="ola bremnes|lofotbrev",
        url="https://tabs.example/lofotbrev",
    )
    manager.songs = {registered.uid: registered}
    manager.current_song = None
    manager.registration_url = ""
    manager.master_enabled = True
    manager.notifications_enabled = True
    manager.target_enabled = {"mobile_app_test": True}
    manager._unsub_media = None
    manager._last_notified_registry_uid = None
    manager._started = True
    manager._signal_update = lambda: None
    return manager, registered


def test_concurrent_group_events_only_notify_once() -> None:
    """Concurrent events for one registry item must reserve dedupe before await."""

    async def scenario() -> None:
        manager, _ = _manager_with_song()
        song = Song(
            title="Lofotbrev",
            artist="Ola Bremnes",
            source_player="media_player.stue",
            spotify_id="23wea78hoXqfnOE9JciIXy",
            match_key="ola bremnes|lofotbrev",
        )
        calls = 0

        async def fake_send(*_args) -> bool:
            nonlocal calls
            calls += 1
            await asyncio.sleep(0)
            return True

        manager._async_send_notifications = fake_send
        await asyncio.gather(
            manager.async_process_song(song),
            manager.async_process_song(song),
        )
        assert calls == 1

    asyncio.run(scenario())


def test_registry_uid_dedupes_spotify_and_fallback_identity() -> None:
    """The same registered song is one notification even with mixed identities."""

    async def scenario() -> None:
        manager, _ = _manager_with_song()
        spotify_song = Song(
            title="Lofotbrev",
            artist="Ola Bremnes",
            source_player="media_player.stue",
            spotify_id="23wea78hoXqfnOE9JciIXy",
            match_key="ola bremnes|lofotbrev",
        )
        fallback_song = Song(
            title="Lofotbrev",
            artist="Ola Bremnes",
            source_player="media_player.gjesterom_sonos",
            spotify_id=None,
            match_key="ola bremnes|lofotbrev",
        )
        calls = 0

        async def fake_send(*_args) -> bool:
            nonlocal calls
            calls += 1
            return True

        manager._async_send_notifications = fake_send
        await manager.async_process_song(spotify_song)
        await manager.async_process_song(fallback_song)
        assert calls == 1

    asyncio.run(scenario())


def test_partial_group_metadata_does_not_rearm_same_notification() -> None:
    """Full -> incomplete -> full metadata for one song must notify once."""

    async def scenario() -> None:
        manager, _ = _manager_with_song()
        complete = Song(
            title="Lofotbrev",
            artist="Ola Bremnes",
            source_player="media_player.stue",
            spotify_id="23wea78hoXqfnOE9JciIXy",
            match_key="ola bremnes|lofotbrev",
        )
        incomplete = Song(
            title="Lofotbrev",
            artist="",
            source_player="media_player.gjesterom_sonos",
            spotify_id=None,
            match_key="|lofotbrev",
        )
        calls = 0

        async def fake_send(*_args) -> bool:
            nonlocal calls
            calls += 1
            return True

        manager._async_send_notifications = fake_send
        await manager.async_process_song(complete)
        await manager.async_process_song(incomplete)
        await manager.async_process_song(complete)
        assert calls == 1

    asyncio.run(scenario())


def test_genuine_unregistered_song_rearms_previous_notification() -> None:
    """A different unregistered song should permit a later return notification."""

    async def scenario() -> None:
        manager, _ = _manager_with_song()
        registered_song = Song(
            title="Lofotbrev",
            artist="Ola Bremnes",
            source_player="media_player.stue",
            spotify_id="23wea78hoXqfnOE9JciIXy",
            match_key="ola bremnes|lofotbrev",
        )
        other_song = Song(
            title="En annen sang",
            artist="En annen artist",
            source_player="media_player.stue",
            spotify_id=None,
            match_key="en annen artist|en annen sang",
        )
        calls = 0

        async def fake_send(*_args) -> bool:
            nonlocal calls
            calls += 1
            return True

        manager._async_send_notifications = fake_send
        await manager.async_process_song(registered_song)
        await manager.async_process_song(other_song)
        await manager.async_process_song(registered_song)
        assert calls == 2

    asyncio.run(scenario())


def test_manual_create_updates_existing_match_instead_of_duplicate() -> None:
    """Manual to-do creation must not create two effective matches."""

    async def scenario() -> None:
        manager, registered = _manager_with_song()
        manager._async_save = AsyncMock()

        result = await manager.async_create_registry_song(
            "Ola Bremnes – Lofotbrev",
            "https://tabs.example/new-lofotbrev",
        )

        assert result.uid == registered.uid
        assert len(manager.songs) == 1
        assert registered.spotify_id == "23wea78hoXqfnOE9JciIXy"
        assert registered.url == "https://tabs.example/new-lofotbrev"

    asyncio.run(scenario())


def test_manual_registry_rejects_empty_title() -> None:
    """A manual summary must contain an actual song title."""

    async def scenario() -> None:
        manager, _ = _manager_with_song()
        manager._async_save = AsyncMock()

        with pytest.raises(ValueError, match="song title"):
            await manager.async_create_registry_song(
                "Ola Bremnes – ",
                "https://tabs.example/invalid",
            )

    asyncio.run(scenario())


def test_manual_update_rejects_duplicate_match_key() -> None:
    """Editing one registry item onto another match must be rejected."""

    async def scenario() -> None:
        manager, _ = _manager_with_song()
        second = RegisteredSong(
            uid="registry-2",
            title="Annen sang",
            artist="Annen artist",
            spotify_id=None,
            match_key="annen artist|annen sang",
            url="https://tabs.example/other",
        )
        manager.songs[second.uid] = second
        manager._async_save = AsyncMock()

        with pytest.raises(ValueError, match="already exists"):
            await manager.async_update_registry_song(
                second.uid,
                "Ola Bremnes – Lofotbrev",
                "https://tabs.example/duplicate",
            )

    asyncio.run(scenario())


def test_stopped_manager_ignores_queued_song_task() -> None:
    """A task reaching the manager after stop/master-off must do nothing."""

    async def scenario() -> None:
        manager, _ = _manager_with_song()
        manager._started = False
        song = Song(
            title="Lofotbrev",
            artist="Ola Bremnes",
            source_player="media_player.stue",
            spotify_id="23wea78hoXqfnOE9JciIXy",
            match_key="ola bremnes|lofotbrev",
        )
        manager._async_send_notifications = AsyncMock(return_value=True)

        await manager.async_process_song(song)

        assert manager.current_song is None
        manager._async_send_notifications.assert_not_awaited()

    asyncio.run(scenario())


def test_notification_payload_has_ios_and_android_links() -> None:
    """Companion notifications include URL keys for both platforms."""

    async def scenario() -> None:
        manager, registered = _manager_with_song()

        class Services:
            def __init__(self) -> None:
                self.payload = None

            def has_service(self, domain: str, service: str) -> bool:
                return domain == "notify" and service == "mobile_app_test"

            async def async_call(
                self,
                _domain: str,
                _service: str,
                payload: dict,
                *,
                blocking: bool,
            ) -> None:
                assert blocking is True
                self.payload = payload

        services = Services()
        manager.hass = SimpleNamespace(services=services)
        sent = await manager._async_send_notifications(
            registered, ["mobile_app_test"]
        )

        assert sent is True
        assert services.payload["data"] == {
            "url": registered.url,
            "clickAction": registered.url,
        }

    asyncio.run(scenario())


def test_unload_stops_manager_only_after_platforms_unload() -> None:
    """Runtime cleanup follows successful platform unloading."""

    async def scenario() -> None:
        order: list[str] = []
        manager = SimpleNamespace(
            async_stop=AsyncMock(side_effect=lambda: order.append("manager"))
        )

        async def unload_platforms(_entry, _platforms) -> bool:
            order.append("platforms")
            return True

        hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_unload_platforms=unload_platforms)
        )
        entry = SimpleNamespace(runtime_data=manager)

        assert await async_unload_entry(hass, entry) is True
        assert order == ["platforms", "manager"]

    asyncio.run(scenario())


def test_failed_platform_unload_keeps_manager_running() -> None:
    """Do not stop runtime resources when Home Assistant reports failed unload."""

    async def scenario() -> None:
        manager = SimpleNamespace(async_stop=AsyncMock())

        async def unload_platforms(_entry, _platforms) -> bool:
            return False

        hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_unload_platforms=unload_platforms)
        )
        entry = SimpleNamespace(runtime_data=manager)

        assert await async_unload_entry(hass, entry) is False
        manager.async_stop.assert_not_awaited()

    asyncio.run(scenario())
