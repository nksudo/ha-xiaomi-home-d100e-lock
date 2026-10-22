Xiaomi Self-Install Smart Lock (xiaomi.lock.d100e) for Xiaomi Home

Community fix so the Xiaomi Self-Install Smart Lock works properly with the official Xiaomi Home integration for Home Assistant. 🇪🇸 Versión en español más abajo.

Unofficial. Tested by one user on one lock (Home Assistant 2026.10.2, Xiaomi Home v0.5.0). Use at your own risk.

The problem

The lock is discovered and about 110 entities are created, but:

all names are NA (* NA NA) and enum states show NA, NA_2, ...;
the operation-log event has 5 parameters that are all called NA, so they overwrite each other and the user ID (who opened the door) is lost;
there is no lock entity.

Details and evidence: docs/ISSUE_xiaomi_home_d100e.md.

What is in this repository
File	Purpose
multi_lang_xiaomi.lock.d100e.json	Translations (English + Spanish) for the model. Fixes names, states and event attributes.
custom_components/xiaomi_home/lock.py	New native lock entity (unlock is disabled by default).
custom_components/xiaomi_home/miot/const.py.patch	One line that registers the lock platform.
custom_components/xiaomi_home/miot/fix-event-argument-collision.patch	Optional generic fix for event arguments that share a name.
docs/	Issue and pull-request texts for the upstream project.
Install
Back up your Home Assistant.
Translations (the most important step). Open /config/custom_components/xiaomi_home/miot/specs/multi_lang.json and add the whole "urn:miot-spec-v2:device:lock:0000A038:xiaomi-d100e": { ... } block from multi_lang_xiaomi.lock.d100e.json inside the top-level { } (keep the JSON valid: a comma between entries).
In Settings > Devices & services > Xiaomi Home > Configure choose Update entity conversion rules.
(Optional, for the lock entity) copy lock.py to /config/custom_components/xiaomi_home/ and add 'lock', after 'light', in SUPPORTED_PLATFORMS of miot/const.py (or apply the patch from the xiaomi_home folder: patch -p1 < miot/const.py.patch).
(Optional) apply miot/fix-event-argument-collision.patch the same way.
Restart Home Assistant.

Xiaomi Home updates (HACS) overwrite these files: re-apply them after updating.

Use: who opened the door

The event entity event.<...>_operation_log_e_22_1 exposes Operation type, Result, User ID, Notification sent and Event time (names follow your integration language).

yaml
triggers:
  - trigger: state
    entity_id: event.<your_lock>_operation_log_e_22_1
conditions:
  - condition: template
    value_template: "{{ trigger.to_state.attributes.get('Operation type') | int(-1) == 7 }}"   # 7 = fingerprint
actions:
  - action: notify.notify
    data:
      message: "Fingerprint unlock, user {{ trigger.to_state.attributes.get('User ID') }}"

Operation types are listed in the issue text. Find each person's User ID by opening the door once with each fingerprint or code.

Safety notes
Unlock actions (Bluetooth, emergency, remote Wi-Fi, voice) are created as normal entities by the integration. Disable them in Settings > Entities and do not expose the lock to voice assistants or to HomeKit/Matter bridges.
lock.unlock is refused by default (ALLOW_REMOTE_UNLOCK = False in lock.py).
lock-state = 2 means latch only: the door is closed but the deadbolt is not extended. It is reported as unlocked. Enable the lock's auto-lock if you want the deadbolt to extend by itself.
It is not verified that the Bluetooth lock/unlock actions work through the cloud.
License

The Xiaomi Home integration is Copyright (C) 2024 Xiaomi Corporation and is distributed under its own license (non-commercial use with Home Assistant; copies must retain the license and copyright). lock.py keeps that header. The patches and translations are provided for use with that integration under the same terms. Read the upstream LICENSE.md and CONTRIBUTING.md before sending anything upstream.

🇪🇸 Versión en español

Arreglo comunitario para que la Xiaomi Self-Install Smart Lock (xiaomi.lock.d100e) funcione bien con la integración oficial Xiaomi Home de Home Assistant.

No oficial. Probado por una persona con una cerradura (Home Assistant 2026.10.2, Xiaomi Home v0.5.0). Úsalo bajo tu responsabilidad.

El problema

La cerradura se detecta y se crean unas 110 entidades, pero todos los nombres salen como NA, los estados como NA/NA_2, y el evento de registro de operaciones trae 5 parámetros que se llaman igual y se pisan entre sí: se pierde el ID de usuario (quién abrió). Tampoco existe una entidad lock.

Instalación
Haz una copia de seguridad.
Traducciones (el paso más importante): en /config/custom_components/xiaomi_home/miot/specs/multi_lang.json añade el bloque "urn:miot-spec-v2:device:lock:0000A038:xiaomi-d100e": { ... } de multi_lang_xiaomi.lock.d100e.json dentro del { } principal (con una coma entre entradas).
En Ajustes > Dispositivos y servicios > Xiaomi Home > Configurar elige Actualizar reglas de conversión de entidades.
(Opcional, para la entidad lock) copia lock.py a /config/custom_components/xiaomi_home/ y añade 'lock', después de 'light', en SUPPORTED_PLATFORMS de miot/const.py.
(Opcional) aplica fix-event-argument-collision.patch.
Reinicia Home Assistant.

Si Xiaomi Home se actualiza, vuelve a aplicar los cambios.

Quién abrió la puerta

El evento event.<...>_operation_log_e_22_1 incluye el tipo de operación y el ID de usuario. Abre una vez con cada huella o clave para saber qué ID corresponde a cada persona. El tipo 7 es huella, 6 clave y 19 puerta cerrada (lista completa en el texto del issue).

Seguridad
Desactiva las entidades de apertura (Bluetooth, emergencia, remota, voz) y no expongas la cerradura a asistentes de voz ni a puentes HomeKit/Matter.
lock.unlock está bloqueado por defecto en lock.py.
El estado 2 significa solo pestillo: la puerta está cerrada pero sin seguro. Activa el cierre automático de la cerradura si quieres que el cerrojo se extienda solo.
No está verificado que las acciones Bluetooth funcionen a través de la nube.
