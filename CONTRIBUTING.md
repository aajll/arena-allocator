# Contributing to arena-allocator

`arena-allocator` is a small C11 arena (bump) allocator. A block handed out twice, or an offset moved past the buffer, corrupts whatever the caller stored there, so read [design.md](docs/design.md) before you change allocation, alignment or markers.

## Getting started

Install a C11 compiler and install the Python tools with [uv](https://docs.astral.sh/uv/), as CI does. The MISRA analysis also needs a current `cppcheck`; CI installs it from Homebrew because the 2.13 release in Ubuntu 24.04 reports different findings. The same commands CI runs, locally:

```sh
# Python tools
uv tool install meson
uv tool install ninja
uv tool install gcovr
uv tool install misch

# Configure with tests and sanitisers (CI default)
meson setup build --buildtype=debug -Dbuild_tests=true -Db_sanitize=address,undefined
meson compile -C build
meson test -C build --verbose

# Release build (the configuration a downstream consumer uses)
meson setup build-rel --buildtype=release -Dbuild_tests=false
meson compile -C build-rel

# Plain build, which adds the install smoke test
meson setup build-plain --buildtype=debug -Dbuild_tests=true
meson compile -C build-plain && meson test -C build-plain

# Coverage (CI gate is 100% line and branch)
meson setup build-cov --buildtype=debug -Dbuild_tests=true -Db_coverage=true
meson compile -C build-cov && meson test -C build-cov
gcovr --root . --filter 'src/' --filter 'include/' --fail-under-line 100 --fail-under-branch 100 --print-summary build-cov

# MISRA C:2023, default build and debug poisoning (reads build/compile_commands.json)
env -u MISRA_RULE_TEXTS misch run --baseline
env -u MISRA_RULE_TEXTS misch run --baseline --profile poison
misch deviations

# Formatting (pinned clang-format through uvx)
scripts/format.sh --fix
```

## Source style

- Formatting is mandatory. Run `scripts/format.sh --fix` before submitting, or `scripts/format.sh` to check without writing, as CI does. The script pins the clang-format release and runs it through `uvx`, so an editor formatter gives the same result only when it runs the same release.
- 8-space indent, Linux brace style, 80-column limit. Match the existing conventions and do not reformat unrelated code.
- The Meson build system is the single source of truth. Update `meson.build` and `tests/meson.build` when you add or remove files. No CMake, no Make, and no other build systems.

## C language rules

- C11 only.
- Use `size_t` for sizes and offsets, `uintptr_t` for address arithmetic, and `unsigned char` for buffer storage, so the code builds where `CHAR_BIT` is 16 and `uint8_t` does not exist.
- No heap allocation (`malloc`, `free`, VLAs), no recursion, no system calls, and no global state.
- Validate every pointer argument at the public API boundary and return a status rather than fault.
- Every public identifier uses the `arena_` or `ARENA_` prefix.

## Arena rules

- Check every bound with offsets against the remaining capacity, never by forming a pointer past the buffer.
- A failed allocation sets `*result` to NULL and leaves the offset and the high-water mark unchanged.
- Allocation stays constant time. Only zeroing and poisoning may touch the buffer.
- `arena_t` has one layout in every configuration. A configuration macro that changes it would make callers and the library disagree, and needs an issue first.

## MISRA C:2023

The library is analysed with `misch` (cppcheck-backed MISRA C:2023 analysis), configured by `misra.toml`, over `include/` and `src/`, once with the default configuration and once with the `poison` profile, which enables `ARENA_CFG_DEBUG_POISON`. CI fails on any finding that is not in that profile's baseline in `analysis/baseline/`. Run it from a configured `build/` directory, with `MISRA_RULE_TEXTS` unset, as CI does. If your change introduces a finding:

1. Prefer restructuring the code so the rule is satisfied. Deviate only when compliance would make the code genuinely worse, and never restructure purely to hide a finding from the checker; an honest deviation beats evasion.
2. Suppress at the point of use with `/* cppcheck-suppress misra-c2012-<rule> ; @deviation <rationale> */`, or add a justified project-wide entry to `analysis/deviations/misra-deviations.txt` for a house-style rule.
3. Verify with `misch run --baseline` for both profiles and `misch deviations`, which requires every suppression to carry a rationale, and justify the deviation in the pull request description.

Do not regenerate a baseline to admit a new finding. It changes only after a deliberate review, with `misch baseline`.

## Tests and coverage

- Add a test for every bug fix and every new feature.
- `test_arena` runs the cases in `tests/test_arena_api.c`, `tests/test_arena_allocation.c` and `tests/test_arena_markers.c`. `tests/test_arena_poison.c` builds its own copy of the library with poisoning enabled. Each new file is listed in `tests/meson.build`.
- Test each guard with the input that reaches it, including NULL arguments, zero sizes, invalid alignments, overflowing array sizes and a full arena.
- CI enforces 100 percent line and branch coverage of `src/` and `include/`. Every new branch needs a test that fails when the branch is broken.
- The `arena docs examples` test compiles every C code block in `README.md`, `CONTRIBUTING.md`, and `docs/` against the public headers, through `tests/docs/check_snippets.py`. A block compiles at file scope by default. On the line directly above the fence, put `<!-- snippet: body -->` for a block of statements, or `<!-- snippet: skip -->` for pseudo-code or a copy of a header definition.

## Documentation

| File | Purpose |
| --- | --- |
| `README.md` | Landing page: quick start, description, validated toolchains, and links. Keep it short. |
| `docs/integration.md` | Requirements, installation, configuration, building, and cross builds. |
| `docs/api.md` | Reference for initialisation, allocation, the typed macros, markers and reset, queries, the configuration macros, and recipes. |
| `docs/design.md` | The bump model, alignment, markers and the high-water mark, poisoning, storage units on 16-bit-MAU targets, concurrency, failure behaviour, MISRA position, and verification. |

Update `docs/api.md` and the header Doxygen together when an interface changes, and check every value an example states against a build. Update `docs/design.md` when allocation, markers, poisoning or the verification changes. Keep it standalone: describe how the library works, not how it was built or which other projects use it. Write prose in British English, one line per paragraph.

## API stability

- The function signatures and macros in `arena.h` and the configuration macros in `arena_cfg.h` are stable within a major release line.
- The values of `arena_status_t` are part of the contract, because callers store and transmit them.
- The members of `arena_t` are private, but its size is not: callers allocate it, so a layout change needs a `CHANGELOG.md` entry.

## Commits

Use Conventional Commits:

- `feat: ...` new feature
- `fix: ...` bug fix
- `docs: ...` documentation only
- `test: ...` test-only changes
- `chore: ...` build, CI, release work
- `refactor: ...` a change that neither fixes a bug nor adds a feature

Keep the subject under about 70 characters. Use the body to explain why the change is needed.

## Pull requests

- Open an issue first for non-trivial changes, so the design can be agreed before implementation.
- Keep pull requests focused: one feature or one fix.
- All CI checks must pass.
- Add a `CHANGELOG.md` entry under `## [Unreleased]` for a user-visible change.
- Flag any new MISRA deviation, and any change to the layout of `arena_t`, in the description.

## When in doubt

Open an issue. The library is small, but every firmware that carves its working memory from it trusts that no two live blocks overlap.
