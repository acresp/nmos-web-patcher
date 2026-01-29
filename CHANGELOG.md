# Changelog

All notable changes to this project are documented in this file.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and uses [Semantic Versioning](https://semver.org/).

---

## [1.7.2] – 2026-01-29

### Fixes

- Senders were not correctly shown in dropdowns of Logical groups page
- Other bugs related to senders/sources terminology changes of 1.7.1...

---

## [1.7.1] – 2025-12-03

### Changed

- **Essence Detection**: improved reliability by determining essence type using /flows
- **Code naming consistency**: changed some "sources" terminology to "senders" to avoid misunderstanding...

---

## [1.7.0] – 2025-11-03

### Added

- **Logical Groups**: added *Disconnect* option in the essence selector (video/audio/anc/none) when creating new logical groups.  
- **Error Handling**: form now properly rejects duplicate logical names or IDs with a clear error message.  
- **Cache System**: extended caching layer to avoid redundant NMOS requests during patch operations.  
  All routing operations now use the local cache, providing a much faster and smoother interface.

### Changed

- **Main Page (Manual Patch View)**: reorganized grid layout by essence type *(Video / Audio / ANC)* for better readability during manual patching.  
- **Logical Page**: dropdowns for senders and receivers are now properly sorted, even on nodes with a large number of endpoints (e.g. SNP).  
- **Logical IDs**: improved contiguous ID allocator to fill gaps automatically when groups are deleted.  
- **BMD Emulator**: automatically reloads and broadcasts after any logical group add/update/delete — no restart required.  
- **Patch Operations**: whenever a patch is performed, the NMOS cache is automatically updated to keep it consistent with the current routing state.

### Fixed

- **Discovery Refresh**: resolved an issue causing multiple node refreshes on application startup.  
  The system now performs a single initialization at boot, followed by periodic refreshes according to the configured interval.

---

## [1.6.1] – 2025-06-16

### Added

- **RossTalk**: minimal integration to support RossTalk XPT commands on port 7788. Enable/disable in Settings page.

#### Changed

- **REST**: /take_many command now use `emit_patch()` function introduced in 1.6.0
- Logical Groups IDs are now beginning at 0 instead of 1. This change is made to reflect more database-style used in majors protocols.
- VideoHub Ethernet Protocol re-index of IDs deleted, was not needed anymore as Logic Groups IDs begins at 0.

---

## [1.6] – 2025-06-16

#### Changed

- **Improved logical group UI**: dropdown selectors for `video`, `audio`, and `data` in logical groups now display the associated node names alongside the IDs, improving readability and usability.
- **More robust NMOS version detection**: node capability detection now works even if a node only exposes senders or receivers, not both. This ensures accurate version discovery in more edge cases.
- **Unified patching backend**: patching operations triggered via the REST API (`/api/take`) and the BMD protocol now rely on a centralized `emit_patch()` function. This provides:
  - parallel execution of video/audio/data patching
  - shared discovery of receivers and sources (single pass)
  - shared `aiohttp` session reuse to reduce network overhead
  - significantly faster patching compared to previous sequential logic
  - consistent behavior between REST and BMD layers

  The manual UI route (`/change_source`) continues to use `change_source()` directly, but is now fully compatible with asynchronous execution.

---

## [1.5.1] – 2025-06-14

### Fixes

- Fix nodes.json management - breaking change introduced with cache management in earlier version
- Nodes aren't stored in cache anymore - only in nodes.json

---

## [1.5] – 2025-06-12

### Added

- **Blackmagic Videohub Ethernet Protocol Support**
  - Added a TCP server emulator for Videohub Protocol v2.3 - can be enabled/disabled in Settings page.
  - Parses and handles input/output routing commands from external BMD controllers
  - Automatically syncs with defined logical groups
  - Triggers real NMOS patches via `emit_patch()` upon incoming routing changes
  - Automatic reload and broadcast when logical mappings change
  - At the moment : tested with Bitfocus Companion & Softron OnTheAir Switch 

- **REST ↔︎ BMD Integration**
  - REST API routes notify the BMD emulator to reflect routing changes in both control layers

---

### Structural Changes

- **Multithreading and Async Task Handling**
  - Isolated thread-safe Flask launch and async BMD task management
  - Runs Flask server and BMD protocol server in parallel using `asyncio.create_task()` and `asyncio.to_thread()`

---

## [1.4.0] – 2025-06-11

### Added
- **REST API** support with multiple endpoints:
  - `GET /api/take`, `take_many`, `disconnect`, `status`, `list`, `ping`
  - Logical routing based on `data_logical.json` mappings (or GUI tab in Settings)
  - JSON responses include `patch_code`, `sender_id`, and `source_name` for automation
  - Endpoint `/api/status` can return the logical source associated with current senders
- New toggle setting: **Enable REST API** in `settings.json` (or Settings menu)
- API documentation now available at [`docs/API.md`](docs/API.md)

### Changed
- Logical group management interface added to the Settings panel:
  - Visual edit/delete of logical sources/receivers
  - `data_logical.json` is now used for automated patching
- Minor design improvements in Settings layout and controls

### Fixed
- Form submission bugs when saving new settings
- Patch now validates presence of all IDs (sender/receiver) before applying
- Better feedback on REST API errors (e.g., `403 REST API disabled`)

### Breaking
- `app.py` has been renamed to `nmos-web-patcher.py` — update your launch commands accordingly!

---

## [1.3.2] – 2025-06-06

### Added
- **Patch Secondary Stream** toggle Y/N in the Settings panel  
  - Allows optional removal of secondary (DUP) streams from SDP  
  - Processed on-the-fly during patch operation - to resolve issue with receivers which don't want missing or invalid IP in environnement without 2022-7.

### Changed
- Moved "Selected Receiver / Current Sender / Selected Source" block into the sticky header area for improved visibility
- Added a footer with version infos
- Saving of settings is now a general functions
- Some cosmetic changes in the WEB UI for better experience

### Fixed

- Removed some unused functions from previous versions

---

## [1.3.1] – 2025-06-05

### Fixed
- Improved sorting of NMOS resources (receivers and sources) for better readability in the UI

---

## [1.3] - 2025-06-05
### Added
- Caching system (data_cache.json) to avoid querying NMOS APIs constantly
- Auto-refresh mechanism with configurable interval (default 300s)
- Settings panel updated with “Other Settings” > “Cache Refresh Interval”

### Changed
- Active Sender check is called only on the necessary endpoint

---

## [1.2.1] – 2025-06-04
### Changed
- Several bug fixes and UI improvements

---

## [1.2.0] – 2025-06-04
### Changed
- Full codebase refactored into modular structure:
  - `routes/` for Flask route separation
  - `services/` for NMOS logic and data handling
  - `templates/` for HTML
- Application can now be run and maintained in a clean, scalable way

### Fixed
- Improved version detection logic to avoid false positives (e.g. SNP bug with HTTP 200 on all endpoints)
- Corrected UI issues related to `settings.html` (broken layout, empty tables)
- Fixed missing receiver/source display on index page

### Added
- Public GitHub repository

---

## [1.0] – 2024-01 *(internal stable build)*
### Added
- Working interface for routing NMOS sources to receivers
- Settings page for node configuration with live version detection
- Version detection via `/x-nmos/` endpoint parsing
- Persistent config storage in `nodes.json`

### Known issues
- Version detection could incorrectly detect supported versions
- Project structure was monolithic (`app.py` only)
