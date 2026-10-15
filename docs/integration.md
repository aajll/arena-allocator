# Integration guide

This guide shows how to add `arena-allocator` to a project, configure it, build it, and run its tests. The API is described in [api.md](api.md), and the allocation model and its guarantees in [design.md](design.md).

## Requirements

- A C11 compiler with `_Static_assert` and `_Alignof`, and a target where `CHAR_BIT` is 8 or 16.
- `<stddef.h>`, `<stdint.h>` with `uintptr_t`, and `<stdbool.h>`. The library calls no standard library function.
- For the tests: Meson, Ninja and Python 3.

## Copy-in

Copy three files into your source tree:

```
include/arena.h
include/arena_cfg.h
src/arena.c
```

Keep the two headers in the same directory, because `arena.h` includes `arena_cfg.h`. Then include the public header:

```c
#include "arena.h"
```

`arena.h` defines the version macros described in [api.md](api.md#version).

## Meson subproject

Put the repository in `subprojects/arena-allocator`, as a checkout or through a wrap file, then declare the dependency:

```meson
arena_dep = dependency('arena', fallback: ['arena-allocator', 'arena_dep'])
```

`dependency('arena')` finds an installed package through `pkg-config`, and otherwise falls back to the subproject's `arena_dep` variable, which links the static library and adds `include/`. Once the subproject is configured it registers `arena_dep` as `arena`, so other subprojects in the same build get it from `dependency('arena')` without a fallback.

| Option | Default | Effect |
| --- | --- | --- |
| `build_tests` | `false` | Builds the unit tests, the poisoning tests, the install smoke test and the documentation example test. |

## Installed package

```sh
meson setup build --buildtype=release -Dbuild_tests=false --prefix=/usr/local
meson compile -C build
meson install -C build
cc app.c $(pkg-config --cflags --libs arena) -o app
```

The install contains the static archive `libarena.a`, the headers in an `arena/` subdirectory, and `arena.pc`. The `pkg-config` flags point into `arena/`, so include the headers by name, or include `<arena/arena.h>` with only the include root on the search path:

<!-- snippet: skip -->
```c
#include "arena.h"
```

Forwarding headers at `${includedir}/arena.h` and `${includedir}/arena_cfg.h` keep `#include <arena.h>` working without `pkg-config`. They are deprecated and will be removed in the next major release.

## Configuration

`arena_cfg.h` holds three options, each behind an `#ifndef` guard, so a `-D` definition replaces the shipped default. They are described in [api.md](api.md#configuration-macros).

Only `src/arena.c` reads them, and none changes `arena_t`, so a caller compiled with different values links and runs correctly but has no effect on the library. Set them where the library is compiled: on the compiler command line for a copy-in build, or in a Meson build through the top-level `c_args`, which also apply to subprojects:

```sh
meson setup build "-Dc_args=-DARENA_CFG_DEBUG_POISON=1U"
```

An installed library keeps the configuration it was built with.

## Build and test

```sh
# Library only
meson setup build --buildtype=release -Dbuild_tests=false
meson compile -C build

# All tests under ASan and UBSan
meson setup build --buildtype=debug -Dbuild_tests=true -Db_sanitize=address,undefined
meson compile -C build
meson test -C build --verbose
```

The poisoning tests build their own copy of the library with `ARENA_CFG_DEBUG_POISON` enabled, so one configuration runs both. The install smoke test installs the library into a temporary directory and links a consumer against it; it runs only in builds without sanitisers or coverage. Coverage, formatting and MISRA commands are in [CONTRIBUTING.md](../CONTRIBUTING.md).

## Cross builds

The consuming firmware owns its cross file, linker command file, and memory placement. No cross file ships with this project.

CI compiles the library with warnings as errors using two releases of a vendor C11 compiler for a 16-bit-MAU DSP target, under both of its object formats. This covers the source dialect and type assumptions only; linking and execution remain checks for the consumer.

On such a target `CHAR_BIT` is 16, so every size, alignment, marker and usage figure counts 16-bit words, and `ARENA_CFG_DEFAULT_ALIGNMENT` of 8 is 16 octets. [design.md](design.md#storage-units-on-16-bit-mau-targets) describes the consequences.
