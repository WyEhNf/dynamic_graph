"""Actual bundled OpenBLAS LAPACKE comparison, separate numerical contract."""
from pathlib import Path
import argparse,ctypes,hashlib,json,struct,time
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--oracle',required=True);p.add_argument('--threads',type=int,required=True);p.add_argument('--kind',choices=['dense','band7'],required=True);a=p.parse_args()
with open(a.input,'rb') as f:
    assert struct.unpack('<I',f.read(4))[0]==1;n=struct.unpack('<I',f.read(4))[0]
    data=np.fromfile(f,dtype='<f8',count=n*n).reshape(n,n);assert f.read(1)==b''
dll=next((Path(np.__file__).parent.parent/'numpy.libs').glob('*openblas*.dll'))
lib=ctypes.CDLL(str(dll))
for name in ('scipy_openblas_get_config64_','scipy_openblas_get_corename64_'):
    getattr(lib,name).restype=ctypes.c_char_p
lib.scipy_openblas_set_num_threads64_.argtypes=[ctypes.c_int]
lib.scipy_openblas_get_num_threads64_.restype=ctypes.c_int
lib.scipy_openblas_set_num_threads64_(a.threads)
assert lib.scipy_openblas_get_num_threads64_()==a.threads
I=ctypes.c_int64;D=ctypes.POINTER(ctypes.c_double)
factor=lib.scipy_LAPACKE_dpotrf_work64_;factor.argtypes=[ctypes.c_int,ctypes.c_char,I,D,I];factor.restype=I
band=lib.scipy_LAPACKE_dpbtrf_work64_;band.argtypes=[ctypes.c_int,ctypes.c_char,I,I,D,I];band.restype=I
start=time.perf_counter();finite=bool(np.isfinite(data).all());finite_ms=1000*(time.perf_counter()-start);assert finite
pack_ms=0.0;unpack_ms=0.0
if a.kind=='dense':
    # Row-major lower A is column-major upper A.T. No transpose/copy needed.
    start=time.perf_counter();info=int(factor(102,b'U',n,data.ctypes.data_as(D),n));factor_ms=1000*(time.perf_counter()-start)
else:
    # Caller-supplied KD7 is part of the standard band API, not auto detection.
    start=time.perf_counter();ab=np.zeros((8,n),dtype=np.float64,order='F')
    for k in range(8):
        j=np.arange(n-k);ab[k,:n-k]=data[j+k,j]
    pack_ms=1000*(time.perf_counter()-start)
    start=time.perf_counter();info=int(band(102,b'L',n,7,ab.ctypes.data_as(D),8));factor_ms=1000*(time.perf_counter()-start)
    start=time.perf_counter()
    for k in range(8):
        j=np.arange(n-k);data[j+k,j]=ab[k,:n-k]
    unpack_ms=1000*(time.perf_counter()-start)
assert info==0,info
start=time.perf_counter()
for i in range(n):data[i,i+1:]=0.0
cleanup_ms=1000*(time.perf_counter()-start)
# Numerical comparison occurs outside every factor/wrapper timing.
with open(a.oracle,'rb') as f:assert f.read(8)==struct.pack('<II',1,n)
ref=np.memmap(a.oracle,dtype='<f8',mode='r',offset=8,shape=(n,n))
mismatches=0;lower_total=n*(n+1)//2;max_abs=0.0;squared_error=0.0;squared_ref=0.0;band_mismatches=0;band_cells=0
for i in range(n):
    x=data[i,:i+1];y=ref[i,:i+1]
    mismatches+=int(np.count_nonzero(x.view(np.uint64)!=y.view(np.uint64)))
    z=x-y;max_abs=max(max_abs,float(np.max(np.abs(z))));squared_error+=float(np.dot(z,z));squared_ref+=float(np.dot(y,y))
    if a.kind=='band7':
        first=max(0,i-7);band_mismatches+=int(np.count_nonzero(data[i,first:i+1].view(np.uint64)!=ref[i,first:i+1].view(np.uint64)));band_cells+=i+1-first
relative=float(np.sqrt(squared_error/squared_ref))
assert relative<=1e-10 and np.all(np.diag(data)>0) and np.isfinite(data).all()
print(json.dumps(dict(n=n,kind=a.kind,threads_requested=a.threads,threads_actual=lib.scipy_openblas_get_num_threads64_(),numpy_version=np.__version__,
    dll=str(dll),dll_sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),config=lib.scipy_openblas_get_config64_().decode(),core=lib.scipy_openblas_get_corename64_().decode(),
    info=info,factor_ms=factor_ms,finite_validation_ms=finite_ms,band_pack_ms=pack_ms,band_unpack_ms=unpack_ms,upper_cleanup_ms=cleanup_ms,
    wrapper_ms=finite_ms+pack_ms+factor_ms+unpack_ms+cleanup_ms,read_and_initialization_timed=False,comparison_timed=False,
    scope='LAPACKE work API pure factor timer; wrapper includes independent NumPy all-finite, band pack/unpack if relevant and required dense upper+0. Input loading excluded as in native compute. No source parsing, metadata, VM, task graph or original-error contract.',
    structural_information='Caller supplied KD7; wrapper excludes discovering/certifying all off-band zeros' if a.kind=='band7' else 'Dense DPOTRF, input lower through column-major upper view',
    lower_cells=lower_total,bit_mismatches_lower=mismatches,bit_identical_to_original_C=mismatches==0,relative_frobenius_error_to_C=relative,max_abs_factor_error_to_C=max_abs,
    inband_cells=band_cells,inband_bit_mismatches=band_mismatches,
    equivalent_dense_gflops=(n**3/3)/(factor_ms*1e6) if a.kind=='dense' else None)),flush=True)
