# NMOS Web Patcher

A minimal NMOS IS04/IS-05 patchbay — built for engineers who like to keep things clean and simple.

<p align="center">
  <img src="docs/nmos-web-patcher-v1.3.2.png" alt="NMOS Web Patcher Screenshot" width="800">
</p>

---

## Features

- Auto-detection of supported NMOS IS-04 and IS-05 versions per node
- Visual routing interface (senders ↔ receivers)
- Supports IS-05 `activate_immediate` flow switching
- Color-coded flow types (video, audio, ancillary, metadata)
- Lightweight node manager: add, edit, delete, version detection
- Compatible with devices from Imagine, Ross, Blackmagic, Phabrix, and others
- Modular Flask-based architecture for maintainability and extensibility
- REST API available for automation and external integrations ([API Documentation](docs/API.md))
- Blackmagic Videohub Ethernet Protocol emulation (see [Bitfocus Companion integration example screenshots](docs/BMD_integration.md)) 

---

## Quick Start

### Requirements

- Python 3.9 or newer
- At least one NMOS IS-04/IS-05 compatible device

### Setup

```bash
git clone https://github.com/acresp/nmos-web-patcher.git
cd nmos-web-patcher
pip install -r requirements.txt
python3 nmos-web-patcher.py
```
Then visit http://localhost:5000 in your browser and add your first NMOS node in the Settings page :)

---

## Device compatibility

The application has been tested and is able to patch signals with the following hardware:

* Imagine Communications SNP Processor
* Ross Ultrix IPX card
* Blackmagic Decklink IP
* Blackmagic Converters (2110 to HDMI & 3x3G)
* Phabrix Qx
* Riedel/Embrionix emSFP

## Roadmap

* Ongoing bug fixes for improved stability  

* Currently, patching logic differs depending on the protocol:
- **BMD/VideoHub protocol** uses a centralized `emit_patch()` function which performs concurrent patching of video, audio, and data essences using asyncio. This provides good responsiveness and parallel execution.
- **REST API** directly calls `change_source()` for each essence in sequence. This approach is functional but lacks the concurrency and shared logic used in the BMD path.

The plan is to **unify both paths** by having REST also rely on the same `emit_patch()` backend, ensuring consistent behavior and enabling future enhancements (like IS-05 bulk patching or logical group-level routing) with a single source of truth.

* Support for IS-05 bulk patching to speed up group operations (as said in previous)
* Additional protocol support based on future needs (e.g. RossTalk)  
* **Contributions, ideas, and tested device feedback are welcome** — feel free to open issues or pull requests.

## License

Copyright © Arnaud Cresp

## One more thing...

Wherever you're patching from — if this tool helped, say hi or open an issue. I'd love to hear where it's being used.

<p align="center">
Want to support me ? :)<br>
  <a href="https://coff.ee/acresp" target="_blank">
    <img src="docs/bmc-button.png" alt="Buy Me a Coffee" width="200">
  </a>
</p>