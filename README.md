# arena-allocator

[![CI](https://github.com/aajll/arena-allocator/actions/workflows/ci.yml/badge.svg)](https://github.com/aajll/arena-allocator/actions/workflows/ci.yml)

A deterministic arena (bump) allocator in C for safety-critical embedded systems.

## Features

- **No dynamic memory** — fixed-size static buffers; no `malloc` / `free`.
- **Deterministic allocation** — O(1) allocation with no branching or overhead.
- **Checkpointing** — save and restore arena state with markers for scoped allocations.
- **High-water tracking** — monitor maximum memory usage for static analysis.
- **Typed helpers** — optional object/array wrappers remove repetitive size/alignment code.
- **Zeroing helpers** — opt-in zero-initialised allocation for state that must start clean.
- **Debug poisoning** — optional fill with known patterns to detect use-after-free.

## Installation

### Copy-in (recommended for embedded targets)

Copy three files into your project tree -- no build system required:

```
include/arena.h
include/arena_cfg.h
src/arena.c
```

Place them in the same directory, then include the header:

```c
#include "arena.h"
```

### Meson subproject

Add this repo as a wrap dependency or subproject. The library exposes an
`arena_dep` dependency object that carries the correct include path:

```meson
arena_dep = dependency('arena-allocator', fallback : ['arena-allocator', 'arena_dep'])
```

### Installed library

`meson install` places the static library, a pkg-config file and the headers under `${includedir}/arena/`. Include `<arena/arena.h>` with the include root on the search path, or `"arena.h"` with the pkg-config flags, which point into `arena/`. Forwarding headers at `${includedir}/arena.h` and `${includedir}/arena_cfg.h` keep `#include <arena.h>` working without pkg-config; they are deprecated and will be removed in the next major release.

## Quick Start

```c
#include <stdio.h>
#include "arena.h"

int main(void)
{
        static uint8_t buffer[1024];
        arena_t arena;
        uint8_t *p1 = NULL;
        uint32_t *p2 = NULL;
        uint8_t *p3 = NULL;
        arena_status_t st;
        arena_marker_t marker;

        /* Initialise arena */
        st = arena_init(&arena, buffer, sizeof(buffer));
        if (st != ARENA_STATUS_OK) {
                return -1;
        }

        /* Allocate memory */
        st = ARENA_ALLOC_ARRAY(&arena, &p1, uint8_t, 100U);
        st = ARENA_ALLOC_ARRAY(&arena, &p2, uint32_t, 50U);

        /* Save checkpoint */
        marker = arena_get_marker(&arena);

        /* Allocate more */
        st = ARENA_ALLOC_ARRAY(&arena, &p3, uint8_t, 300U);

        /* Rewind to checkpoint (releases p3) */
        arena_rewind(&arena, marker);

        /* Reset completely */
        arena_reset(&arena);

        return 0;
}
```

## Scoped Temporary Allocations

Markers let you use one arena as both permanent storage and function-scoped
scratch memory.

```c
arena_status_t decode_packet(arena_t *const arena)
{
        arena_marker_t scratch;
        uint8_t *workspace = NULL;
        arena_status_t st;

        scratch = arena_get_marker(arena);
        if (scratch == ARENA_MARKER_INVALID) {
                return ARENA_STATUS_NULL_POINTER;
        }

        st = ARENA_ALLOC_ARRAY(arena, &workspace, uint8_t, 64U);
        if (st != ARENA_STATUS_OK) {
                return st;
        }

        /* Use workspace for temporary parsing state. */

        arena_rewind(arena, scratch);
        return ARENA_STATUS_OK;
}
```

## Typed Helpers

The core byte-oriented API remains available, but the header also provides
small typed wrappers for common cases.

```c
sample_t *sample = NULL;
uint16_t *table = NULL;

st = ARENA_ALLOC_OBJECT(&arena, &sample, sample_t);
st = ARENA_ALLOC_ARRAY_ZERO(&arena, &table, uint16_t, 32U);
```

Each macro evaluates to the `arena_status_t` of the allocation and sets the pointer to NULL on failure. The pointer is assigned by ordinary conversion from `void *`, so passing the address of anything other than an object pointer fails to compile. The `arena` argument is evaluated twice and must not have side effects.

Prefer the macros or the `_ptr` functions to calling `arena_alloc()` with `(void **)&typed_ptr`. That cast makes the library store a `void *` into an object of another pointer type, which is undefined behaviour under the C aliasing rules.

## Configuration

All macros live in `arena_cfg.h` and can be overridden before including the
header or passed as `-D` flags on the compiler command line.

| Macro | Description | Default |
|---|---|---|
| `ARENA_CFG_DEFAULT_ALIGNMENT` | Default alignment when 0 is passed to `arena_alloc()`. Must be a power of two. | `8U` |
| `ARENA_CFG_DEBUG_POISON` | Fill memory with poison pattern on reset/rewind (1=enabled, 0=disabled). | `0U` |
| `ARENA_CFG_POISON_PATTERN` | Byte pattern used for debug poisoning. | `0xAAU` |

## Building

```sh
# Library only (release)
meson setup build --buildtype=release
meson compile -C build

# With unit tests
meson setup build --buildtype=debug -Dbuild_tests=true
meson compile -C build
meson test -C build
```

## Platform support

The library is portable C11 with no target-specific code paths, and works wherever `CHAR_BIT` is 8 or 16. Sizes, alignments, markers and usage figures count `sizeof` units, so on a 16-bit-MAU target one byte is one 16-bit word and `ARENA_CFG_DEFAULT_ALIGNMENT` is measured in words.

| Toolchain | Target | Status |
|---|---|---|
| GCC, Clang | x86_64 Linux | Host tests (CI) |
| TI C2000 CGT 22.6 and 25.11 LTS | 16-bit-MAU DSP family | Library cross-build, COFF and EABI (CI) |

## Notes

| Topic | Note |
|---|---|
| **Memory** | All storage is static. The backing buffer must outlive the arena instance. |
| **Thread safety** | Not thread-safe. Protect with an external mutex if needed. |
| **Deallocation** | Memory is freed deterministically via `arena_rewind()` or `arena_reset()`. |
| **Error handling** | All functions return status codes; no `errno` or exceptions. |
| **WCET** | All operations have deterministic O(1) worst-case execution time. |
| **Alignment** | Custom alignments must be powers of two; verified at compile time. |

## API Reference

### Status codes

All functions that can fail return an `arena_status_t`:

| Value | Name | Meaning |
|---|---|---|
| `0` | `ARENA_STATUS_OK` | Operation succeeded |
| `1` | `ARENA_STATUS_NULL_POINTER` | A required pointer argument was NULL |
| `2` | `ARENA_STATUS_OUT_OF_MEMORY` | Not enough space left in the arena |
| `3` | `ARENA_STATUS_INVALID_ALIGNMENT` | Alignment is non-zero and not a power of two |
| `4` | `ARENA_STATUS_INVALID_ARGUMENT` | Zero size/count, or invalid byte-count computation |

### Initialisation

```c
arena_status_t arena_init(arena_t *arena, void *buffer, size_t size);
```

Initialise an arena with a backing buffer. The buffer must remain valid for the
arena's lifetime. Returns `ARENA_STATUS_INVALID_ARGUMENT` if `size` is zero,
`ARENA_STATUS_NULL_POINTER` if either pointer is NULL.

### Allocation

```c
arena_status_t arena_alloc(arena_t *arena, void **result, size_t size, size_t alignment);
arena_status_t arena_alloc_zero(arena_t *arena, void **result, size_t size, size_t alignment);
arena_status_t arena_alloc_array(arena_t *arena, void **result,
                                 size_t element_size, size_t alignment,
                                 size_t count);
arena_status_t arena_alloc_array_zero(arena_t *arena, void **result,
                                      size_t element_size, size_t alignment,
                                      size_t count);
```

Allocate `size` bytes with the requested alignment. Pass `alignment = 0` to use
the default (`ARENA_CFG_DEFAULT_ALIGNMENT`, 8 bytes). Returns
`ARENA_STATUS_INVALID_ARGUMENT` if `size` is zero,
`ARENA_STATUS_INVALID_ALIGNMENT` if `alignment` is non-zero and not a power of
two, or `ARENA_STATUS_OUT_OF_MEMORY` if the arena is full. On failure,
`*result` is set to `NULL`. The array variants reject `count == 0`,
`element_size == 0`, and any `element_size * count` overflow before
attempting the allocation. The `_zero` variants additionally clear the
allocated bytes.

### Typed Macros

```c
#define ARENA_ALLOC_OBJECT(arena, result, type)
#define ARENA_ALLOC_ARRAY(arena, result, type, count)
#define ARENA_ALLOC_OBJECT_ZERO(arena, result, type)
#define ARENA_ALLOC_ARRAY_ZERO(arena, result, type, count)
```

These wrappers infer `sizeof(type)` and `_Alignof(type)` for common object and
array allocations, and evaluate to the allocation status.

```c
void *arena_alloc_array_ptr(arena_t *arena, size_t element_size,
                            size_t alignment, size_t count);
void *arena_alloc_array_zero_ptr(arena_t *arena, size_t element_size,
                                 size_t alignment, size_t count);
arena_status_t arena_get_last_status(const arena_t *arena);
```

The `_ptr` functions return the block, or NULL on failure, so the result can be assigned to any object pointer without a cast. Every allocation function records its status on the arena; `arena_get_last_status()` reads it, and returns `ARENA_STATUS_NULL_POINTER` for a NULL arena.

### Checkpointing

```c
arena_marker_t arena_get_marker(const arena_t *arena);
void arena_rewind(arena_t *arena, arena_marker_t marker);
```

Save and restore arena state for scoped allocations.

### Query Functions

```c
size_t arena_get_used(const arena_t *arena);
size_t arena_get_high_water(const arena_t *arena);
size_t arena_get_capacity(const arena_t *arena);
```

Query current usage, maximum usage, and total capacity.

### Reset

```c
void arena_reset(arena_t *arena);
```

Reset the arena to its initial empty state.
