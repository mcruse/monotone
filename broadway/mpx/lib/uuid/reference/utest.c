#include "copyrt.h"
#include "sysdep.h"
#include <stdio.h>
#include "uuid.h"

#define BUILD_HACK 1
#ifdef BUILD_HACK
#include "namespace.h"
#else
uuid_t NameSpace_DNS = { /* 6ba7b810-9dad-11d1-80b4-00c04fd430c8 */
  0x6ba7b810,
  0x9dad,
  0x11d1,
  0x80, 0xb4, 0x00, 0xc0, 0x4f, 0xd4, 0x30, 0xc8
};
#endif

/* puid -- print a UUID */
void puid(uuid_t u);

/* Simple driver for UUID generator */
#ifdef BUILD_HACK
int main(int argc, char **argv) {
#else
  void main(int argc, char **argv) {
#endif
    uuid_t u;
    int f;

    uuid_create(&u);
    printf("uuid_create()             -> "); puid(u);

    f = uuid_compare(&u, &u);
    printf("uuid_compare(u,u): %d\n", f);     /* should be 0 */
    f = uuid_compare(&u, &NameSpace_DNS);
    printf("uuid_compare(u, NameSpace_DNS): %d\n", f); /* s.b. 1 */
    f = uuid_compare(&NameSpace_DNS, &u);
    printf("uuid_compare(NameSpace_DNS, u): %d\n", f); /* s.b. -1 */

    uuid_create_from_name(&u, NameSpace_DNS, "www.widgets.com", 15);
    printf("uuid_create_from_name() -> "); puid(u);
#ifdef BUILD_HACK
    return 0;
#endif
  };

  void puid(uuid_t u) {
    int i;

    printf("%8.8x-%4.4x-%4.4x-%2.2x%2.2x-", u.time_low, u.time_mid,
	   u.time_hi_and_version, u.clock_seq_hi_and_reserved,
	   u.clock_seq_low);
    for (i = 0; i < 6; i++)
      printf("%2.2x", u.node[i]);
    printf("\n");
  };
