# RossTalk

## RossTalk Emulator – Minimal Emulation of Ultrix™ Behavior

This emulator provides a **minimal RossTalk implementation**

---

## Supported Command

### `XPT` — Crosspoint Routing

This is the only supported and processed command. It allows a controller to request that a source (input) be routed to a destination (output) - related to Logic Groups database.

**Syntax:**
```
XPT I:<user-id> D:<dest> S:<source> [L:<levels>]
```

- `D:` → Destination logical ID (receiver)
- `S:` → Source logical ID (sender)
- `I:` and `L:` are **accepted but ignored ATM**.
- The command must be **terminated with CRLF** (`\r\n`).

**Example:**
```
XPT I:1 D:4 S:8 L:1-17
```

This command will patch logical source `8` to logical destination `4`.

**But a minimal command is also accepted like:**
```
XPT D:5 S:0
```

This command will patch logical source `0` to logical destination `5`.

**Behavior:**
- Valid source and destination IDs are looked up from the logical group configuration.
- If both are known, a patch is triggered via the NMOS stack.
- No response is sent to the client (silent acknowledgment), mimicking Ultrix.

---

## Ignored or Unsupported Commands

All other commands are silently **ignored**. This includes, but is not limited to:

- `GPI`, `TIMER`, etc.

These commands are **not processed** and do **not generate a response**

---

## Notes

- The emulator listens by default on **port 7788** (`0.0.0.0:7788`), like Ross Ultrix.
- Logical IDs are derived from the `sources` and `receivers` defined in `data_logical.json`.
- `emit_patch(sender_id, receiver_id, origin="RossTalk")` is used for NMOS-level routing.

---

## Intended Use

This module is intended for **automated control systems**, **tally controllers**, or **RossTalk-based patchers** targeting an Ultrix-like router. It does not implement the full RossTalk specification and should be used where **minimal compatibility** is sufficient.

---