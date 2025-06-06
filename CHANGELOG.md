# Changelog

All notable changes to this project are documented in this file.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and uses [Semantic Versioning](https://semver.org/).

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
- Auto-refresh mechanism with configurable interval (default 10min)
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
