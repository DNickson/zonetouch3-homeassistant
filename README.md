# Polyaire ZoneTouch 3 for Home Assistant

A HACS integration for the [Polyaire ZoneTouch 3](https://polyaire.com.au/) zone
controller. It talks TCP directly to the ZoneTouch 3 console on your local
network — no cloud, no extra hardware.

## Features

- **Fan entity per zone** — on/off, open percentage (5% steps) and, on zones
  that support it, a *turbo* preset. Spill status is exposed as an attribute.
- **Temperature sensor** — the console's temperature reading.
- **Diagnostic sensors** — system ID, installer details, firmware and console
  versions.
- Zones and their names are **discovered automatically** from the console.
- Control commands apply instantly: the console's reply is used to update
  entity state without waiting for the next poll.

## Installation

1. Add this repository to HACS as a custom repository (type: integration) and
   install it, or copy the files into `custom_components/zonetouch3/`.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for
   **ZoneTouch 3**.
4. Enter the console's IP address (shown on the console under
   *System Settings → WiFi Settings*). The default port is 7030.

## Upgrading from 0.0.x

Version 0.2.0 is a rewrite:

- Configuration moved from `configuration.yaml` to the UI. Remove any
  `fan:`, `sensor:` or `text:` platform entries for `zonetouch3` from your
  YAML configuration, then add the integration via the UI.
- The text entities (System ID, etc.) are now diagnostic sensors, and the
  "Updater" helper entity no longer exists. Old orphaned entities can be
  removed from the entity registry.

## Protocol

The console is polled every 10 seconds over a short-lived TCP connection using
the documented group status (`0x21`) and group name (`0xFF 0x13`) messages;
zone control uses group control (`0x20`). System information and the console
temperature come from the undocumented extended message `0xFF 0xF0` used by
the official app. See `ZoneTouch3 Communication Protocol V1.0.pdf` in this
repository for the protocol specification.
