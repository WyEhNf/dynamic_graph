/* Self-set blocked right-looking Cholesky. Same update order as the page image.
   Tile boundaries are dynamic; block_size can exceed n and need not divide n. */
#include <math.h>
static double quotient(double x, double y) { return x / y; }
static double multiply_add(double x, double y, double z) { return x * y + z; }
int cholesky_blocked(const double *a, double *l, int n, int block_size) {
  for (int panel = 0; panel < n; panel += block_size) {
    int panel_end = panel + block_size < n ? panel + block_size : n;
    for (int i = panel; i < panel_end; ++i) {
      l[i*n+i] = sqrt(a[i*n+i] - l[i*n+i]);
      for (int row_tile = i+1; row_tile < n; row_tile += block_size) {
        int row_end = row_tile + block_size < n ? row_tile + block_size : n;
        for (int j = row_tile; j < row_end; ++j) {
          l[j*n+i] = quotient(a[j*n+i] - l[j*n+i], l[i*n+i]);
          for (int col_tile = i+1; col_tile <= j; col_tile += block_size) {
            int col_end = col_tile + block_size < j+1 ? col_tile + block_size : j+1;
            for (int k = col_tile; k < col_end; ++k) {
              l[j*n+k] = multiply_add(l[j*n+i], l[k*n+i], l[j*n+k]);
            }
          }
        }
      }
    }
  }
  return 0;
}
