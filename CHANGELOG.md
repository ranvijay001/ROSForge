# Changelog

All notable changes to ROSForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-24

### Added
- Auto build verification and fix loop (`--max-fix-attempts`)
- Interactive migration mode (`--interactive`)
- Batch workspace migration (`rosforge migrate-workspace`)
- Custom transformation rules via YAML (`--rules`)
- Cost estimation display before migration
- Confidence scoring in CLI output
- Pre-migration confirmation prompt (`--yes` to skip)
- Bridge/fallback guidance for untranslatable packages

### Changed
- Updated CLI help text for analyze and status commands
- Improved launch rule conversion for `<machine>` and `<test>` tags
- Updated PromptBuilder to support custom rule merging

## [0.1.0] - 2026-02-24

### Added
- Initial release with complete ROS1 to ROS2 migration pipeline
- Five pipeline stages: Ingest, Analyze, Transform, Validate, Report
- BYOM engine support: Claude (CLI/API), Gemini (CLI/API), OpenAI (CLI/API)
- Static knowledge base: API mappings, CMake rules, package.xml rules, launch rules, msg/srv rules
- Full parser suite: Python source, launch XML, msg/srv, CMake, package.xml
- CLI commands: migrate, analyze, config, status
- Jinja2 migration report with git diff
- Telemetry with opt-in local logging
- 692 tests (unit, integration, e2e)
