# arena-allocator

[![CI](https://github.com/aajll/arena-allocator/actions/workflows/ci.yml/badge.svg)](https://github.com/aajll/arena-allocator/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A C11 arena (bump) allocator over a caller-provided buffer: aligned allocation in constant time, released all at once by a reset or back to a saved marker, with no heap.**

## Quick start

Copy `include/arena.h`, `include/arena_cfg.h` and `src/arena.c` into your project. For a Meson subproject or an installed `pkg-config` package, see the [integration guide](docs/integration.md).

```c
#include <stdio.h>

#include "arena.h"

static unsigned char buffer[256];

int
main(void)
{
        arena_t arena;
        uint32_t *samples = NULL;
        char *scratch = NULL;

        if (arena_init(&arena, buffer, sizeof(buffer)) != ARENA_STATUS_OK) {
                return 1;
        }
        if (ARENA_ALLOC_ARRAY(&arena, &samples, uint32_t, 16U)
            != ARENA_STATUS_OK) {
                return 1;
        }

        /* Scratch space above a marker is released by one rewind. */
        const arena_marker_t mark = arena_get_marker(&arena);
        if (ARENA_ALLOC_ARRAY(&arena, &scratch, char, 100U)
            != ARENA_STATUS_OK) {
                return 1;
        }
        /* Prints "used 164 of 256". */
        printf("used %zu of %zu\n", arena_get_used(&arena),
               arena_get_capacity(&arena));

        arena_rewind(&arena, mark);
        /* Prints "used 64, high water 164". */
        printf("used %zu, high water %zu\n", arena_get_used(&arena),
               arena_get_high_water(&arena));

        /* A request larger than the free space fails: prints "2". */
        printf("%d\n", (int)ARENA_ALLOC_ARRAY(&arena, &scratch, char, 200U));
        return 0;
}
```

## Description

The arena is a small structure the caller owns, pointing at a buffer the caller also owns. Each allocation aligns the current offset and moves it forward; nothing is freed individually. A marker records the offset, so everything allocated after it can be released in one step, which makes the arena suited to per-frame or per-request scratch memory beside long-lived data.

- Allocation in constant time, with any power-of-two alignment and an overflow-checked array form
- Typed macros that take `sizeof` and `_Alignof` from the type and assign the result without a cast
- Markers for scoped release, a full reset, and a high-water mark that survives both for sizing the buffer
- Optional zeroing on allocation, and optional poisoning of released memory in debug builds
- Tests under ASan and UBSan with 100% line and branch coverage, and MISRA C:2023 analysis with [`misch`](https://pypi.org/project/misch/)

## Validated toolchains

| Toolchain               | Target                        | Validation                                        |
| ----------------------- | ----------------------------- | ------------------------------------------------- |
| GCC                     | x86_64 Linux                  | All tests, with and without debug poisoning       |
| DSP vendor C11 compiler | 16-bit MAU (`CHAR_BIT == 16`) | Library compile, two releases, two object formats |

Target linking and execution belong to the consuming firmware. See [cross builds](docs/integration.md#cross-builds).

## Documentation

- [Integration guide](docs/integration.md) — copy-in, Meson subproject, installed package, configuration, building, and cross builds
- [API reference](docs/api.md) — initialisation, allocation, typed macros, markers and reset, queries, configuration macros, and recipes
- [Design](docs/design.md) — the bump model, alignment, markers, poisoning, storage units on 16-bit-MAU targets, failure behaviour, and verification
- [Changelog](CHANGELOG.md) — release history

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before you open a pull request. Report security issues as described in [SECURITY.md](.github/SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
