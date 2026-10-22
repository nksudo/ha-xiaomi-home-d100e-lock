<!--
  PR 1 (small and generic). Branch suggestion: fix/event-argument-collision-and-d100e-translations
  TITLE: Fix event arguments overwriting each other and add translations for xiaomi.lock.d100e
-->

## What this changes

1. **`miot/miot_device.py`**: when two arguments of an event resolve to the same name (for example untranslated names, which all become `NA`), the attribute keys are made unique by appending the piid. Before, only the last argument survived.
2. **`miot/specs/multi_lang.json`**: adds the entry `urn:miot-spec-v2:device:lock:0000A038:xiaomi-d100e` with English and Spanish translations (284 keys) for the Xiaomi Self-Install Smart Lock (`xiaomi.lock.d100e`).

## Why

The model uses a proprietary spec with no cloud translations. Every name becomes `NA`, and the operation-log event, which carries the user ID of who opened the door, lost almost all its data because the five arguments were all called `NA`.

Related issue: <link to the issue>

## Before / after (operation-log event)

Before:

```
event_type: NA
NA: <unix timestamp>
```

After:

```
event_type: Operation log
Operation type: 19
Result: 1
User ID: 0
Notification sent: true
Event time: <unix timestamp>
```

## How I tested

- Home Assistant 2026.10.2, Xiaomi Home v0.5.0, one `xiaomi.lock.d100e`.
- Applied both changes, ran "Update entity conversion rules" and checked entity names, enum states and the event attributes above.
- The patch applies cleanly on v0.5.0 (`patch -p1 --dry-run`).

## Notes

- The event fix does not change names that are already unique, so existing devices are unaffected.
- Only the lock model above gets new translations; no existing entry in `multi_lang.json` is modified.
- Keys follow the documented format (`service:019:property:012:valuelist:002`; three-digit decimal ids; the value-list key uses the list index).
