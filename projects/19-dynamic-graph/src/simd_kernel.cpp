#include "native_input_scan.hpp"
// This translation unit alone is compiled with AVX2/FMA. The generic detector
// remains portable; callers require both CPU features before entering here.
#include <immintrin.h>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <bit>
#include <cstdint>
#include <limits>
namespace chol {
#ifdef CHOL_VECTOR_SCANS
static_assert(sizeof(double)==8&&std::numeric_limits<double>::is_iec559);
bool all_finite_avx2(const double* values,std::size_t count) {
  const auto exponent=_mm256_set1_epi64x(0x7ff0000000000000LL);
  std::size_t i=0;
  for(;i+4<=count;i+=4) {
    const auto bits=_mm256_castpd_si256(_mm256_loadu_pd(values+i));
    const auto invalid=_mm256_cmpeq_epi64(_mm256_and_si256(bits,exponent),exponent);
    if(_mm256_movemask_pd(_mm256_castsi256_pd(invalid)))return false;
  }
  for(;i<count;++i)if((std::bit_cast<std::uint64_t>(values[i])&0x7ff0000000000000ULL)==0x7ff0000000000000ULL)return false;
  return true;
}
std::size_t first_nonzero_avx2(const double* values,std::size_t count) {
  const auto magnitude=_mm256_set1_epi64x(0x7fffffffffffffffLL),zero=_mm256_setzero_si256();
  std::size_t i=0;
  for(;i+4<=count;i+=4) {
    const auto bits=_mm256_castpd_si256(_mm256_loadu_pd(values+i));
    const auto zeros=_mm256_cmpeq_epi64(_mm256_and_si256(bits,magnitude),zero);
    const unsigned nonzero=(~static_cast<unsigned>(_mm256_movemask_pd(_mm256_castsi256_pd(zeros))))&15u;
    if(nonzero)return i+std::countr_zero(nonzero);
  }
  for(;i<count;++i)if(std::bit_cast<std::uint64_t>(values[i])&0x7fffffffffffffffULL)return i;
  return count;
}
#endif
#if defined(CHOL_FUSED_FINITE_BAND_SCAN) && defined(CHOL_HAVE_X86_SIMD) && defined(CHOL_VECTOR_SCANS)
NativeBandFacts fused_finite_band_avx2(const double* values,std::size_t n,std::size_t limit) {
  const auto exponent=_mm256_set1_epi64x(0x7ff0000000000000LL);
  const auto magnitude=_mm256_set1_epi64x(0x7fffffffffffffffLL);
  const auto zero=_mm256_setzero_si256();
  std::size_t width=0;
  for(std::size_t i=0;i<n;++i) {
    const auto* row=values+i*n;
    std::size_t j=0;
    bool found=false;
    // Only complete lower-triangle groups enter this loop. All four lanes
    // are validated before their earliest nonzero may establish the width.
    for(;j+4<=i;j+=4) {
      const auto bits=_mm256_castpd_si256(_mm256_loadu_pd(row+j));
      const auto invalid=_mm256_cmpeq_epi64(_mm256_and_si256(bits,exponent),exponent);
      if(_mm256_movemask_pd(_mm256_castsi256_pd(invalid)))return {false,false,0};
      const auto zeros=_mm256_cmpeq_epi64(_mm256_and_si256(bits,magnitude),zero);
      const unsigned nonzero=(~static_cast<unsigned>(_mm256_movemask_pd(_mm256_castsi256_pd(zeros))))&15u;
      if(nonzero) {
        width=std::max(width,i-(j+std::countr_zero(nonzero)));
        j+=4; // Every lane in this block has already passed finiteness.
        found=true;
        break;
      }
    }
    // After full groups only zero to three lower cells remain. bit_cast and
    // integer masks leave fenv unchanged, including for signaling NaNs.
    if(!found)for(;j<i;++j) {
      const auto bits=std::bit_cast<std::uint64_t>(row[j]);
      if((bits&0x7ff0000000000000ULL)==0x7ff0000000000000ULL)return {false,false,0};
      if(bits&0x7fffffffffffffffULL) {
        width=std::max(width,i-j);
        ++j;
        break;
      }
    }
    if(width>limit) {
      // A dense rejection is not a finite-input certificate. Check every
      // remaining cell, including this row's diagonal/upper and later rows.
      const auto consumed=i*n+j;
      if(!all_finite_avx2(values+consumed,n*n-consumed))return {false,false,0};
      return {true,false,width};
    }
    // The remaining lower cells cannot increase this row's width; diagonal
    // and upper cells still must pass finite validation. No rescanning.
    if(!all_finite_avx2(row+j,n-j))return {false,false,0};
  }
  return {true,true,width};
}
#endif
template<bool Fused> static __m256d madd(__m256d x,__m256d y,__m256d z) {
  if constexpr(Fused)return _mm256_fmadd_pd(x,y,z);
  else return _mm256_add_pd(_mm256_mul_pd(x,y),z);
}
#ifdef CHOL_COLUMN_WORKSPACE
void transpose_factor_export_avx2(double* output,std::size_t stride,const double* source,std::size_t rows,std::size_t cols,std::size_t b,bool diagonal) {
  std::size_t r=0;
  for(;r+4<=rows;r+=4) {
    std::size_t c=0;const auto common=diagonal?std::min(cols,r):cols;
    for(;c+4<=common;c+=4) {
      const auto x0=_mm256_loadu_pd(source+c*b+r),x1=_mm256_loadu_pd(source+(c+1)*b+r);
      const auto x2=_mm256_loadu_pd(source+(c+2)*b+r),x3=_mm256_loadu_pd(source+(c+3)*b+r);
      const auto t0=_mm256_unpacklo_pd(x0,x1),t1=_mm256_unpackhi_pd(x0,x1);
      const auto t2=_mm256_unpacklo_pd(x2,x3),t3=_mm256_unpackhi_pd(x2,x3);
      auto* target=output+r*stride+c;
      _mm256_storeu_pd(target,_mm256_permute2f128_pd(t0,t2,0x20));
      _mm256_storeu_pd(target+stride,_mm256_permute2f128_pd(t1,t3,0x20));
      _mm256_storeu_pd(target+2*stride,_mm256_permute2f128_pd(t0,t2,0x31));
      _mm256_storeu_pd(target+3*stride,_mm256_permute2f128_pd(t1,t3,0x31));
    }
    for(std::size_t lane=0;lane<4;++lane) {
      const auto end=diagonal?std::min(cols,r+lane+1):cols;
      for(std::size_t h=c;h<end;++h)output[(r+lane)*stride+h]=source[h*b+r+lane];
    }
  }
  for(;r<rows;++r)for(std::size_t c=0;c<(diagonal?std::min(cols,r+1):cols);++c)output[r*stride+c]=source[c*b+r];
}
template<bool Fused>static void column_rank(double* target,const double* left,double right,std::size_t count) {
  const auto y=_mm256_set1_pd(right);std::size_t r=0;
  for(;r+4<=count;r+=4)_mm256_storeu_pd(target+r,madd<Fused>(_mm256_loadu_pd(left+r),y,_mm256_loadu_pd(target+r)));
  for(;r<count;++r) {
    if constexpr(Fused)target[r]=std::fma(left[r],right,target[r]);
    else target[r]=left[r]*right+target[r];
  }
}
void ordered_column_update_avx2(double* target,const double* left,double right,std::size_t count,bool fused) {
  if(fused)column_rank<true>(target,left,right,count);else column_rank<false>(target,left,right,count);
}
template<bool Fused>static void column_tile(double* output,const double* left,const double* right,std::size_t rows,std::size_t cols,std::size_t depth,std::size_t b,bool diagonal) {
  std::size_t c=0;
  // Four columns share each left-factor vector, while each output retains its
  // own ascending k chain and original left*right operand order.
  if(!diagonal)for(;c+4<=cols;c+=4) {
    std::size_t r=0;
    for(;r+8<=rows;r+=8) {
      auto* t0=output+c*b+r;auto* t1=t0+b;auto* t2=t1+b;auto* t3=t2+b;
      auto a0=_mm256_loadu_pd(t0),a1=_mm256_loadu_pd(t0+4);
      auto d0=_mm256_loadu_pd(t1),d1=_mm256_loadu_pd(t1+4);
      auto e0=_mm256_loadu_pd(t2),e1=_mm256_loadu_pd(t2+4);
      auto f0=_mm256_loadu_pd(t3),f1=_mm256_loadu_pd(t3+4);
      for(std::size_t k=0;k<depth;++k) {
        const auto x0=_mm256_loadu_pd(left+k*b+r),x1=_mm256_loadu_pd(left+k*b+r+4);
        const auto y0=_mm256_set1_pd(right[k*b+c]),y1=_mm256_set1_pd(right[k*b+c+1]);
        const auto y2=_mm256_set1_pd(right[k*b+c+2]),y3=_mm256_set1_pd(right[k*b+c+3]);
        a0=madd<Fused>(x0,y0,a0);a1=madd<Fused>(x1,y0,a1);
        d0=madd<Fused>(x0,y1,d0);d1=madd<Fused>(x1,y1,d1);
        e0=madd<Fused>(x0,y2,e0);e1=madd<Fused>(x1,y2,e1);
        f0=madd<Fused>(x0,y3,f0);f1=madd<Fused>(x1,y3,f1);
      }
      _mm256_storeu_pd(t0,a0);_mm256_storeu_pd(t0+4,a1);_mm256_storeu_pd(t1,d0);_mm256_storeu_pd(t1+4,d1);
      _mm256_storeu_pd(t2,e0);_mm256_storeu_pd(t2+4,e1);_mm256_storeu_pd(t3,f0);_mm256_storeu_pd(t3+4,f1);
    }
    for(;r<rows;++r)for(std::size_t lane=0;lane<4;++lane) {
      auto value=output[(c+lane)*b+r];
      for(std::size_t k=0;k<depth;++k) {
        if constexpr(Fused)value=std::fma(left[k*b+r],right[k*b+c+lane],value);
        else value=left[k*b+r]*right[k*b+c+lane]+value;
      }
      output[(c+lane)*b+r]=value;
    }
  }
  for(;c<cols;++c) {
    std::size_t r=diagonal?c:0;
    for(;r+16<=rows;r+=16) {
      auto* t=output+c*b+r;
      auto a0=_mm256_loadu_pd(t),a1=_mm256_loadu_pd(t+4),a2=_mm256_loadu_pd(t+8),a3=_mm256_loadu_pd(t+12);
      for(std::size_t k=0;k<depth;++k) {
        const auto y=_mm256_set1_pd(right[k*b+c]);const auto* x=left+k*b+r;
        a0=madd<Fused>(_mm256_loadu_pd(x),y,a0);a1=madd<Fused>(_mm256_loadu_pd(x+4),y,a1);
        a2=madd<Fused>(_mm256_loadu_pd(x+8),y,a2);a3=madd<Fused>(_mm256_loadu_pd(x+12),y,a3);
      }
      _mm256_storeu_pd(t,a0);_mm256_storeu_pd(t+4,a1);_mm256_storeu_pd(t+8,a2);_mm256_storeu_pd(t+12,a3);
    }
    for(;r+4<=rows;r+=4) {
      auto value=_mm256_loadu_pd(output+c*b+r);
      for(std::size_t k=0;k<depth;++k)value=madd<Fused>(_mm256_loadu_pd(left+k*b+r),_mm256_set1_pd(right[k*b+c]),value);
      _mm256_storeu_pd(output+c*b+r,value);
    }
    for(;r<rows;++r) {
      auto value=output[c*b+r];
      for(std::size_t k=0;k<depth;++k) {
        if constexpr(Fused)value=std::fma(left[k*b+r],right[k*b+c],value);
        else value=left[k*b+r]*right[k*b+c]+value;
      }
      output[c*b+r]=value;
    }
  }
}
void ordered_column_tile_avx2(double* output,const double* left,const double* right,std::size_t rows,std::size_t cols,std::size_t depth,std::size_t b,bool diagonal,bool fused) {
  if(fused)column_tile<true>(output,left,right,rows,cols,depth,b,diagonal);else column_tile<false>(output,left,right,rows,cols,depth,b,diagonal);
}
#endif
#ifdef CHOL_VECTOR_PANEL
template<bool Fused>static void row_update(double*target,const double*factor,double value,std::size_t count) {
  const auto x=_mm256_set1_pd(value);std::size_t h=0;
  for(;h+16<=count;h+=16) {
    _mm256_storeu_pd(target+h,madd<Fused>(x,_mm256_loadu_pd(factor+h),_mm256_loadu_pd(target+h)));
    _mm256_storeu_pd(target+h+4,madd<Fused>(x,_mm256_loadu_pd(factor+h+4),_mm256_loadu_pd(target+h+4)));
    _mm256_storeu_pd(target+h+8,madd<Fused>(x,_mm256_loadu_pd(factor+h+8),_mm256_loadu_pd(target+h+8)));
    _mm256_storeu_pd(target+h+12,madd<Fused>(x,_mm256_loadu_pd(factor+h+12),_mm256_loadu_pd(target+h+12)));
  }
  for(;h+4<=count;h+=4)_mm256_storeu_pd(target+h,madd<Fused>(x,_mm256_loadu_pd(factor+h),_mm256_loadu_pd(target+h)));
  for(;h<count;++h) {
    if constexpr(Fused)target[h]=std::fma(value,factor[h],target[h]);
    else target[h]=value*factor[h]+target[h];
  }
}
void ordered_row_update_avx2(double*target,const double*factor,double value,std::size_t count,bool fused) {
  if(fused)row_update<true>(target,factor,value,count);else row_update<false>(target,factor,value,count);
}
#endif
template<bool Fused> static void ordered_update(double* output,std::size_t stride,const double* left,const double* right,std::size_t rows,std::size_t cols,std::size_t depth,std::size_t b,bool diagonal,std::size_t logical_size) {
  std::size_t first_row=0;
#if CHOL_AVX_ROW_GROUP == 8
  // Experimental eight rows x four columns: eight vector accumulators and one
  // shared right factor. Independent outputs keep the original ordered chain.
  if(!diagonal)for(;first_row+7<rows;first_row+=8) {
    auto* t=output+first_row*stride;std::size_t h=0;
    for(;h+4<=cols;h+=4) {
      auto a0=_mm256_loadu_pd(t+h),a1=_mm256_loadu_pd(t+stride+h);
      auto a2=_mm256_loadu_pd(t+2*stride+h),a3=_mm256_loadu_pd(t+3*stride+h);
      auto a4=_mm256_loadu_pd(t+4*stride+h),a5=_mm256_loadu_pd(t+5*stride+h);
      auto a6=_mm256_loadu_pd(t+6*stride+h),a7=_mm256_loadu_pd(t+7*stride+h);
      for(std::size_t k=0;k<depth;++k) {
        const auto y=_mm256_loadu_pd(right+k*b+h);const auto* x=left+k*b+first_row;
        a0=madd<Fused>(_mm256_set1_pd(x[0]),y,a0);a1=madd<Fused>(_mm256_set1_pd(x[1]),y,a1);
        a2=madd<Fused>(_mm256_set1_pd(x[2]),y,a2);a3=madd<Fused>(_mm256_set1_pd(x[3]),y,a3);
        a4=madd<Fused>(_mm256_set1_pd(x[4]),y,a4);a5=madd<Fused>(_mm256_set1_pd(x[5]),y,a5);
        a6=madd<Fused>(_mm256_set1_pd(x[6]),y,a6);a7=madd<Fused>(_mm256_set1_pd(x[7]),y,a7);
      }
      _mm256_storeu_pd(t+h,a0);_mm256_storeu_pd(t+stride+h,a1);_mm256_storeu_pd(t+2*stride+h,a2);_mm256_storeu_pd(t+3*stride+h,a3);
      _mm256_storeu_pd(t+4*stride+h,a4);_mm256_storeu_pd(t+5*stride+h,a5);_mm256_storeu_pd(t+6*stride+h,a6);_mm256_storeu_pd(t+7*stride+h,a7);
    }
    for(;h<cols;++h)for(std::size_t row=0;row<8;++row) {
      auto sum=t[row*stride+h];
      for(std::size_t k=0;k<depth;++k) {
        if constexpr(Fused)sum=std::fma(left[k*b+first_row+row],right[k*b+h],sum);
        else sum=left[k*b+first_row+row]*right[k*b+h]+sum;
      }
      t[row*stride+h]=sum;
    }
  }
#endif
#if CHOL_AVX_ROW_GROUP == 0 || CHOL_AVX_ROW_GROUP == 4 || CHOL_AVX_ROW_GROUP == 8
  // Four rows x eight columns use the same eight vector accumulators as the
  // two-row kernel, while sharing each right-factor load across four rows.
  if(!diagonal && (CHOL_AVX_ROW_GROUP!=0||logical_size>=2048))for(;first_row+3<rows;first_row+=4) {
    auto* t0=output+first_row*stride;auto* t1=t0+stride;auto* t2=t1+stride;auto* t3=t2+stride;
    std::size_t h=0;
    for(;h+8<=cols;h+=8) {
      auto a0=_mm256_loadu_pd(t0+h),a1=_mm256_loadu_pd(t0+h+4);
      auto c0=_mm256_loadu_pd(t1+h),c1=_mm256_loadu_pd(t1+h+4);
      auto d0=_mm256_loadu_pd(t2+h),d1=_mm256_loadu_pd(t2+h+4);
      auto e0=_mm256_loadu_pd(t3+h),e1=_mm256_loadu_pd(t3+h+4);
      for(std::size_t k=0;k<depth;++k) {
        const auto x0=_mm256_set1_pd(left[k*b+first_row]),x1=_mm256_set1_pd(left[k*b+first_row+1]);
        const auto x2=_mm256_set1_pd(left[k*b+first_row+2]),x3=_mm256_set1_pd(left[k*b+first_row+3]);
        const auto y0=_mm256_loadu_pd(right+k*b+h);
        a0=madd<Fused>(x0,y0,a0);c0=madd<Fused>(x1,y0,c0);d0=madd<Fused>(x2,y0,d0);e0=madd<Fused>(x3,y0,e0);
        const auto y1=_mm256_loadu_pd(right+k*b+h+4);
        a1=madd<Fused>(x0,y1,a1);c1=madd<Fused>(x1,y1,c1);d1=madd<Fused>(x2,y1,d1);e1=madd<Fused>(x3,y1,e1);
      }
      _mm256_storeu_pd(t0+h,a0);_mm256_storeu_pd(t0+h+4,a1);_mm256_storeu_pd(t1+h,c0);_mm256_storeu_pd(t1+h+4,c1);
      _mm256_storeu_pd(t2+h,d0);_mm256_storeu_pd(t2+h+4,d1);_mm256_storeu_pd(t3+h,e0);_mm256_storeu_pd(t3+h+4,e1);
    }
    for(;h+4<=cols;h+=4) {
      auto a=_mm256_loadu_pd(t0+h),c=_mm256_loadu_pd(t1+h),d=_mm256_loadu_pd(t2+h),e=_mm256_loadu_pd(t3+h);
      for(std::size_t k=0;k<depth;++k) {
        const auto y=_mm256_loadu_pd(right+k*b+h);
        a=madd<Fused>(_mm256_set1_pd(left[k*b+first_row]),y,a);c=madd<Fused>(_mm256_set1_pd(left[k*b+first_row+1]),y,c);
        d=madd<Fused>(_mm256_set1_pd(left[k*b+first_row+2]),y,d);e=madd<Fused>(_mm256_set1_pd(left[k*b+first_row+3]),y,e);
      }
      _mm256_storeu_pd(t0+h,a);_mm256_storeu_pd(t1+h,c);_mm256_storeu_pd(t2+h,d);_mm256_storeu_pd(t3+h,e);
    }
    for(;h<cols;++h) {
      auto a=t0[h],c=t1[h],d=t2[h],e=t3[h];
      for(std::size_t k=0;k<depth;++k) {
        const auto y=right[k*b+h];
        if constexpr(Fused){a=std::fma(left[k*b+first_row],y,a);c=std::fma(left[k*b+first_row+1],y,c);d=std::fma(left[k*b+first_row+2],y,d);e=std::fma(left[k*b+first_row+3],y,e);}
        else {a=left[k*b+first_row]*y+a;c=left[k*b+first_row+1]*y+c;d=left[k*b+first_row+2]*y+d;e=left[k*b+first_row+3]*y+e;}
      }
      t0[h]=a;t1[h]=c;t2[h]=d;t3[h]=e;
    }
  }
#endif
#if CHOL_AVX_ROW_GROUP == 0 || CHOL_AVX_ROW_GROUP == 2 || CHOL_AVX_ROW_GROUP == 8
  // Two independent rows share the same factor vectors. Each accumulator still
  // sees k=0..depth-1 in source order; there is no reduction reassociation.
  if(!diagonal)for(;first_row+1<rows;first_row+=2) {
    auto* target0=output+first_row*stride;auto* target1=target0+stride;
    std::size_t h=0;
    for(;h+16<=cols;h+=16) {
      auto a0=_mm256_loadu_pd(target0+h),a1=_mm256_loadu_pd(target0+h+4),a2=_mm256_loadu_pd(target0+h+8),a3=_mm256_loadu_pd(target0+h+12);
      auto c0=_mm256_loadu_pd(target1+h),c1=_mm256_loadu_pd(target1+h+4),c2=_mm256_loadu_pd(target1+h+8),c3=_mm256_loadu_pd(target1+h+12);
      for(std::size_t k=0;k<depth;++k) {
        const auto x0=_mm256_set1_pd(left[k*b+first_row]),x1=_mm256_set1_pd(left[k*b+first_row+1]);const auto* y=right+k*b+h;
        const auto y0=_mm256_loadu_pd(y);a0=madd<Fused>(x0,y0,a0);c0=madd<Fused>(x1,y0,c0);
        const auto y1=_mm256_loadu_pd(y+4);a1=madd<Fused>(x0,y1,a1);c1=madd<Fused>(x1,y1,c1);
        const auto y2=_mm256_loadu_pd(y+8);a2=madd<Fused>(x0,y2,a2);c2=madd<Fused>(x1,y2,c2);
        const auto y3=_mm256_loadu_pd(y+12);a3=madd<Fused>(x0,y3,a3);c3=madd<Fused>(x1,y3,c3);
      }
      _mm256_storeu_pd(target0+h,a0);_mm256_storeu_pd(target0+h+4,a1);_mm256_storeu_pd(target0+h+8,a2);_mm256_storeu_pd(target0+h+12,a3);
      _mm256_storeu_pd(target1+h,c0);_mm256_storeu_pd(target1+h+4,c1);_mm256_storeu_pd(target1+h+8,c2);_mm256_storeu_pd(target1+h+12,c3);
    }
    for(;h+4<=cols;h+=4) {
      auto a=_mm256_loadu_pd(target0+h),c=_mm256_loadu_pd(target1+h);
      for(std::size_t k=0;k<depth;++k) {
        const auto y=_mm256_loadu_pd(right+k*b+h);
        a=madd<Fused>(_mm256_set1_pd(left[k*b+first_row]),y,a);c=madd<Fused>(_mm256_set1_pd(left[k*b+first_row+1]),y,c);
      }
      _mm256_storeu_pd(target0+h,a);_mm256_storeu_pd(target1+h,c);
    }
    for(;h<cols;++h) {
      auto a=target0[h],c=target1[h];
      for(std::size_t k=0;k<depth;++k) {
        const auto y=right[k*b+h];
        if constexpr(Fused){a=std::fma(left[k*b+first_row],y,a);c=std::fma(left[k*b+first_row+1],y,c);}
        else {a=left[k*b+first_row]*y+a;c=left[k*b+first_row+1]*y+c;}
      }
      target0[h]=a;target1[h]=c;
    }
  }
#endif
  for(std::size_t j=first_row;j<rows;++j) {
    auto* target=output+j*stride;const auto end=diagonal?std::min(cols,j+1):cols;
    std::size_t h=0;
    for(;h+16<=end;h+=16) {
      auto z0=_mm256_loadu_pd(target+h),z1=_mm256_loadu_pd(target+h+4),z2=_mm256_loadu_pd(target+h+8),z3=_mm256_loadu_pd(target+h+12);
      for(std::size_t k=0;k<depth;++k) {
        const auto x=_mm256_set1_pd(left[k*b+j]);const auto* y=right+k*b+h;
        z0=madd<Fused>(x,_mm256_loadu_pd(y),z0);z1=madd<Fused>(x,_mm256_loadu_pd(y+4),z1);
        z2=madd<Fused>(x,_mm256_loadu_pd(y+8),z2);z3=madd<Fused>(x,_mm256_loadu_pd(y+12),z3);
      }
      _mm256_storeu_pd(target+h,z0);_mm256_storeu_pd(target+h+4,z1);_mm256_storeu_pd(target+h+8,z2);_mm256_storeu_pd(target+h+12,z3);
    }
    for(;h+4<=end;h+=4) {
      auto z=_mm256_loadu_pd(target+h);
      for(std::size_t k=0;k<depth;++k)z=madd<Fused>(_mm256_set1_pd(left[k*b+j]),_mm256_loadu_pd(right+k*b+h),z);
      _mm256_storeu_pd(target+h,z);
    }
    for(;h<end;++h) {
      auto z=target[h];
      for(std::size_t k=0;k<depth;++k) {
        if constexpr(Fused)z=std::fma(left[k*b+j],right[k*b+h],z);
        else z=left[k*b+j]*right[k*b+h]+z;
      }
      target[h]=z;
    }
  }
}
void ordered_update_avx2(double* output,std::size_t stride,const double* left,const double* right,std::size_t rows,std::size_t cols,std::size_t depth,std::size_t b,bool diagonal,bool fused,std::size_t logical_size) {
  if(fused)ordered_update<true>(output,stride,left,right,rows,cols,depth,b,diagonal,logical_size);
  else ordered_update<false>(output,stride,left,right,rows,cols,depth,b,diagonal,logical_size);
}
}
