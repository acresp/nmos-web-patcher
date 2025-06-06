# NMOS Web Patcher

> A minimal NMOS IS-05 patchbay — built for engineers who like to keep things clean and simple.

<p align="center">
  <img src="docs/nmos-web-patcher-v1.3.2.png" alt="NMOS Web Patcher Screenshot" width="800">
</p>

<p align="center">
  <a href="https://coff.ee/acresp" target="_blank">
    <img src="docs/bmc-button.png" alt="Buy Me a Coffee" width="200">
  </a>
</p>

---

## Features

- Auto-detection of supported NMOS and IS-05 versions per node
- Visual routing interface (senders ↔ receivers)
- Supports IS-05 `activate_immediate` flow switching
- Color-coded flow types (video, audio, ancillary, metadata)
- Lightweight node manager: add, edit, delete, version detection
- Compatible with devices from Imagine, Ross, Blackmagic, Phabrix, and others
- Modular Flask-based architecture for maintainability and extensibility

---

## Quick Start

### Requirements

- Python 3.9 or newer
- At least one NMOS IS-05 compatible device

### Setup

```bash
git clone https://github.com/acresp/nmos-web-patcher.git
cd nmos-web-patcher
pip install -r requirements.txt
python app.py
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

## ToDo

* Bulk patching
* Better check for the essence type (color coding/cosmetic...)
* Better UI with nodes groups
* Simple REST API to make patches like http://localhost:5000/patch?src=1&dest=1 for easier integration in automations softwares
* Sky is the limit...

## License

Copyright © Arnaud Cresp

## One more thing...

Wherever you're patching from — if this tool helped, say hi or open an issue. I'd love to hear where it's being used. :)
