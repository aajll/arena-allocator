# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Support for targets where `CHAR_BIT == 16`: the buffer pointer, fill helper and poison cache use `unsigned char` instead of `uint8_t`, and the 8-bit-byte assertion is gone. Layout is unchanged on byte-addressed targets.
- `arena_alloc_array_ptr()` and `arena_alloc_array_zero_ptr()` return the allocated block directly, and `arena_get_last_status()` reports the status every allocation function now records on the arena.
- CI cross-builds the library with TI C2000 CGT 22.6.2 and 25.11.1, COFF and EABI, with warnings as errors.

### Changed

- `arena_t` gains a `last_status` field. Its fields remain internal, so code that declares arenas and uses the API is unaffected.
- Standardised project metadata, SPDX headers, security policy, pkg-config generation, installed version header, contributor guidance, and CI coverage thresholds with the primitive family baseline.

### Fixed

- `ARENA_ALLOC_OBJECT`, `ARENA_ALLOC_ARRAY` and their `_ZERO` variants no longer cast the result to `void **`, which stored a `void *` into a typed pointer object (undefined behaviour under the aliasing rules) and accepted non-pointer results. They assign through ordinary conversion and still evaluate to `arena_status_t`. The `arena` argument is now evaluated twice.
- `arena_version.h` now defines `ARENA_VERSION` as a single string literal and `ARENA_VERSION_MAJOR`, `_MINOR` and `_PATCH` as integers, so the macros compile when used.

## [1.1.8] - 2026-03-10

### Fixed

- Corrected the exported Meson library dependency and generated `arena_version.h` into the build directory for consumers.

## [1.1.7] - 2026-03-06

### Fixed

- Made the install smoke test detect Meson multiarch library directory layouts.

## [1.1.3] - 2026-03-03

### Fixed

- Resolved MISRA C:2012 audit findings around header guards, unused includes, NULL marker handling, const-correct prototypes, Rule 11.6 documentation, and marker/alignment regression tests.
