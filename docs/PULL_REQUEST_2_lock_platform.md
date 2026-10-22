<!--
  PR 2 (to open only after the maintainers answer the questions in the issue).
  TITLE: Add a native lock entity for xiaomi.lock.d100e (unlock disabled by default)
-->

## What this changes

- Adds `lock.py`: a `lock` platform for the model `xiaomi.lock.d100e` only.
- Adds `'lock'` to `SUPPORTED_PLATFORMS` in `miot/const.py`.

## Behaviour

| MIoT `lock-state` | Home Assistant state |
|---|---|
| 0 | locked |
| 1 | unlocked |
| 2 (latch only, deadbolt not extended) | unlocked (attribute `latch_only: true`) |
| 3 (abnormal) | jammed |

Extra attributes: `door_state` (open / closed / not_detected), `lock_battery`, `keypad_battery`, `lock_state_raw`, `model`.

## Security

A `lock` entity makes unlocking reachable from dashboards, Assist, Matter/HomeKit bridges, automations and MCP clients without any extra confirmation. For that reason:

- `lock.lock` uses the existing `ble-lock` action.
- `lock.unlock` is refused unless `ALLOW_REMOTE_UNLOCK` is set to `True` in `lock.py`. I would prefer to turn this into an integration option if the maintainers agree.
- Emergency, voice and remote Wi-Fi unlock are not used by this entity.

## Open points

- I could not verify that `ble-lock` / `ble-unlock` work through the cloud API. State mapping and entity creation were verified; the lock command was not.
- If a generic `lock` conversion rule in `specv2entity` is preferred over a model-specific platform, I am happy to rework this.

## Tested

Home Assistant 2026.10.2, Xiaomi Home v0.5.0, one `xiaomi.lock.d100e`: the entity is created, shows `unlocked` with `latch_only: true` when the door is closed without the deadbolt, and `unlock` is refused with the default settings.
