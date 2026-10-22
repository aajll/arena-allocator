# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.2.0] - 2026-10-22

### Added

- Support for targets where `CHAR_BIT == 16`: the buffer pointer, fill helper and poison cache use `unsigned char` instead of `uint8_t`, and the 8-bit-byte assertion is gone. Layout is unchanged on byte-addressed targets.
- `arena_alloc_array_ptr()` and `arena_alloc_array_zero_ptr()` return the allocated block directly, and `arena_get_last_status()` reports the status every allocation function now records on the arena.
- CI cross-builds the library with TI C2000 CGT 22.6.2 and 25.11.1, COFF and EABI, with warnings as errors.

### Changed

- `arena.h` defines `ARENA_VERSION_MAJOR`, `_MINOR`, `_PATCH`, `ARENA_VERSION` and the new `ARENA_VERSION_STRING` and `ARENA_VERSION_NUMBER` (`long`, `MAJOR * 10000 + MINOR * 100 + PATCH`), so a copied-in header carries its version. Meson fails to configure when the header and `project(version:)` disagree, and the build needs Meson 0.57 or later.
- `arena.h` and `arena_cfg.h` install under `${includedir}/arena/`, where the pkg-config file already points.
- CI gates line and branch coverage at 100 %. Two defensive checks that no input could reach are removed: the internal size helper's NULL check and the post-alignment wrap check, which `align_up()` already prevents.
- `arena_t` gains a `last_status` field. Its fields remain internal, so code that declares arenas and uses the API is unaffected.
- CI runs a MISRA C:2023 analysis with `misch`, for the default build and with `ARENA_CFG_DEBUG_POISON`, against baselines in `analysis/baseline/` that record the existing findings, and checks formatting with the clang-format release pinned in `scripts/format.sh`. Three declarations and macros are reformatted to match it.
- The README is a short landing page, with the integration guide, API reference and design record in `docs/`. `CONTRIBUTING.md` and `AGENTS.md` follow the same layout, and an `arena docs examples` test compiles every C example in the documentation.
- CI installs Meson, Ninja and gcovr with `uv` instead of `pip`, and the Meson files and tests carry SPDX licence headers.
- Standardised project metadata, SPDX headers, security policy, pkg-config generation, installed version header, contributor guidance, and CI coverage thresholds with the primitive family baseline.

### Deprecated

- The forwarding headers installed at `${includedir}/arena.h` and `${includedir}/arena_cfg.h`. Include `<arena/arena.h>` or use the pkg-config include path; the forwarders will be removed in the next major release.

### Removed

- `arena_version.h`. `arena.h` defines the version macros.

### Fixed

- `ARENA_ALLOC_OBJECT`, `ARENA_ALLOC_ARRAY` and their `_ZERO` variants no longer cast the result to `void **`, which stored a `void *` into a typed pointer object (undefined behaviour under the aliasing rules) and accepted non-pointer results. They assign through ordinary conversion and still evaluate to `arena_status_t`. The `arena` argument is now evaluated twice.

## [1.1.8] - 2026-03-10

### Fixed

- Corrected the exported Meson library dependency and generated `arena_version.h` into the build directory for consumers.

## [1.1.7] - 2026-03-06

### Fixed

- Made the install smoke test detect Meson multiarch library directory layouts.

## [1.1.3] - 2026-03-03

### Fixed

- Resolved MISRA C:2012 audit findings around header guards, unused includes, NULL marker handling, const-correct prototypes, Rule 11.6 documentation, and marker/alignment regression tests.
