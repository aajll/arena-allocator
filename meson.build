project(
  'arena-allocator',
  'c',
  version: '1.2.0',
  default_options: ['warning_level=3'],
)

_ver = meson.project_version().split('.')
_conf = configuration_data()
_conf.set_quoted('ARENA_VERSION', meson.project_version())
_conf.set('ARENA_VERSION_MAJOR', _ver[0].to_int())
_conf.set('ARENA_VERSION_MINOR', _ver[1].to_int())
_conf.set('ARENA_VERSION_PATCH', _ver[2].to_int())

version_h = configure_file(
  input: 'config' / 'arena_version.h.in',
  output: 'arena_version.h',
  configuration: _conf,
  install: true,
  install_dir: get_option('includedir') / 'arena',
)

arena_inc = include_directories('include', 'config')
arena_src = ['src/arena.c']

arena_lib = static_library(
  'arena',
  arena_src,
  include_directories: arena_inc,
  install: true,
)

arena_dep = declare_dependency(include_directories: arena_inc, link_with: arena_lib)

install_headers('include/arena.h', 'include/arena_cfg.h', subdir: 'arena')

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
