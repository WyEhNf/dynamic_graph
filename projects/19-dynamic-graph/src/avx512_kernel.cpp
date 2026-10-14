// This translation unit only: AVX512F/FMA, entered after CPU + OS gate.
#include <immintrin.h>
#include <algorithm>
#include <cmath>
#include <cstddef>
namespace chol {
template<bool Fused>static __m512d madd512(__m512d x,__m512d y,__m512d z) {
  if constexpr(Fused)return _mm512_fmadd_pd(x,y,z);
  else return _mm512_add_pd(_mm512_mul_pd(x,y),z);
}
template<bool Fused>static double madd_scalar(double x,double y,double z) {
  if constexpr(Fused)return std::fma(x,y,z);
  else return x*y+z;
}
template<bool Fused>static void update512(double* output,std::size_t stride,const double* left,const double* right,std::size_t rows,std::size_t cols,std::size_t depth,std::size_t b,bool diagonal) {
  std::size_t first_row=0;
  if(!diagonal)for(;first_row+4<=rows;first_row+=4) {
    auto* t0=output+first_row*stride;auto* t1=t0+stride;auto* t2=t1+stride;auto* t3=t2+stride;
    std::size_t h=0;
    for(;h+16<=cols;h+=16) {
      auto a0=_mm512_loadu_pd(t0+h),a1=_mm512_loadu_pd(t0+h+8);
      auto c0=_mm512_loadu_pd(t1+h),c1=_mm512_loadu_pd(t1+h+8);
      auto d0=_mm512_loadu_pd(t2+h),d1=_mm512_loadu_pd(t2+h+8);
      auto e0=_mm512_loadu_pd(t3+h),e1=_mm512_loadu_pd(t3+h+8);
      for(std::size_t k=0;k<depth;++k) {
        const auto* x=left+k*b+first_row;const auto* y=right+k*b+h;
        const auto x0=_mm512_set1_pd(x[0]),x1=_mm512_set1_pd(x[1]),x2=_mm512_set1_pd(x[2]),x3=_mm512_set1_pd(x[3]);
        const auto y0=_mm512_loadu_pd(y),y1=_mm512_loadu_pd(y+8);
        a0=madd512<Fused>(x0,y0,a0);a1=madd512<Fused>(x0,y1,a1);
        c0=madd512<Fused>(x1,y0,c0);c1=madd512<Fused>(x1,y1,c1);
        d0=madd512<Fused>(x2,y0,d0);d1=madd512<Fused>(x2,y1,d1);
        e0=madd512<Fused>(x3,y0,e0);e1=madd512<Fused>(x3,y1,e1);
      }
      _mm512_storeu_pd(t0+h,a0);_mm512_storeu_pd(t0+h+8,a1);_mm512_storeu_pd(t1+h,c0);_mm512_storeu_pd(t1+h+8,c1);
      _mm512_storeu_pd(t2+h,d0);_mm512_storeu_pd(t2+h+8,d1);_mm512_storeu_pd(t3+h,e0);_mm512_storeu_pd(t3+h+8,e1);
    }
    // Bounded tail vectors; no packed padding/output upper tile accesses.
    for(;h+8<=cols;h+=8) {
      auto a=_mm512_loadu_pd(t0+h),c=_mm512_loadu_pd(t1+h),d=_mm512_loadu_pd(t2+h),e=_mm512_loadu_pd(t3+h);
      for(std::size_t k=0;k<depth;++k) {
        const auto y=_mm512_loadu_pd(right+k*b+h);const auto* x=left+k*b+first_row;
        a=madd512<Fused>(_mm512_set1_pd(x[0]),y,a);c=madd512<Fused>(_mm512_set1_pd(x[1]),y,c);
        d=madd512<Fused>(_mm512_set1_pd(x[2]),y,d);e=madd512<Fused>(_mm512_set1_pd(x[3]),y,e);
      }
      _mm512_storeu_pd(t0+h,a);_mm512_storeu_pd(t1+h,c);_mm512_storeu_pd(t2+h,d);_mm512_storeu_pd(t3+h,e);
    }
    for(;h<cols;++h) {
      auto a=t0[h],c=t1[h],d=t2[h],e=t3[h];
      for(std::size_t k=0;k<depth;++k){const auto* x=left+k*b+first_row;const auto y=right[k*b+h];a=madd_scalar<Fused>(x[0],y,a);c=madd_scalar<Fused>(x[1],y,c);d=madd_scalar<Fused>(x[2],y,d);e=madd_scalar<Fused>(x[3],y,e);}
      t0[h]=a;t1[h]=c;t2[h]=d;t3[h]=e;
    }
  }
  for(std::size_t j=first_row;j<rows;++j) {
    auto* target=output+j*stride;const auto end=diagonal?std::min(cols,j+1):cols;std::size_t h=0;
    for(;h+8<=end;h+=8) {
      auto z=_mm512_loadu_pd(target+h);
      for(std::size_t k=0;k<depth;++k)z=madd512<Fused>(_mm512_set1_pd(left[k*b+j]),_mm512_loadu_pd(right+k*b+h),z);
      _mm512_storeu_pd(target+h,z);
    }
    for(;h<end;++h){auto z=target[h];for(std::size_t k=0;k<depth;++k)z=madd_scalar<Fused>(left[k*b+j],right[k*b+h],z);target[h]=z;}
  }
}
void ordered_update_avx512(double* output,std::size_t stride,const double* left,const double* right,std::size_t rows,std::size_t cols,std::size_t depth,std::size_t b,bool diagonal,bool fused) {
  if(fused)update512<true>(output,stride,left,right,rows,cols,depth,b,diagonal);
  else update512<false>(output,stride,left,right,rows,cols,depth,b,diagonal);
}
}
