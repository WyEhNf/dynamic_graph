/* Algorithm transcribed from the official page's code image, 2026-10-10.
   https://www.chaspark.com/#/races/competitions/1326691788365586432
   Image: 1326692271903821824.png.
   The image omits div/madd definitions and output initialization. LOCAL CONTRACT:
   div(x,y)=x/y; madd(x,y,z)=x*y+z (NOT fused); caller initializes L to zero.
   These helpers are local assumptions, not supplied official definitions. */
#include <math.h>
static double div(double x, double y) { return x / y; }
static double madd(double x, double y, double z) { return x * y + z; }
void cholesky(double *A, double *L, int n) {
  for (int i = 0; i < n; i++) {
    L[i*n+i] = sqrt(A[i*n+i] - L[i*n+i]);
    for (int j = i+1; j < n; j++) {
      L[j*n+i] = div(A[j*n+i] - L[j*n+i], L[i*n+i]);
      for (int k = i+1; k <= j; k++) {
        L[j*n+k] = madd(L[j*n+i], L[k*n+i], L[j*n+k]);
      }
    }
  }
}
