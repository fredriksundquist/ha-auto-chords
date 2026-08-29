# Auto Chords

Auto Chords is a Home Assistant custom integration that links songs playing on selected `media_player` entities to chord/tab URLs and can send the registered link as a clickable Home Assistant Companion notification.

> **Development status:** `0.1.0-alpha.2` has passed its first real Home Assistant 2026.8.3 runtime test. Config entry setup, Sonos metadata tracking, registration, persistence and Companion notification delivery have all been verified on the target Home Assistant instance.

## V0.1 behavior

- Watches only the `media_player` entities selected in the integration setup.
- A true master switch disconnects the media state listeners while disabled.
- A separate global notification switch mutes outgoing notifications without stopping song tracking.
- Every selected `notify.mobile_app_*` target gets its own enable/disable switch.
- Uses Spotify track ID when Home Assistant exposes one; otherwise falls back to normalized artist + title.
- Shows the latest detected song in a sensor with artist, source player, Spotify track ID, registration status and registered URL as attributes.
- Register the current song by pasting an HTTP/HTTPS chord URL into the **Chord URL** text entity and pressing **Register current song**.
- Registered songs are exposed through a standard Home Assistant to-do list so entries can be viewed, edited and deleted in the existing frontend.
- Suppresses duplicate notifications when grouped players resolve to the same registered song, including a full → temporarily incomplete → full metadata sequence for the same title.
- Re-evaluates matching when media metadata becomes more complete, so staged Sonos metadata updates do not prevent a valid match.
- Sends the registered link using the Companion notification URL fields for both iOS and Android.
- Manual to-do creation reuses an existing artist/title match instead of creating a second effective duplicate.

## Installation via HACS custom repository

This repository is structured as a HACS integration repository and is public so HACS can access it. The current build has passed HACS repository validation.

Minimum supported Home Assistant version for this alpha is **2026.8.3**.

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/fredriksundquist/ha-auto-chords` as type **Integration**.
3. Download Auto Chords.
4. Restart Home Assistant.
5. Add **Auto Chords** under **Settings → Devices & services**.

Existing installations can be updated through HACS. Removing the config entry is not required for normal updates; registered songs and settings remain in the existing Auto Chords store.

## Configuration

The config flow requires:

- one or more `media_player` entities;
- one or more currently registered `notify.mobile_app_*` actions.

The notification target list comes from Home Assistant's registered `notify` actions at the moment the config/options form is opened. If a Companion device is renamed or its notify action changes, open the integration options and select the new action.

For the first test, selecting one Sonos player or players that represent the same synchronized playback is recommended. Multiple independent players that are playing different songs at the same time do not yet have a source-priority policy.

## Entities

All entities belong to one Home Assistant device named **Auto Chords**:

- **Auto Chords** — master switch. Off means no media-player listener is registered.
- **Notifications** — global notification mute.
- **Notifications: _device_** — one switch per selected notification action.
- **Current song** — current title plus useful matching/registration attributes.
- **Chord URL** — transient URL input used by the registration button.
- **Register current song** — stores/updates the currently detected song.
- **Registered songs** — editable to-do-list view of the persistent song registry.

The **Registered songs** list is used as an editable registry, not as a task tracker. Home Assistant still renders a normal to-do checkbox, but completion state is intentionally not stored in V0.1; registered songs remain active until edited or deleted.

## Clickable chord link in a dashboard

The **Current song** sensor exposes the registered chord URL as its `chord_url` attribute. A standard Markdown card can therefore show a clickable link for the currently playing registered song.

Replace `sensor.auto_chords_current_song` with the actual entity ID if Home Assistant generated a different one:

```yaml
type: markdown
content: >
  {% set url = state_attr('sensor.auto_chords_current_song', 'chord_url') %}
  {% set title = states('sensor.auto_chords_current_song') %}
  {% if url %}
  ## 🎸 {{ title }}
  [Open chords]({{ url }})
  {% else %}
  **{{ title }}**

  No chord link registered for this song.
  {% endif %}
```

This does not require an additional Auto Chords entity. The dashboard reads the existing `chord_url` sensor attribute and updates automatically when the current song changes.

## Stored data

Auto Chords keeps its own persistent data in one Home Assistant `Store` owned by the config entry. It contains:

- generated song-registry UID;
- song title;
- artist;
- Spotify track ID when available;
- normalized artist/title match key;
- chord/tab URL;
- master-switch state;
- global notification-switch state;
- enabled/disabled state for configured notification targets.

The selected media players and notification actions are ordinary Home Assistant config-entry data/options. The **Chord URL** input is deliberately transient and starts empty after a restart; incomplete pasted URLs are not persisted.

Auto Chords does **not**:

- contact Ultimate Guitar;
- scrape chord sites;
- use the Spotify API;
- require Music Assistant;
- poll the internet;
- create `input_*` helpers;
- use Home Assistant restore-state storage for its own switches/text input;
- register a global Home Assistant state-change listener while enabled. It subscribes only to the selected media-player entity IDs.

## Validation

The current build has passed:

- Python 3.14.2 source compilation;
- Ruff static checks;
- pytest with Home Assistant 2026.8.3;
- Home Assistant hassfest;
- HACS integration repository validation;
- first real target-instance runtime testing on Home Assistant 2026.8.3.

The test suite covers matching helpers, URL validation, concurrent notification deduplication, mixed Spotify/fallback identity, staged full/incomplete/full Sonos metadata, queued-task lifecycle after stop, iOS/Android notification link data, manual registry duplicate/title validation and config-entry unload ordering.

CI also uses `pytest-homeassistant-custom-component` pinned to the release generated for Home Assistant 2026.8.3. A Home Assistant fixture smoke-test sets up a real config entry, forwards all five platforms, verifies the Auto Chords device/entity registry entries, and exercises the config flow's empty-selection validation.

## Uninstall

Use this order so Home Assistant can run the integration's cleanup handler:

1. Go to **Settings → Devices & services → Auto Chords** and remove the integration entry.
2. The integration unloads its media listeners and deletes the config entry's Auto Chords `Store`, including registered songs and switch settings.
3. Confirm the Auto Chords device/entities are gone from Home Assistant.
4. Then uninstall Auto Chords in HACS (or remove `custom_components/auto_chords` if it was installed manually).
5. Restart Home Assistant if requested.

Do **not** delete the integration code before removing the config entry. If the Python files are removed first, Home Assistant cannot execute Auto Chords' `async_remove_entry()` cleanup code.

Normal historical states already written to Home Assistant's Recorder database are controlled by Home Assistant's own retention/purge policy; Auto Chords does not directly modify Recorder history.

## Matching details

For Sonos playback of Spotify tracks, a media content ID such as:

```text
x-sonos-spotify:spotify%3atrack%3a23wea78hoXqfnOE9JciIXy?sid=9&flags=8232&sn=2
```

is decoded and the Spotify track ID `23wea78hoXqfnOE9JciIXy` is used as the preferred identity. If no Spotify track ID is present, Auto Chords compares a normalized `artist|title` key.

Notification deduplication is based on the matched registry item's UID. If a grouped Sonos temporarily reports the same title without artist or Spotify ID after that registry item has already notified, Auto Chords treats that as potentially staged metadata and does not immediately re-arm the same notification. A genuinely different unmatched song still re-arms notifications for a later return to the registered song.

If the artist/title of a registry entry is changed manually, an old Spotify track ID is discarded so it cannot accidentally keep matching the previous track. Editing one registry entry so it would duplicate another artist/title match is rejected.

## Branches

- `main` — reviewed/testable baseline and releases.
- `dev` — active development and review before merge.

## License

MIT
