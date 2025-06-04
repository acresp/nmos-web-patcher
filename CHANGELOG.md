# Changelog

All notable changes to this project are documented in this file.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and uses [Semantic Versioning](https://semver.org/).

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
