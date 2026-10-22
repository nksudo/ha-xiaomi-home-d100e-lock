# -*- coding: utf-8 -*-
"""
Copyright (C) 2024 Xiaomi Corporation.

The ownership and intellectual property rights of Xiaomi Home Assistant
Integration and related Xiaomi cloud service API interface provided under this
license, including source code and object code (collectively, "Licensed Work"),
are owned by Xiaomi. Subject to the terms and conditions of this License, Xiaomi
hereby grants you a personal, limited, non-exclusive, non-transferable,
non-sublicensable, and royalty-free license to reproduce, use, modify, and
distribute the Licensed Work only for your use of Home Assistant for
non-commercial purposes. For the avoidance of doubt, Xiaomi does not authorize
you to use the Licensed Work for any other purpose, including but not limited
to use Licensed Work to develop applications (APP), Web services, and other
forms of software.

You may reproduce and distribute copies of the Licensed Work, with or without
modifications, whether in source or object form, provided that you must give
any other recipients of the Licensed Work a copy of this License and retain all
copyright and disclaimers.

Xiaomi provides the Licensed Work on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied, including, without
limitation, any warranties, undertakes, or conditions of TITLE, NO ERROR OR
OMISSION, CONTINUITY, RELIABILITY, NON-INFRINGEMENT, MERCHANTABILITY, or
FITNESS FOR A PARTICULAR PURPOSE. In any event, you are solely responsible
for any direct, indirect, special, incidental, or consequential damages or
losses arising from the use or inability to use the Licensed Work.

Xiaomi reserves all rights not expressly granted to you in this License.
Except for the rights expressly granted by Xiaomi under this License, Xiaomi
does not authorize you in any form to use the trademarks, copyrights, or other
forms of intellectual property rights of Xiaomi and its affiliates, including,
without limitation, without obtaining other written permission from Xiaomi, you
shall not use "Xiaomi", "Mijia" and other words related to Xiaomi or words that
may make the public associate with Xiaomi in any form to publicize or promote
the software or hardware devices that use the Licensed Work.

Xiaomi has the right to immediately terminate all your authorization under this
License in the event:
1. You assert patent invalidation, litigation, or other claims against patents
or other intellectual property rights of Xiaomi or its affiliates; or,
2. You make, have made, manufacture, sell, or offer to sell products that knock
off Xiaomi or its affiliates' products.

Switch entities for Xiaomi Home.
"""

# Native `lock` entity for the Xiaomi Self-Install Smart Lock (xiaomi.lock.d100e).
# Community contribution. See README.md in the repository for context.

from __future__ import annotations

from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.lock import LockEntity
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .miot.const import DOMAIN
from .miot.miot_device import MIoTDevice, MIoTEntityData, MIoTServiceEntity
from .miot.miot_spec import MIoTSpecAction, MIoTSpecProperty, MIoTSpecService


MODEL = "xiaomi.lock.d100e"

# SECURITY: while False, Home Assistant can only LOCK the door. Unlocking is
# refused for every caller (dashboards, Assist, Matter/HomeKit bridges,
# automations, MCP). Set it to True only if you accept that risk.
ALLOW_REMOTE_UNLOCK = False


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the D100E native lock entity."""
    device_list: list[MIoTDevice] = hass.data[DOMAIN]["devices"][
        config_entry.entry_id
    ]
    entities: list[D100ELock] = []
    for device in device_list:
        if device.model != MODEL:
            continue
        entity_data = _build_entity_data(device)
        if entity_data is not None:
            entities.append(D100ELock(device, entity_data))

    if entities:
        async_add_entities(entities)


def _build_entity_data(device: MIoTDevice) -> Optional[MIoTEntityData]:
    """Build a service entity containing the D100E state and battery props."""
    services = {service.iid: service for service in device.spec_instance.services}
    lock_service = services.get(19)
    action_service = services.get(18)
    door_service = services.get(20)
    battery_service = services.get(21)
    if not lock_service or not action_service:
        return None

    entity_data = MIoTEntityData(platform="lock", spec=lock_service)
    for service, names in (
        (lock_service, {"lock-state"}),
        (door_service, {"door-state"} if door_service else set()),
        (battery_service, {"lock-mah", "keypad-mah"} if battery_service else set()),
    ):
        if service:
            entity_data.props.update(
                prop for prop in service.properties if prop.name in names
            )

    # Prefer Bluetooth actions because they require no secret parameter.
    # Remote Wi-Fi actions require the D100E's secret and remain available as
    # the original Xiaomi Home action entities.
    entity_data.actions.update(
        action
        for action in action_service.actions
        if action.name in {"ble-lock", "ble-unlock"}
    )
    if not any(action.name == "ble-lock" for action in entity_data.actions):
        return None
    if not any(action.name == "ble-unlock" for action in entity_data.actions):
        return None
    return entity_data


class D100ELock(MIoTServiceEntity, LockEntity):
    """Home Assistant lock entity backed by Xiaomi D100E MIoT properties."""

    _lock_state: Optional[MIoTSpecProperty]
    _door_state: Optional[MIoTSpecProperty]
    _lock_battery: Optional[MIoTSpecProperty]
    _keypad_battery: Optional[MIoTSpecProperty]
    _lock_action: Optional[MIoTSpecAction]
    _unlock_action: Optional[MIoTSpecAction]

    def __init__(self, miot_device: MIoTDevice, entity_data: MIoTEntityData) -> None:
        super().__init__(miot_device=miot_device, entity_data=entity_data)
        self._lock_state = None
        self._door_state = None
        self._lock_battery = None
        self._keypad_battery = None
        self._lock_action = None
        self._unlock_action = None

        for prop in entity_data.props:
            if prop.name == "lock-state":
                self._lock_state = prop
            elif prop.name == "door-state":
                self._door_state = prop
            elif prop.name == "lock-mah":
                self._lock_battery = prop
            elif prop.name == "keypad-mah":
                self._keypad_battery = prop
        for action in entity_data.actions:
            if action.name == "ble-lock":
                self._lock_action = action
            elif action.name == "ble-unlock":
                self._unlock_action = action

        self._attr_icon = "mdi:lock"

    @property
    def is_locked(self) -> Optional[bool]:
        """MIoT lock-state: 0 = locked (deadbolt out), 1 = unlocked,
        2 = latch only (door closed, deadbolt NOT extended), 3 = abnormal.
        Value 2 is not secured, so it is reported as unlocked."""
        value = self.get_prop_value(self._lock_state)
        if value is None:
            return None
        if value == 0:
            return True
        if value in (1, 2):
            return False
        return None

    @property
    def is_jammed(self) -> bool:
        """Value 3 = abnormal state / jammed bolt."""
        return self.get_prop_value(self._lock_state) == 3

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose useful D100E state without making it a control surface."""
        attrs: dict[str, Any] = {}
        door = self.get_prop_value(self._door_state)
        if door is not None:
            attrs["door_state"] = {0: "open", 1: "closed", 2: "not_detected"}.get(
                door, door
            )
        lock_battery = self.get_prop_value(self._lock_battery)
        if lock_battery is not None:
            attrs["lock_battery"] = lock_battery
        keypad_battery = self.get_prop_value(self._keypad_battery)
        if keypad_battery is not None:
            attrs["keypad_battery"] = keypad_battery
        raw = self.get_prop_value(self._lock_state)
        if raw is not None:
            attrs["latch_only"] = raw == 2
            attrs["lock_state_raw"] = raw
        attrs["model"] = MODEL
        return attrs

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock via the existing Bluetooth MIoT action."""
        if not self._lock_action:
            raise HomeAssistantError("D100E BLE lock action is unavailable")
        try:
            await self.action_async(self._lock_action)
        except RuntimeError as err:
            raise HomeAssistantError(str(err)) from err

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock via the existing Bluetooth MIoT action (disabled by default)."""
        if not ALLOW_REMOTE_UNLOCK:
            raise ServiceValidationError(
                "Remote unlock is disabled (ALLOW_REMOTE_UNLOCK = False)."
            )
        if not self._unlock_action:
            raise HomeAssistantError("D100E BLE unlock action is unavailable")
        try:
            await self.action_async(self._unlock_action)
        except RuntimeError as err:
            raise HomeAssistantError(str(err)) from err
