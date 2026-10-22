<!--
  GitHub issue for XiaoMi/ha_xiaomi_home
  Paste the TITLE in the title box and everything below the line in the body.
-->

**TITLE:** Xiaomi Self-Install Smart Lock (`xiaomi.lock.d100e`): entities named "NA", event arguments overwrite each other (user ID lost) and no `lock` entity

---

## Summary

The Xiaomi Self-Install Smart Lock (`xiaomi.lock.d100e`) **is discovered** by the integration and about 110 entities are created, but the result is hard to use:

1. Every service/property/event/action is named `NA`, and enum states show `NA`, `NA_2`, ...
2. All parameters of the *operation log* event are named `NA`, so they overwrite each other in the event attributes. **The user ID (who opened the door) is lost**; only the last parameter (a timestamp) survives.
3. There is no `lock` entity, so the lock is not controllable or usable as a lock (it ends up as generic sensors).
4. Unlock-type actions (Bluetooth, emergency, remote Wi-Fi, voice) are created as ordinary enabled buttons / notify entities.

I have a working workaround (local translations) and a proposal for a native `lock` entity. Files are attached / linked below. I would like to know what the maintainers prefer so this can be fixed upstream for everyone.

## Environment

- Home Assistant: 2026.10.2
- Xiaomi Home integration: v0.5.0 (installed with HACS)
- Cloud server: US
- Device: Xiaomi Self-Install Smart Lock, model `xiaomi.lock.d100e`, lock firmware `2.7.0_0029`
- Spec URN: `urn:miot-spec-v2:device:lock:0000A038:xiaomi-d100e:2` (services use the proprietary namespace, hence the `*` prefix in entity names)

## Evidence

### 1. Everything is "NA"

The cached spec (`.storage/xiaomi_home/miot_specs/urn:miot-spec-v2:device:lock:0000A038:xiaomi-d100e:2_es.dict`) has `description_trans: "NA"` for the device and for every service, property, event and action. Resulting entity names look like `* NA NA`, and enum values are `NA`, `NA_2`, `NA_3`:

| Property | siid/piid | Real value list | What HA shows |
|---|---|---|---|
| lock-state | 19/12 | 0 locked, 1 unlocked, 2 latch only, 3 abnormal | `Cerradura`, `Desbloquear`, `NA`, `NA_2` |
| door-state | 20/1 | 0 open, 1 closed, 2 not detected | `NA`, `NA_2`, `NA_3` |

### 2. Event arguments collide (data loss)

`MIoTEventEntity.__init__` (miot/miot_device.py) builds:

```python
self._arguments_map = {}
for prop in spec.argument:
    self._arguments_map[prop.iid] = prop.description_trans
```

and `__on_event_occurred` stores `trans_arg[self._arguments_map[item['piid']]] = item['value']`.
When several arguments share the same translated name (here all of them are `NA`), the dict keeps only the last one.

The operation-log event (siid 22, eiid 1) has 5 arguments: `res (3)`, `operation-log-type (1)`, `operation-id (4)`, `push-status (5)`, `current-time (6)`. Before the workaround the event entity only exposed:

```
event_type: NA
NA: <unix timestamp>        # the last argument; user ID and operation type are gone
```

After adding translations (workaround below) the same event exposes all five values:

```
event_type: Operation log
Operation type: 19
Result: 1
User ID: 0
Notification sent: true
Event time: <unix timestamp>
```

This looks like a generic problem for any device whose arguments are untranslated or share a name, so I propose a small fix (see `fix-event-argument-collision.patch`): make duplicated names unique by appending the piid.

### 3. No `lock` entity

`lock` is not in `SUPPORTED_PLATFORMS` and there is no conversion rule for the lock device type, so `lock-state` (a 4-value enum, `latch only` being the most common real state) ends up as a plain enum sensor. There is also no way to lock the door from HA.

### 4. Dangerous actions enabled by default

The spec has actions for Bluetooth unlock (`ble-unlock`), emergency unlock, remote Wi-Fi unlock and voice unlock. They are created as enabled `button` / `notify` entities. If someone exposes all entities to a voice assistant or a HomeKit/Matter bridge, these become pressable. It would be safer to create unlock-type actions disabled by default (`entity_registry_enabled_default = False`). I do **not** know whether the Bluetooth actions work through the cloud or require Bluetooth proximity; I have not tested them.

## Workaround (works for me)

1. Local translation entry for the model in `miot/specs/multi_lang.json` (file: `multi_lang_xiaomi.lock.d100e.json`, English + Spanish, 284 keys). Format as documented in the README (`service:019:property:012:valuelist:002`, ...).
2. Settings > Xiaomi Home > Configure > "Update entity conversion rules".

Result: entity names, enum states and event attributes are correct and the user ID is available.

## Proposed changes

1. **Translations** for `xiaomi.lock.d100e` in the cloud multi-language data or in `multi_lang.json` (file attached).
2. **Event argument fix** so duplicated/untranslated names do not overwrite each other (`fix-event-argument-collision.patch`, a ~10 line change, applies cleanly on v0.5.0).
3. **Native `lock` platform** for this model (`lock.py` + one line in `const.py`, see `const.py.patch`):
   - `is_locked`: `0` locked; `1` and `2` unlocked (value 2 is latch only, the door is **not** secured); `3` jammed.
   - Lock uses the `ble-lock` action. Unlock is **disabled by default** (`ALLOW_REMOTE_UNLOCK = False`), because a `lock` entity makes unlock reachable from every integration and assistant.
   - Extra attributes: `door_state`, `lock_battery`, `keypad_battery`, `latch_only`.
4. Mark unlock-type actions as disabled by default.

## Questions for the maintainers

- Can the cloud translations for this model be added?
- Is a model-specific `lock` platform acceptable, or would you prefer a generic conversion rule (lock service + door-state) in `specv2entity`? If generic, how should unlock be gated (opt-in option, confirmation, code)?
- Do `ble-lock` / `ble-unlock` work through the cloud API or only locally over Bluetooth?

## Operation log reference (from the public MIoT spec)

`operation-log-type` (siid 22, piid 1). Value `19` (door closed) was verified on a real device; the others come from the public spec and are not verified.

| Value | Meaning | Value | Meaning |
|---|---|---|---|
| 0 | Matter unlock | 11 | Periodic password unlock |
| 1 | Matter lock | 12 | Fingerprint added |
| 2 | Manual lock | 13 | Fingerprint deleted |
| 3 | App lock | 14 | Password added |
| 4 | One-touch unlock | 15 | Password deleted |
| 5 | One-touch lock | 16 | Emergency unlock |
| 6 | Password unlock | 17 | Keypad key lock |
| 7 | Fingerprint unlock | 18 | Auto-lock |
| 8 | Manual unlock | 19 | Door closed |
| 9 | App unlock | 20 | Unlock failed |
| 10 | One-time password unlock | 21 | Lock failed |

*Serial numbers, MAC addresses, Matter pairing data and account IDs have been removed from this report.*
