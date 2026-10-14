"""One milestone compares old rows, column tiles, row tiles, and fast export."""
from benchmark_column_workspace import main

if __name__=='__main__':
    main(milestone='row-tile',
         variants=('thread-policy','column-workspace','row-tile','transpose-export'),
         stress_variants=('row-tile','transpose-export'),
         contract='original-C full bytes; tile accumulators row-major until P/T completes, then column factors via worker-local scratch; source operand and reduction order preserved; separate serial and AVX2/parallel final export; compute includes export and full +0 output allocation')
