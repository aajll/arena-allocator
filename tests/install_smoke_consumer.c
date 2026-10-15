/*********************************************************************
 * SPDX-License-Identifier: MIT
 *
 * @file install_smoke_consumer.c
 * @brief Minimal consumer used to validate staged installs.
 *********************************************************************/

#if defined(SMOKE_ROOT_INCLUDE)
#include <arena.h>
#else
#include <arena/arena.h>
#include <arena/arena_version.h>
_Static_assert(ARENA_VERSION_MAJOR >= 1, "arena_version.h is usable");
#endif
#include <stdint.h>

int
main(void)
{
        static uint8_t buffer[64U];
        arena_t arena;
        arena_status_t st;
        void *ptr = (void *)0;

        st = arena_init(&arena, buffer, sizeof(buffer));
        if (st != ARENA_STATUS_OK) {
                return 1;
        }

        st = arena_alloc(&arena, &ptr, 16U, 0U);
        if (st != ARENA_STATUS_OK) {
                return 2;
        }

        if ((ptr == NULL) || (arena_get_capacity(&arena) != sizeof(buffer))) {
                return 3;
        }

        return 0;
}
