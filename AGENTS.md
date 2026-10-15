# AGENTS.md

---

## 1) Project-specific instructions

**Project:** `arena-allocator`
**Primary goal:** A C11 arena (bump) allocator over a caller-provided buffer: aligned allocation in constant time, released in bulk by a reset or a rewind to a saved marker. No heap, no system calls, no global state.

### 1.1 Essential commands

#### Configure and build (library only)

```sh
meson setup build --wipe --buildtype=release -Dbuild_tests=false
meson compile -C build
```

#### Configure, build, and run unit tests

```sh
meson setup build --wipe --buildtype=debug -Dbuild_tests=true -Db_sanitize=address,undefined
meson compile -C build
meson test -C build --verbose
```

`arena_poison_test` in this suite runs against a copy of the library built with `ARENA_CFG_DEBUG_POISON`. `arena_install_smoke` runs only in builds without sanitisers or coverage.

#### MISRA C:2023, default build and debug poisoning (reads `build/compile_commands.json`)

```sh
env -u MISRA_RULE_TEXTS misch run --baseline
env -u MISRA_RULE_TEXTS misch run --baseline --profile poison
misch deviations
```

#### Formatting (pinned clang-format through `uvx`)

```sh
scripts/format.sh          # check, as CI does
scripts/format.sh --fix    # rewrite in place
```

Coverage commands are in `CONTRIBUTING.md`.

### 1.2 Notes

- `include/arena.h` defines the version macros, and `meson setup` fails when they differ from `project(version:)`, so a release updates both.
- The build produces only a static library, installed as `libarena.a` with headers under `arena/`, deprecated forwarding headers at the include root, and `arena.pc`. The only Meson option is `build_tests`.
- The `ARENA_CFG_*` macros are read only by `src/arena.c` and do not change `arena_t`. Set them where the library is compiled.

---

## 2) Non-negotiable design invariants

- **Constant-time allocation.** Allocation has no loop except the optional zeroing. Poisoning is the only other code that walks the buffer.
- **No overlap.** A live block is never handed out again until a rewind or reset releases it.
- **Checked bounds.** Fit is checked with offsets against the remaining capacity; no pointer is formed past the buffer. `arena_init` rejects a buffer that would pass `UINTPTR_MAX`, and array sizes are checked against `SIZE_MAX` before multiplying.
- **Fail clean.** A failed allocation writes NULL to `*result` and leaves the offset and high-water mark unchanged. A rewind to a marker above the used size is ignored.
- **One layout.** `arena_t` is the same in every configuration.
- Not thread-safe. No heap, no system calls, no blocking, no global state.

---

## 3) CI / source of truth

- CI definitions live in `.github/workflows/ci.yml`.
- Prefer running the same commands locally as CI runs (see §1.1 above).
- Install Python tools (Meson, Ninja, gcovr, misch) with `uv tool install`, never `pip`; CI does the same through `astral-sh/setup-uv`. CI installs `cppcheck` for the MISRA job from Homebrew because Ubuntu's 2.13 reports different findings.
- `misch run --baseline` must pass against `analysis/baseline/` for both profiles. Never regenerate a baseline to admit a new finding. Run it with `MISRA_RULE_TEXTS` unset, as CI does.
- The CI jobs are: tests under ASan/UBSan with a check that the poisoning and install smoke tests are registered, a release build, a 100 percent line and branch coverage gate, a TI C2000 library build (CGT 22.6.2 and 25.11.1, COFF and EABI, warnings as errors), `clang-format`, and `misch` for both profiles.

---

## 4) Docs / commit conventions

### Documentation layout

- `README.md` is a short landing page (under 100 lines). Put detail in `docs/`, never in the README; link to the owning file instead.
- `docs/integration.md` owns requirements, install methods, configuration, building, and cross builds.
- `docs/api.md` owns the API reference, the configuration macros and recipes. Change it together with the headers; keep signatures in fenced `c` blocks and describe them in prose, not function tables. Check every value an example states against a build.
- `docs/design.md` is the single authoritative design record: the bump model, alignment, markers and the high-water mark, poisoning, storage units on 16-bit-MAU targets, concurrency, failure behaviour, MISRA position, and verification.
- `CONTRIBUTING.md` documents the contributor workflow; `CHANGELOG.md` holds release history (Keep a Changelog); `.github/SECURITY.md` covers vulnerability reporting.
- Code blocks in `README.md`, `CONTRIBUTING.md`, and `docs/` are compiled by the `arena docs examples` test (`tests/docs/check_snippets.py`). Each document is compiled as one source file: a `c` fence is file-level code, `<!-- snippet: body -->` wraps statements, and `<!-- snippet: skip -->` excludes pseudo-code. Do not use `skip` to silence a broken example.
- Prose uses British spelling. Do not hard-wrap Markdown: write one line per paragraph. The 80-column limit applies to C source, not Markdown.

### Commits

- Use **Conventional Commits** format when asked to commit.
- Keep commits focused; explain *why* in the message body.

---

## 5) C style expectations

### Build & configuration

- Use the Meson build system. Do not introduce CMake, Make, or other systems.
- Update `meson.build` and `tests/meson.build` when adding or removing files.
- `arena_cfg.h` is public and installed beside `arena.h`. Every option stays behind an `#ifndef` guard.

### Formatting

- `.clang-format` is present and **mandatory**. Run `scripts/format.sh --fix` before committing. It runs the clang-format release pinned in the script through `uvx`. Do not use a system `clang-format`: another release can format the same code differently.
- Do not reformat unrelated code.
- Key settings: 8-space indent, `BreakBeforeBraces: Linux`, column limit 80.

### Style & correctness

- Match conventions in the existing files (indentation, braces, naming).
- Every public identifier uses the `arena_` or `ARENA_` prefix. Keep public headers minimal; do not expose internal helpers.
- Validate pointer arguments at every public API boundary; no `errno`.
- Use `size_t` for sizes and offsets, `uintptr_t` for addresses and `unsigned char` for buffer storage, so the code builds where `CHAR_BIT` is 16.
- `arena_status_t` values are part of the API; changing one is a breaking change. A change to the layout of `arena_t` needs a `CHANGELOG.md` entry.
- Public symbols carry Doxygen with the full contract: preconditions and return semantics.

### MISRA deviations

- Prefer compliant code; never restructure only to hide a finding. Deviate at the point of use with `/* cppcheck-suppress misra-c2012-<rule> ; @deviation <rationale> */`, or project-wide in `analysis/deviations/misra-deviations.txt` for a house-style rule.

### Comment placement (Doxygen)

- Inline trailing annotations (`/**< ... */`) on `enum`/`struct` members are allowed only when the resulting line fits the 80-column limit.
- If any member's annotation would overrun, move **all** of that aggregate's member docs into a single structured Doxygen block above the type, as an `@details` list of `- ::SYMBOL  description` entries.
- Never mix inline and block forms within one aggregate, and never leave a trailing comment that clang-format would wrap onto a second line.
- After editing, run `scripts/format.sh` and an 80-column scan.

### Testing

- Run `meson test -C build` after every change.
- Unit tests live in `tests/test_arena_*.c`, run by `tests/test_arena.c`; poisoning tests in `tests/test_arena_poison.c`. Do not add Unity or another external framework.
- Test each guard with the input that reaches it: NULL arguments, zero sizes, invalid alignments, overflowing array sizes, a full arena.
- Add a test case for each bug fix and each new feature.
- Keep `src/` and `include/` at the coverage gate (100 percent line and branch).
