# Design

`arena-allocator` hands out memory from a buffer the caller provides by moving one offset forward, and takes it back only in bulk: everything above a saved marker, or everything at once. This document describes the bump model, alignment, markers and the high-water mark, debug poisoning, storage units on 16-bit-MAU targets, the concurrency contract, and how the library is verified. The API is in [api.md](api.md).

## Goals

- No heap: the arena never allocates its own memory, and the caller decides where the buffer lives.
- Allocation in constant time, independent of how many allocations came before.
- Release in bulk, so a function's or a frame's temporary memory is reclaimed in one step and fragmentation cannot occur.
- Misuse the arena can detect, such as a NULL argument, a zero size, an invalid alignment or an overflowing array size, returns a status and leaves the arena unchanged.
- Portable C11, including targets where `CHAR_BIT` is 16.

Freeing individual blocks, growing the buffer, and sharing one arena between concurrent contexts are out of scope.

## The arena

`arena_t` holds the start and capacity of the buffer, the current offset into it, the high-water mark, the poison pattern, and the status of the last allocation. The structure has the same layout in every configuration, so a caller and a library built with different `ARENA_CFG_*` values agree on it.

The used size is the current offset. Everything below it has been handed out; everything from it to the capacity is free. The arena keeps no record of individual blocks, which is why a block cannot be freed on its own and why the bookkeeping costs a fixed few words regardless of the number of allocations.

## Allocation

An allocation takes the address at the current offset, rounds it up to the requested alignment, checks that the block fits between that address and the end of the buffer, and moves the offset to the end of the block. The work is a handful of integer operations with no loop, so its time does not depend on the arena's history. The zeroing variants add one pass over the new block.

Alignment is computed on the address, through `uintptr_t`, rather than on the offset. A buffer placed at any address therefore yields correctly aligned blocks; the padding needed varies with the placement. The rounding saturates rather than wrapping, and a saturated result is reported as `ARENA_STATUS_OUT_OF_MEMORY`. The fit is checked against the remaining capacity, never by forming an address past the buffer, so no check depends on pointer arithmetic that could overflow.

`arena_init` rejects a buffer whose end would pass `UINTPTR_MAX`, which is what lets every later address computation stay in range. The array forms check `element_size * count` against `SIZE_MAX` before multiplying.

A failed allocation sets the caller's result pointer to NULL and leaves the offset and the high-water mark as they were.

## Markers and the high-water mark

A marker is the current offset, saved by value. Rewinding to a marker sets the offset back to it, which releases every allocation made after it in one step. Markers nest naturally: a function that takes a marker on entry and rewinds before returning leaves the arena exactly as it found it, whatever its callees did in between.

A rewind accepts any marker at or below the current offset and ignores a larger one. The check stops a stale marker from extending the used region into memory that was never handed out, but it cannot tell a marker from this arena's past from any other offset in range. A marker taken before a reset and used after the arena has grown past it again releases whatever is above it. Pair each marker with the scope that created it.

The high-water mark is the largest offset the arena has reached since `arena_init`. Rewinds and resets leave it alone, so after a test run it gives the buffer size the workload needed, padding included.

## Debug poisoning

With `ARENA_CFG_DEBUG_POISON` enabled, `arena_init` fills the whole buffer with `ARENA_CFG_POISON_PATTERN`, and `arena_rewind` and `arena_reset` fill everything from the new offset to the end of the buffer. Free memory therefore always holds the pattern, and a read through a pointer that outlived its rewind returns recognisable values instead of plausible stale data. Allocation does not touch the block, so a new block also starts with the pattern unless it is zeroed.

Poisoning makes init, rewind and reset take time proportional to the free space, so it is a test and debug aid. With it disabled, rewind and reset are constant time.

## Storage units on 16-bit-MAU targets

The library uses `unsigned char` for the buffer and `size_t` for every count, and computes nothing in octets. On a target where `CHAR_BIT` is 16, `sizeof` and therefore every size, alignment, marker and usage figure counts 16-bit words. `ARENA_CFG_DEFAULT_ALIGNMENT` of 8 aligns to 8 words, and a 32-bit object needs 2 units. The typed macros take `sizeof` and `_Alignof` from the type, so they need no change between targets. The poison pattern fills each word with the configured value, 0x00AA by default.

## Concurrency

An arena is not safe to use from two contexts at once, and that includes queries. Allocation reads and then writes the offset, so two concurrent allocations can return overlapping blocks, and a reader can see the offset and the high-water mark at different moments. A caller that shares an arena between tasks, or between a task and an interrupt handler, must serialise every call. Separate arenas, each with its own buffer, share nothing and need no coordination.

## Failure behaviour

| Condition | Result |
| --- | --- |
| NULL arena or buffer to `arena_init` | `ARENA_STATUS_NULL_POINTER`; nothing is written. |
| Zero size, or a buffer that would pass `UINTPTR_MAX` | `ARENA_STATUS_INVALID_ARGUMENT` from `arena_init`; nothing is written. |
| NULL result pointer | `ARENA_STATUS_NULL_POINTER`; the status is recorded on a non-NULL arena. |
| NULL arena to an allocation | `ARENA_STATUS_NULL_POINTER`; `*result` is NULL. |
| Alignment not a power of two | `ARENA_STATUS_INVALID_ALIGNMENT`; `*result` is NULL. |
| Zero size, element size or count, or an overflowing array size | `ARENA_STATUS_INVALID_ARGUMENT`; `*result` is NULL. |
| Block does not fit | `ARENA_STATUS_OUT_OF_MEMORY`; `*result` is NULL and the arena is unchanged. |
| NULL arena to a marker, rewind, reset or query | `ARENA_MARKER_INVALID`, no effect, or 0. |
| Marker above the used size | Ignored by `arena_rewind`. |
| Stale marker within the used size | Accepted; releases whatever lies above it. |
| Arena used before `arena_init` | Undefined; the members hold arbitrary values. |
| Concurrent calls on one arena | Undefined; the caller must serialise them. |
| `ARENA_CFG_DEFAULT_ALIGNMENT` not a power of two | Compile error from a `_Static_assert` in `src/arena.c`. |

## MISRA C:2023

The library is analysed with [`misch`](https://pypi.org/project/misch/), a cppcheck-based MISRA C:2023 checker, over `include/` and `src/`, once with the default configuration and once with `ARENA_CFG_DEBUG_POISON` enabled. Each run has its own baseline of accepted findings in `analysis/baseline/`, and CI fails on any finding outside it. The default build has 43 findings:

| Rule | Findings | Cause |
| --- | --- | --- |
| 15.5 | 21 | Early returns, which reject invalid arguments before any work. |
| 8.7 | 12 | Public functions with no caller outside `src/arena.c` in the analysed code. |
| 2.5 | 4 | The typed allocation macros, which no analysed file expands. |
| 11.5 | 2 | Conversions from `void *` to `unsigned char *` for the buffer and the fill helper. |
| 11.4 | 1 | The buffer start converted to `uintptr_t` for alignment. |
| 11.6 | 1 | The buffer pointer converted to `uintptr_t` for the overflow check in `arena_init`. |
| 17.8 | 1 | The alignment parameter replaced by the default when it is 0. |
| 18.4 | 1 | Pointer addition that forms the returned block address. |

The poisoning build has the same findings and one more 18.4, for the pointer addition that locates the free region on rewind. The baselines record the findings as they stand. Formal compliance needs a certified analyser and a deviation record from the consuming project.

## Verification

The tests run on the host:

| Test | What it checks |
| --- | --- |
| `arena_test` | Initialisation, including size overflow; every NULL, zero and invalid-alignment argument; alignment boundaries and mask arithmetic; exact-capacity and out-of-memory allocation; the zeroing and array forms, including overflow; the typed macros, the `_ptr` functions and the last status; markers, invalid and NULL markers, scoped temporary use, used size and high-water transitions. |
| `arena_poison_test` | With poisoning enabled and a non-default pattern: the fill on init, on rewind of the free tail only, and on reset. |
| `arena_install_smoke` | Installs the library into a temporary directory and builds and runs a consumer through each include path: the `arena/` subdirectory, the root forwarding headers, and the `pkg-config` directory. Plain builds only. |
| Typed macro probes | At configure time, a typed macro must compile with a pointer result and must fail to compile with a non-pointer one. |
| `arena docs examples` | Every C block in the README, `CONTRIBUTING.md` and `docs/` compiles against the public headers. |

CI runs the tests under AddressSanitizer and UndefinedBehaviorSanitizer and checks that the poisoning and install smoke tests are registered. It gates line and branch coverage of `src/` and `include/` at 100 percent, builds the library in release mode, checks formatting, and runs the MISRA analysis for both configurations. It also compiles the library with warnings as errors under TI C2000 CGT 22.6.2 and 25.11.1, in both the COFF and EABI formats.
