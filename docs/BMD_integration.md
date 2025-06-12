# Blackmagic Videohub Protocol Integration

This page demonstrates the integration of the **Blackmagic Videohub Ethernet Protocol** with the **NMOS Web Patcher**.

The built-in emulator allows external systems — such as **Bitfocus Companion**, custom panels or Videohub-compatible software — to connect over TCP and trigger real-time routing actions.

---

## Getting Started

1. Activate it directly from the **Settings panel** in the Web UI.
2. The emulator will listen on TCP port `9990`.

---

## Example Integration: Bitfocus Companion

The emulator responds to standard Videohub protocol commands. Here’s a basic setup in **Bitfocus Companion**:

<p align="center">
  <img src="docs/nmos_companion.png" alt="NMOS Web Patcher in Companion" width="800">
</p>

> * Connection to the NMOS Web Patcher’s emulator
> * Button triggering routing change (e.g. Output 2 ← Input 1)
> * Feedback showing current route

Example for the Receivers, you can see that it's reflecting the logical groups defined in the database.

<p align="center">
  <img src="docs/nmos_companion_logical.png" alt="NMOS Web Patcher in Companion" width="800">
</p>

---

## Notes

* Labeling and routing is based on logical groupings
* Changes are immediately reflected in the NMOS IS-05 system
* Works concurrently with REST API and Web UI — all actions stay in sync

---

For more technical details, see `/protocols/bmdvideohub.py` in the source code.
