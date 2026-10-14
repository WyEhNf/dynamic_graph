/* Self-built fixture, not the official competition source. */
#include <math.h>
int cholesky_reference(const double *a, double *l, int n) {
  for (int i = 0; i < n; ++i) {
    for (int j = 0; j <= i; ++j) {
      double sum = 0.0;
      for (int k = 0; k < j; ++k) {
        sum += l[i*n+k] * l[j*n+k];
      }
      if (i == j) l[i*n+j] = sqrt(a[i*n+i] - sum);
      else l[i*n+j] = (a[i*n+j] - sum) / l[j*n+j];
    }
  }
  return 0;
}
