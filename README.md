# Auto Chords  DANGER! NOT FINISH! FIRST TEST!

Auto Chords is a Home Assistant custom integration that links songs playing on selected `media_player` entities to chord/tab URLs and can send the registered link as a clickable Home Assistant Companion notification.

> **Development status:** `0.1.0-alpha.1` is prepared for the first Home Assistant test, but has not yet been installed on the target Home Assistant instance. The current review build on `dev` has passed Python 3.14.2 compilation, Ruff, pytest against Home Assistant 2026.8.3, Home Assistant hassfest and HACS validation. Keep the warning above until the first real Home Assistant test has succeeded.

## V0.1 behavior

- Watches only the `media_player` entities selected in the integration setup.
- A true master switch disconnects the media state listeners while disabled.
- A separate global notification switch mutes outgoing notifications without stopping song tracking.
- Every selected `notify.mobile_app_*` target gets its own enable/disable switch.
- Uses Spotify track ID when Home Assistant exposes one; otherwise falls back to normalized artist + title.
- Shows the latest detected song in a sensor with artist, source player, Spotify track ID, registration status and registered URL as attributes.
- Register the current song by pasting an HTTP/HTTPS chord URL into the **Chord URL** text entity and pressing **Register current song**.
- Registered songs are exposed through a standard Home Assistant to-do list so entries can be viewed, edited and deleted in the existing frontend.
- Suppresses duplicate notifications when grouped players resolve to the same registered song.
- Re-evaluates matching when media metadata becomes more complete, so staged Sonos metadata updates do not prevent a valid match.
- Sends the registered link using the Companion notification URL fields for both iOS and Android.

## Installation later via HACS custom repository

This repository is structured as a HACS integration repository and is public so HACS can access it. The current review build has passed HACS repository validation.

After the reviewed build has been merged to `main`:

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/fredriksundquist/ha-auto-chords` as type **Integration**.
3. Download Auto Chords.
4. Restart Home Assistant.
5. Add **Auto Chords** under **Settings → Devices & services**.

## Configuration

The config flow asks for:

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

The current review build has passed:

- Python 3.14.2 source compilation;
- Ruff static checks;
- pytest while importing Home Assistant 2026.8.3;
- Home Assistant hassfest;
- HACS integration repository validation.

The focused tests cover matching helpers, URL validation, concurrent notification deduplication, mixed Spotify/fallback identity, queued-task lifecycle after stop, iOS/Android notification link data, and config-entry unload ordering.

Passing these checks does not replace testing the integration in a real Home Assistant instance. The first target-instance installation is still the next release gate.

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

Notification deduplication is based on the matched registry item's UID. This avoids duplicate notifications when one selected player exposes a Spotify ID while another reaches the same registered song through artist/title fallback.

If the artist/title of a registry entry is changed manually, an old Spotify track ID is discarded so it cannot accidentally keep matching the previous track.

## Branches

- `main` — reviewed/testable baseline and releases.
- `dev` — active development and review before merge.

## License

MIT
