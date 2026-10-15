# API reference

`arena.h` declares the whole interface and includes `arena_cfg.h`. The examples in this document compile together as one file after `#include "arena.h"`.

## Conventions

- The arena is an `arena_t` that the caller owns, and it manages a buffer the caller also owns. Both may be static, on the stack, or embedded in another structure. The buffer must outlive every use of the arena and of the memory it hands out.
- The members of `arena_t` are private. Read them through the query functions.
- Every pointer argument is checked, and a NULL pointer is never dereferenced. Functions that cannot return a status ignore a NULL arena, and queries on one return 0.
- Sizes, alignments, markers and usage figures count `sizeof` units: bytes, or 16-bit words where `CHAR_BIT` is 16.
- No function is safe to call on the same arena from two contexts at once. [design.md](design.md#concurrency) gives the contract.

## Status codes

<!-- snippet: skip -->
```c
typedef enum {
        ARENA_STATUS_OK = 0,
        ARENA_STATUS_NULL_POINTER = 1,
        ARENA_STATUS_OUT_OF_MEMORY = 2,
        ARENA_STATUS_INVALID_ALIGNMENT = 3,
        ARENA_STATUS_INVALID_ARGUMENT = 4
} arena_status_t;
```

`ARENA_STATUS_NULL_POINTER` means a required pointer was NULL, `ARENA_STATUS_OUT_OF_MEMORY` that the free space cannot hold the aligned request, `ARENA_STATUS_INVALID_ALIGNMENT` that a non-zero alignment is not a power of two, and `ARENA_STATUS_INVALID_ARGUMENT` that a size or count is zero, an array size overflows `size_t`, or a buffer would wrap the address space. The values are part of the API.

## Initialisation

```c
arena_status_t arena_init(arena_t *const arena, void *const buffer,
                          size_t size);
```

`arena_init` attaches `size` units of `buffer` to the arena and empties it: the used size and the high-water mark become 0, and the last status `ARENA_STATUS_OK`. With debug poisoning enabled it also fills the whole buffer with the poison pattern.

It returns `ARENA_STATUS_NULL_POINTER` if `arena` or `buffer` is NULL, and `ARENA_STATUS_INVALID_ARGUMENT` if `size` is zero or the buffer would extend past `UINTPTR_MAX`. On failure the arena is not written. Calling it again on a live arena discards every allocation and the high-water mark.

## Allocation

```c
arena_status_t arena_alloc(arena_t *const arena, void **const result,
                           size_t size, size_t alignment);
arena_status_t arena_alloc_zero(arena_t *const arena, void **const result,
                                size_t size, size_t alignment);
```

`arena_alloc` rounds the current position up to `alignment`, reserves `size` units from there, and writes the start address to `*result`. An `alignment` of 0 selects `ARENA_CFG_DEFAULT_ALIGNMENT`. Alignment is applied to the address, not to the offset in the buffer, so the result is aligned however the buffer itself is placed. The padding skipped to reach the alignment counts towards the used size.

`arena_alloc_zero` does the same and then sets every unit of the block to zero. The memory `arena_alloc` returns holds whatever was there before: data from an earlier allocation, or the poison pattern in a debug build.

The arguments are checked in this order, and the first failure is returned:

1. `result` is NULL: `ARENA_STATUS_NULL_POINTER`. Otherwise `*result` is set to NULL before any other check.
2. `arena` is NULL: `ARENA_STATUS_NULL_POINTER`.
3. `alignment` is not a power of two: `ARENA_STATUS_INVALID_ALIGNMENT`.
4. `size` is zero: `ARENA_STATUS_INVALID_ARGUMENT`.
5. The aligned block does not fit: `ARENA_STATUS_OUT_OF_MEMORY`.

A failed call leaves the used size and high-water mark unchanged.

```c
arena_status_t arena_alloc_array(arena_t *const arena, void **const result,
                                 size_t element_size, size_t alignment,
                                 size_t count);
arena_status_t arena_alloc_array_zero(arena_t *const arena,
                                      void **const result,
                                      size_t element_size, size_t alignment,
                                      size_t count);
```

The array forms reserve `element_size * count` units. After the `result` check they return `ARENA_STATUS_INVALID_ARGUMENT` if either factor is zero or the product overflows `size_t`, before the arena is examined, and then behave as `arena_alloc` and `arena_alloc_zero`.

Every allocation function, including the typed macros below, records its status on the arena whenever `arena` is non-NULL:

```c
arena_status_t arena_get_last_status(const arena_t *const arena);
```

`arena_get_last_status` returns that status, or `ARENA_STATUS_NULL_POINTER` for a NULL arena.

## Typed allocation

<!-- snippet: skip -->
```c
#define ARENA_ALLOC_OBJECT(arena, result, type)
#define ARENA_ALLOC_ARRAY(arena, result, type, count)
#define ARENA_ALLOC_OBJECT_ZERO(arena, result, type)
#define ARENA_ALLOC_ARRAY_ZERO(arena, result, type, count)
```

The macros allocate one `type`, or `count` of them, with `sizeof(type)` and `_Alignof(type)`, and assign the result to `*(result)`, which must be a pointer variable. They evaluate to the status of the allocation, and on failure `*(result)` is NULL. `arena` is evaluated twice, once to allocate and once to read the status, so it must not have side effects.

<!-- snippet: body -->
```c
static unsigned char storage[128];
arena_t arena;
struct point {
        int16_t x;
        int16_t y;
} *origin = NULL;
uint16_t *table = NULL;

(void)arena_init(&arena, storage, sizeof(storage));
if ((ARENA_ALLOC_OBJECT_ZERO(&arena, &origin, struct point) == ARENA_STATUS_OK)
    && (ARENA_ALLOC_ARRAY(&arena, &table, uint16_t, 32U) == ARENA_STATUS_OK)) {
        table[0] = (uint16_t)origin->x;
}
```

The assignment converts from `void *` in the ordinary way, so passing the address of anything other than an object pointer fails to compile. Prefer the macros to calling `arena_alloc` with `(void **)&typed_ptr`: that cast makes the library store a `void *` into an object of another pointer type, which the C aliasing rules leave undefined.

The macros expand to two functions that return the block directly, which can also be called on their own:

```c
void *arena_alloc_array_ptr(arena_t *const arena, size_t element_size,
                            size_t alignment, size_t count);
void *arena_alloc_array_zero_ptr(arena_t *const arena, size_t element_size,
                                 size_t alignment, size_t count);
```

They return the block, or NULL on any failure, and record the status for `arena_get_last_status`.

## Markers and reset

```c
arena_marker_t arena_get_marker(const arena_t *const arena);
void arena_rewind(arena_t *const arena, arena_marker_t marker);
void arena_reset(arena_t *const arena);
```

`arena_get_marker` returns the current used size as an `arena_marker_t`, a `size_t`. For a NULL arena it returns `ARENA_MARKER_INVALID`, which is `SIZE_MAX` and never a reachable offset.

`arena_rewind` sets the used size back to `marker`, which releases every allocation made after the marker was taken. It does nothing for a NULL arena or a marker above the current used size, including `ARENA_MARKER_INVALID`, and reports nothing, so check a marker against `ARENA_MARKER_INVALID` when it is taken. A marker is only an offset: one taken before a reset or a deeper rewind is accepted again once the arena has grown past it, and releases whatever lies above it.

`arena_reset` sets the used size to 0. Neither function changes the high-water mark or the last status. With debug poisoning enabled, both fill the whole free region, from the new used size to the end of the buffer, with the poison pattern.

Pointers into the released region stay valid C pointers, but the memory they reference is handed out again by the next allocation.

## Queries

```c
size_t arena_get_used(const arena_t *const arena);
size_t arena_get_high_water(const arena_t *const arena);
size_t arena_get_capacity(const arena_t *const arena);
```

`arena_get_used` returns the units in use, including alignment padding. `arena_get_high_water` returns the largest used size since `arena_init`; a rewind or reset does not lower it. `arena_get_capacity` returns the buffer size given to `arena_init`. Each returns 0 for a NULL arena.

## Configuration macros

Each macro lives in `arena_cfg.h` behind an `#ifndef` guard and is overridden with a `-D` flag where the library is compiled. [integration.md](integration.md#configuration) explains where.

| Macro | Default | Effect |
| --- | --- | --- |
| `ARENA_CFG_DEFAULT_ALIGNMENT` | `8U` | Alignment, in units, used when an allocation passes 0. Must be a power of two; anything else stops the build of `src/arena.c` with a `_Static_assert`. |
| `ARENA_CFG_DEBUG_POISON` | `0U` | When non-zero, `arena_init`, `arena_rewind` and `arena_reset` fill free memory with the poison pattern. |
| `ARENA_CFG_POISON_PATTERN` | `0xAAU` | The value written to each unit when poisoning. |

## Recipes

### Scoped scratch memory

Take a marker on entry and rewind before every return, so a function's working memory is released however it exits:

```c
arena_status_t
decode_packet(arena_t *const arena, const unsigned char *const packet,
              size_t len)
{
        const arena_marker_t scratch = arena_get_marker(arena);
        unsigned char *work = NULL;
        arena_status_t st;

        if (scratch == ARENA_MARKER_INVALID) {
                return ARENA_STATUS_NULL_POINTER;
        }
        st = ARENA_ALLOC_ARRAY(arena, &work, unsigned char, len);
        if (st == ARENA_STATUS_OK) {
                for (size_t i = 0U; i < len; i++) {
                        work[i] = packet[i];
                }
                /* parse work[] here */
        }

        arena_rewind(arena, scratch);
        return st;
}
```

Allocations made before the marker, by the caller or earlier in the program, are untouched. A function that keeps part of its result must allocate it before taking the marker.

### Sizing the buffer

Run the worst-case workload on a generously sized arena in a test build, then read the high-water mark:

<!-- snippet: body -->
```c
static _Alignas(8) unsigned char trial[4096];
arena_t probe;

(void)arena_init(&probe, trial, sizeof(trial));
/* run the worst-case workload against &probe */
const size_t needed = arena_get_high_water(&probe);
```

The figure includes the alignment padding, which depends on where the buffer is placed. Declare the trial and production buffers with `_Alignas` at least as strict as the largest alignment the workload requests, here 8, and the padding is the same in both.
