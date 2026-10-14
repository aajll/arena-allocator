inc = include_directories('../include', '../config')
python = import('python').find_installation('python3')

test_exe = executable('test_arena',
        'test_arena.c',
        'test_arena_api.c',
        'test_arena_allocation.c',
        'test_arena_markers.c',
        '../src/arena.c',
        include_directories : inc,
        c_args : ['-DTEST_BUILD'])

poison_test_exe = executable('test_arena_poison',
        'test_arena_poison.c', '../src/arena.c',
        include_directories : inc,
        c_args : [
                '-DTEST_BUILD',
                '-DARENA_CFG_DEBUG_POISON=1U',
                '-DARENA_CFG_POISON_PATTERN=0xDEU',
        ])

# The typed macros assign through ordinary pointer conversion, so passing the
# address of a non-pointer object must fail to compile. The pointer variant is
# the control: it must compile, so the check cannot pass for an unrelated reason.
_typed_macro_probe = '''
#include "arena.h"
int main(void)
{
        static unsigned char buffer[16];
        arena_t arena;
        @0@ result = 0;
        (void)arena_init(&arena, buffer, sizeof(buffer));
        return (int)ARENA_ALLOC_OBJECT(&arena, &result, int);
}
'''
_cc = meson.get_compiler('c')
if not _cc.compiles(_typed_macro_probe.format('int *'),
                    include_directories : inc, args : ['-Werror'],
                    name : 'typed macro accepts a pointer result')
  error('ARENA_ALLOC_OBJECT rejected a pointer result')
endif
if _cc.compiles(_typed_macro_probe.format('int'),
                include_directories : inc, args : ['-Werror'],
                name : 'typed macro rejects a non-pointer result')
  error('ARENA_ALLOC_OBJECT accepted a non-pointer result')
endif

test('arena_test', test_exe)
test('arena_poison_test', poison_test_exe)

# The smoke test installs libarena.a and links it from a plain consumer that carries no sanitizer or coverage flags. Instrumented static archives embed sanitizer/gcov runtime symbols that the consumer linker cannot resolve, so the install-smoke test only runs for plain builds.
if get_option('b_sanitize') == 'none' and not get_option('b_coverage')
  test('arena_install_smoke', python,
       args : [files('run_install_smoke.py'), meson.project_source_root(),
               meson.project_build_root()])
endif
