# SPDX-License-Identifier: MIT

project(
  'arena-allocator',
  'c',
  version: '1.2.0',
  meson_version: '>=0.57.0',
  default_options: ['warning_level=3'],
)

# include/arena.h defines the version macros, so a copy-in build has them.
# Configuration fails when they differ from the project version.

fs = import('fs')
version_parts = meson.project_version().split('.')
version_macros = {
  'ARENA_VERSION_MAJOR': version_parts[0],
  'ARENA_VERSION_MINOR': version_parts[1],
  'ARENA_VERSION_PATCH': version_parts[2],
  'ARENA_VERSION': '"' + meson.project_version() + '"',
}
header_lines = []
foreach line : fs.read('include' / 'arena.h').split('\n')
  header_lines += ' '.join(line.split())
endforeach
foreach name, value : version_macros
  if '#define @0@ @1@'.format(name, value) not in header_lines
    error('include/arena.h must define @0@ as @1@'.format(name, value))
  endif
endforeach

arena_inc = include_directories('include')
arena_src = ['src/arena.c']

arena_lib = static_library(
  'arena',
  arena_src,
  include_directories: arena_inc,
  install: true,
)

arena_dep = declare_dependency(include_directories: arena_inc, link_with: arena_lib)
meson.override_dependency('arena', arena_dep)

install_headers(
  'include/arena.h',
  'include/arena_cfg.h',
  subdir: 'arena',
)

# Deprecated: keep #include <arena.h> working for consumers that add only the
# include root to their search path. Removed in the next major release.
install_headers('compat/arena.h', 'compat/arena_cfg.h')

# === pkg-config ===============================================================

pkgconfig = import('pkgconfig')
pkgconfig.generate(
  arena_lib,
  name: 'arena',
  description: 'Deterministic arena (bump) allocator in C for safety-critical embedded systems',
  subdirs: 'arena',
)

# === Host unit tests ==========================================================

if get_option('build_tests')
  subdir('tests')
endif
