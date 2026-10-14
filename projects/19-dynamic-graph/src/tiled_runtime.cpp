#include "cholesky/runtime.hpp"
#include "native_input_scan.hpp"
#ifdef CHOL_CACHE_NATIVE_WORKSPACE
#include "cholesky/native_workspace.hpp"
#include <optional>
#endif
#ifdef CHOL_REUSE_WORKERS
#include "cholesky/execution_context.hpp"
#endif
#ifdef CHOL_HAVE_AVX512_KERNEL
#include "cholesky/simd_dispatch.hpp"
#endif
#include <algorithm>
#include <bit>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <exception>
#include <deque>
#include <limits>
#include <mutex>
#include <memory>
#include <new>
#include <queue>
#include <stdexcept>
#include <thread>
#include <utility>
#ifndef CHOL_UPDATE_WIDTH
#define CHOL_UPDATE_WIDTH 4
#endif
#ifndef CHOL_PACK_INITIALIZATION
#define CHOL_PACK_INITIALIZATION 0
#endif

namespace chol {
#ifdef CHOL_HAVE_AVX512_KERNEL
void ordered_update_avx512(double*,std::size_t,const double*,const double*,std::size_t,std::size_t,std::size_t,std::size_t,bool,bool);
#endif
bool try_structured_factor(const Matrix&,Matrix&,Options,bool);
#ifdef CHOL_HAVE_X86_SIMD
void ordered_update_avx2(double*,std::size_t,const double*,const double*,std::size_t,std::size_t,std::size_t,std::size_t,bool,bool,std::size_t);
#ifdef CHOL_COLUMN_WORKSPACE
void transpose_factor_export_avx2(double*,std::size_t,const double*,std::size_t,std::size_t,std::size_t,bool);
void ordered_column_update_avx2(double*,const double*,double,std::size_t,bool);
void ordered_column_tile_avx2(double*,const double*,const double*,std::size_t,std::size_t,std::size_t,std::size_t,bool,bool);
#endif
#ifdef CHOL_VECTOR_PANEL
void ordered_row_update_avx2(double*,const double*,double,std::size_t,bool);
#endif
#endif
namespace {
using Clock = std::chrono::steady_clock;
double elapsed(Clock::time_point start) { return std::chrono::duration<double,std::milli>(Clock::now()-start).count(); }
enum class Kind : std::uint8_t { Factor, Solve, Update };
struct Task {
  std::uint16_t panel, row, col;
  Kind kind;
  std::uint8_t pending;
};
static_assert(sizeof(Task)==8);
struct AlignedDelete {
  void operator()(double* pointer)const noexcept {::operator delete[](pointer,std::align_val_t(64));}
};

class TileProgram {
  const Matrix& input_;
  Matrix& output_;
  const std::size_t n_, b_, tiles_;
  const bool fused_;
  const bool simd_;
  const bool avx512_;
  std::unique_ptr<double[],AlignedDelete> factors_;
  double* factor_data_=nullptr;
  std::size_t packed_elements_=0;
  std::uint64_t logical_tasks_=0;
  std::vector<std::size_t> panel_offsets_;
public:
  std::vector<Task> tasks;
  TileProgram(const Matrix& input, Matrix& output, unsigned tile_size, bool fused,bool simd,bool serial_walk=false,bool avx512=false,double* leased_factors=nullptr)
    : input_(input), output_(output), n_(input.n), b_(tile_size), tiles_((n_+b_-1)/b_), fused_(fused),simd_(simd),avx512_(avx512) {
    const auto count=std::uint64_t(tiles_)*(tiles_+1)*(tiles_+2)/6;
    logical_tasks_=count;
    if(count>16000000)throw std::runtime_error("tile graph exceeds 16 million tasks; increase --tile-size");
    packed_elements_=tiles_*(tiles_+1)/2*b_*b_;
    if(leased_factors)factor_data_=leased_factors;
    else {
      factors_.reset(static_cast<double*>(::operator new[](packed_elements_*sizeof(double),std::align_val_t(64))));
      factor_data_=factors_.get();
    }
    // In row-major mode every factor read follows its P/T assignment; NaN
    // POISON verifies that property. The unified column workspace also holds
    // accumulators, so its initial +0 state is mandatory in every pack mode.
    // Neither mode reads padded coordinates.
#if defined(CHOL_TILE_FIRST_TOUCH)
    // The unique panel-0 task initializes each destination's valid +0 cells.
    // Its dependency chain orders every later accumulator read.
#elif CHOL_PACK_INITIALIZATION == 0 || defined(CHOL_COLUMN_WORKSPACE)
    std::fill_n(factor_data_,packed_elements_,0.0);
#elif CHOL_PACK_INITIALIZATION == 2
    std::fill_n(factor_data_,packed_elements_,std::numeric_limits<double>::quiet_NaN());
#elif CHOL_PACK_INITIALIZATION != 1
#error Invalid CHOL_PACK_INITIALIZATION
#endif
#ifdef CHOL_SERIAL_TILE_WALK
    if(serial_walk)return; // Logical cap and factor initialization still apply.
#else
    (void)serial_walk;
#endif
#ifdef CHOL_LAZY_TILE_GRAPH
    tasks.reserve(tiles_*(tiles_+1)/2);
    // pending becomes a state: 0 blocked, 1 queued, 2 running, 3 factor done.
    // Each destination retains only its next panel; completed factors are
    // immutable and their owning destination state supplies readiness.
    for(std::size_t row=0;row<tiles_;++row)for(std::size_t col=0;col<=row;++col) {
      std::uint8_t waiting=0;
#ifdef CHOL_LAZY_CACHED_WAIT
      waiting=col?(row==col?1:2):(row?1:0);
#endif
      tasks.push_back({0,static_cast<std::uint16_t>(row),static_cast<std::uint16_t>(col),col?Kind::Update:(row?Kind::Solve:Kind::Factor),waiting});
    }
#else
    panel_offsets_.resize(tiles_);tasks.reserve(count);
    auto add = [&](Kind kind,std::size_t k,std::size_t m,std::size_t h,unsigned prerequisites) {
      tasks.push_back({static_cast<std::uint16_t>(k),static_cast<std::uint16_t>(m),static_cast<std::uint16_t>(h),kind,static_cast<std::uint8_t>(prerequisites)});
    };
    for (std::size_t k=0;k<tiles_;++k) {
      panel_offsets_[k]=tasks.size();
      add(Kind::Factor,k,k,k,k?1:0);
      for (std::size_t m=k+1;m<tiles_;++m)add(Kind::Solve,k,m,k,k?2:1);
      for (std::size_t h=k+1;h<tiles_;++h) for (std::size_t m=h;m<tiles_;++m)
        add(Kind::Update,k,m,h,(m==h?1:2)+(k?1:0));
    }
#endif
  }
  std::uint64_t logical_tasks()const{return logical_tasks_;}
  std::size_t bytes() const { return packed_elements_*sizeof(double); }
  std::size_t graph_bytes() const {
    auto bytes=tasks.capacity()*sizeof(Task)+panel_offsets_.size()*sizeof(std::size_t);
#ifdef CHOL_LAZY_CACHED_WAIT
    if(!tasks.empty())bytes+=tiles_*sizeof(std::int16_t);
#endif
    return bytes;
  }
  std::size_t solve_id(std::size_t row,std::size_t panel) const { return panel_offsets_[panel]+row-panel; }
  std::size_t update_id(std::size_t row,std::size_t col,std::size_t panel) const {
    const auto preceding=col-panel-1;
    return panel_offsets_[panel]+tiles_-panel+preceding*(2*(tiles_-panel)-preceding-1)/2+row-col;
  }
  template<class Retire> void users(std::size_t index,Retire retire) const {
    const auto& t=tasks[index];const std::size_t k=t.panel,m=t.row,h=t.col;
    // Symbolic successors replace a separately allocated edge list per task.
    switch(t.kind) {
      case Kind::Factor:
        for(std::size_t row=k+1;row<tiles_;++row)retire(solve_id(row,k));
        break;
      case Kind::Solve:
        for(std::size_t col=k+1;col<=m;++col)retire(update_id(m,col,k));
        for(std::size_t row=m+1;row<tiles_;++row)retire(update_id(row,m,k));
        break;
      case Kind::Update:
        if(k+1<h)retire(update_id(m,h,k+1));
        else if(m==h)retire(panel_offsets_[h]);
        else retire(solve_id(m,h));
        break;
    }
  }
  double* packed(std::size_t row,std::size_t col) { return factor_data_+(row*(row+1)/2+col)*b_*b_; }
  template<bool Fused> void factor_impl(std::size_t tile) {
    auto* l=output_.values.data(); const auto* a=input_.values.data();
    auto* diagonal=packed(tile,tile);
    const auto begin=tile*b_,end=std::min(n_,begin+b_);
    for(std::size_t i=begin;i<end;++i) {
      const auto pivot=a[i*n_+i]-l[i*n_+i];
      if(!(pivot>0.0)||!std::isfinite(pivot)) throw std::runtime_error("matrix is not positive definite at pivot "+std::to_string(i));
      l[i*n_+i]=std::sqrt(pivot);
      diagonal[(i-begin)*b_+i-begin]=l[i*n_+i];
      for(std::size_t j=i+1;j<end;++j) {
        l[j*n_+i]=(a[j*n_+i]-l[j*n_+i])/l[i*n_+i];
        const auto value=l[j*n_+i];
        diagonal[(i-begin)*b_+j-begin]=value;
#if defined(CHOL_VECTOR_PANEL) && defined(CHOL_HAVE_X86_SIMD)
        if(simd_&&b_>=64&&j-i>=8)ordered_row_update_avx2(l+j*n_+i+1,diagonal+(i-begin)*b_+i+1-begin,value,j-i,Fused);
        else
#endif
        for(std::size_t k=i+1;k<=j;++k) l[j*n_+k]=ordered_madd<Fused>(value,diagonal[(i-begin)*b_+k-begin],l[j*n_+k]);
      }
    }
  }
  void factor(std::size_t tile) {if(fused_)factor_impl<true>(tile);else factor_impl<false>(tile);}
  template<bool Fused> void solve_impl(std::size_t row,std::size_t panel) {
    auto* l=output_.values.data(); const auto* a=input_.values.data();
    const auto* diagonal=packed(panel,panel);auto* factor=packed(row,panel);
    const auto begin=panel*b_,end=std::min(n_,begin+b_);
    const auto first=row*b_,last=std::min(n_,first+b_);
    for(std::size_t i=begin;i<end;++i) for(std::size_t j=first;j<last;++j) {
      l[j*n_+i]=(a[j*n_+i]-l[j*n_+i])/diagonal[(i-begin)*b_+i-begin];
      const auto value=l[j*n_+i];
      factor[(i-begin)*b_+j-first]=value;
#if defined(CHOL_VECTOR_PANEL) && defined(CHOL_HAVE_X86_SIMD)
      if(simd_&&b_>=64&&end-i-1>=8)ordered_row_update_avx2(l+j*n_+i+1,diagonal+(i-begin)*b_+i+1-begin,value,end-i-1,Fused);
      else
#endif
      for(std::size_t k=i+1;k<end;++k) l[j*n_+k]=ordered_madd<Fused>(value,diagonal[(i-begin)*b_+k-begin],l[j*n_+k]);
    }
  }
  void solve(std::size_t row,std::size_t panel) {if(fused_)solve_impl<true>(row,panel);else solve_impl<false>(row,panel);}
  template<bool Fused> static double ordered_madd(double x,double y,double z) {
    if constexpr(Fused) return std::fma(x,y,z);
    else return x*y+z;
  }
  template<unsigned Width,bool Fused> void update_group(double* target,const double* left,const double* right,std::size_t j,std::size_t h,std::size_t depth) {
    double accumulators[Width];
    for(unsigned lane=0;lane<Width;++lane)accumulators[lane]=target[h+lane];
    for(std::size_t k=0;k<depth;++k) {
      const auto x=left[k*b_+j];const auto* y=right+k*b_+h;
      #pragma GCC unroll 16
      for(unsigned lane=0;lane<Width;++lane)accumulators[lane]=ordered_madd<Fused>(x,y[lane],accumulators[lane]);
    }
    for(unsigned lane=0;lane<Width;++lane)target[h+lane]=accumulators[lane];
  }
  template<bool Fused> void update_impl(std::size_t row,std::size_t col,std::size_t panel) {
    auto* l=output_.values.data(); const auto* left=packed(row,panel); const auto* right=packed(col,panel);
    const auto rows=std::min(b_,n_-row*b_),cols=std::min(b_,n_-col*b_),depth=std::min(b_,n_-panel*b_);
    for(std::size_t j=0;j<rows;++j) {
      auto* target=l+(row*b_+j)*n_+col*b_;
      const auto end=row==col?std::min(cols,j+1):cols;
      std::size_t h=0;
      // Independent accumulators expose SIMD/ILP without reassociating any
      // individual reduction. Every cell observes source panel/column order.
      if constexpr(CHOL_UPDATE_WIDTH>4)
        for(;h+CHOL_UPDATE_WIDTH<=end;h+=CHOL_UPDATE_WIDTH)update_group<CHOL_UPDATE_WIDTH,Fused>(target,left,right,j,h,depth);
      for(;h+4<=end;h+=4) {
        auto z0=target[h],z1=target[h+1],z2=target[h+2],z3=target[h+3];
        for(std::size_t k=0;k<depth;++k) {
          const auto x=left[k*b_+j]; const auto* y=right+k*b_+h;
          z0=ordered_madd<Fused>(x,y[0],z0); z1=ordered_madd<Fused>(x,y[1],z1); z2=ordered_madd<Fused>(x,y[2],z2); z3=ordered_madd<Fused>(x,y[3],z3);
        }
        target[h]=z0;target[h+1]=z1;target[h+2]=z2;target[h+3]=z3;
      }
      for(;h<end;++h) {
        auto accumulator=target[h];
        for(std::size_t k=0;k<depth;++k) accumulator=ordered_madd<Fused>(left[k*b_+j],right[k*b_+h],accumulator);
        target[h]=accumulator;
      }
    }
  }
  void update(std::size_t row,std::size_t col,std::size_t panel) {
#ifdef CHOL_HAVE_AVX512_KERNEL
    if(avx512_) {
      ordered_update_avx512(output_.values.data()+row*b_*n_+col*b_,n_,packed(row,panel),packed(col,panel),std::min(b_,n_-row*b_),std::min(b_,n_-col*b_),std::min(b_,n_-panel*b_),b_,row==col,fused_);return;
    }
#endif
#ifdef CHOL_HAVE_X86_SIMD
    if(simd_) {
      ordered_update_avx2(output_.values.data()+row*b_*n_+col*b_,n_,packed(row,panel),packed(col,panel),std::min(b_,n_-row*b_),std::min(b_,n_-col*b_),std::min(b_,n_-panel*b_),b_,row==col,fused_,n_);return;
    }
#endif
    if(fused_)update_impl<true>(row,col,panel);
    else update_impl<false>(row,col,panel);
  }
#ifdef CHOL_COLUMN_WORKSPACE
  template<bool Fused>void column_rank(double* target,const double* left,double right,std::size_t count) {
#ifdef CHOL_HAVE_X86_SIMD
    if(simd_&&b_>=64&&count>=8){ordered_column_update_avx2(target,left,right,count,Fused);return;}
#endif
    for(std::size_t row=0;row<count;++row)target[row]=ordered_madd<Fused>(left[row],right,target[row]);
  }
  template<bool Fused>void column_factor(std::size_t tile) {
    auto* diagonal=packed(tile,tile);const auto first=tile*b_,depth=std::min(b_,n_-first);const auto* a=input_.values.data();
    for(std::size_t i=0;i<depth;++i) {
      const auto pivot=a[(first+i)*n_+first+i]-diagonal[i*b_+i];
      if(!(pivot>0.0)||!std::isfinite(pivot))throw std::runtime_error("matrix is not positive definite at pivot "+std::to_string(first+i));
      diagonal[i*b_+i]=std::sqrt(pivot);
      // These divisions read only column i. Updates write future columns, so
      // all j factors may be produced first without changing any FP chain.
      for(std::size_t j=i+1;j<depth;++j)diagonal[i*b_+j]=(a[(first+j)*n_+first+i]-diagonal[i*b_+j])/diagonal[i*b_+i];
      for(std::size_t k=i+1;k<depth;++k)column_rank<Fused>(diagonal+k*b_+k,diagonal+i*b_+k,diagonal[i*b_+k],depth-k);
    }
  }
  template<bool Fused>void column_solve(std::size_t row,std::size_t panel) {
    auto* target=packed(row,panel);const auto* diagonal=packed(panel,panel);const auto* a=input_.values.data();
    const auto first=row*b_,begin=panel*b_,rows=std::min(b_,n_-first),depth=std::min(b_,n_-begin);
    for(std::size_t i=0;i<depth;++i) {
      for(std::size_t j=0;j<rows;++j)target[i*b_+j]=(a[(first+j)*n_+begin+i]-target[i*b_+j])/diagonal[i*b_+i];
      for(std::size_t k=i+1;k<depth;++k)column_rank<Fused>(target+k*b_,target+i*b_,diagonal[i*b_+k],rows);
    }
  }
  template<bool Fused>void column_update(std::size_t row,std::size_t col,std::size_t panel) {
    auto* target=packed(row,col);const auto* left=packed(row,panel);const auto* right=packed(col,panel);
    const auto rows=std::min(b_,n_-row*b_),cols=std::min(b_,n_-col*b_),depth=std::min(b_,n_-panel*b_);
#ifdef CHOL_HAVE_X86_SIMD
    if(simd_){ordered_column_tile_avx2(target,left,right,rows,cols,depth,b_,row==col,Fused);return;}
#endif
    for(std::size_t col_index=0;col_index<cols;++col_index) {
      const auto first=row==col?col_index:0;std::size_t r=first;
      for(;r+CHOL_UPDATE_WIDTH<=rows;r+=CHOL_UPDATE_WIDTH) {
        double values[CHOL_UPDATE_WIDTH];
        for(unsigned lane=0;lane<CHOL_UPDATE_WIDTH;++lane)values[lane]=target[col_index*b_+r+lane];
        for(std::size_t k=0;k<depth;++k)for(unsigned lane=0;lane<CHOL_UPDATE_WIDTH;++lane)values[lane]=ordered_madd<Fused>(left[k*b_+r+lane],right[k*b_+col_index],values[lane]);
        for(unsigned lane=0;lane<CHOL_UPDATE_WIDTH;++lane)target[col_index*b_+r+lane]=values[lane];
      }
      for(;r<rows;++r) {
        auto value=target[col_index*b_+r];
        for(std::size_t k=0;k<depth;++k)value=ordered_madd<Fused>(left[k*b_+r],right[k*b_+col_index],value);
        target[col_index*b_+r]=value;
      }
    }
  }
#ifdef CHOL_ROW_TILE_WORKSPACE
  template<bool Fused>void row_tile_factor(std::size_t tile,std::vector<double>& scratch) {
    scratch.resize(b_*b_);auto* target=packed(tile,tile);const auto first=tile*b_,depth=std::min(b_,n_-first);const auto* a=input_.values.data();
    for(std::size_t i=0;i<depth;++i) {
      const auto pivot=a[(first+i)*n_+first+i]-target[i*b_+i];
      if(!(pivot>0.0)||!std::isfinite(pivot))throw std::runtime_error("matrix is not positive definite at pivot "+std::to_string(first+i));
      target[i*b_+i]=std::sqrt(pivot);scratch[i*b_+i]=target[i*b_+i];
      for(std::size_t j=i+1;j<depth;++j) {
        auto* destination=target+j*b_;
        destination[i]=(a[(first+j)*n_+first+i]-destination[i])/target[i*b_+i];
        const auto value=destination[i];scratch[i*b_+j]=value;
#if defined(CHOL_VECTOR_PANEL) && defined(CHOL_HAVE_X86_SIMD)
        if(simd_&&b_>=64&&j-i>=8)ordered_row_update_avx2(destination+i+1,scratch.data()+i*b_+i+1,value,j-i,Fused);
        else
#endif
        for(std::size_t k=i+1;k<=j;++k)destination[k]=ordered_madd<Fused>(value,scratch[i*b_+k],destination[k]);
      }
    }
    // This task exclusively owns its tile. Change its storage interpretation
    // only after all row accumulators are consumed and before retirement.
    for(std::size_t c=0;c<depth;++c)for(std::size_t r=c;r<depth;++r)target[c*b_+r]=scratch[c*b_+r];
  }
  template<bool Fused>void row_tile_solve(std::size_t row,std::size_t panel,std::vector<double>& scratch) {
    scratch.resize(b_*b_);auto* target=packed(row,panel);const auto* diagonal=packed(panel,panel);const auto* a=input_.values.data();
    const auto first=row*b_,begin=panel*b_,rows=std::min(b_,n_-first),depth=std::min(b_,n_-begin);
    for(std::size_t i=0;i<depth;++i)for(std::size_t j=0;j<rows;++j) {
      auto* destination=target+j*b_;
      destination[i]=(a[(first+j)*n_+begin+i]-destination[i])/diagonal[i*b_+i];
      const auto value=destination[i];scratch[i*b_+j]=value;
#if defined(CHOL_VECTOR_PANEL) && defined(CHOL_HAVE_X86_SIMD)
      if(simd_&&b_>=64&&depth-i-1>=8)ordered_row_update_avx2(destination+i+1,diagonal+i*b_+i+1,value,depth-i-1,Fused);
      else
#endif
      for(std::size_t k=i+1;k<depth;++k)destination[k]=ordered_madd<Fused>(value,diagonal[i*b_+k],destination[k]);
    }
    for(std::size_t c=0;c<depth;++c)std::copy_n(scratch.data()+c*b_,rows,target+c*b_);
  }
  template<bool Fused>void row_tile_update(std::size_t row,std::size_t col,std::size_t panel) {
    auto* target=packed(row,col);const auto* left=packed(row,panel);const auto* right=packed(col,panel);
    const auto rows=std::min(b_,n_-row*b_),cols=std::min(b_,n_-col*b_),depth=std::min(b_,n_-panel*b_);
#ifdef CHOL_HAVE_X86_SIMD
    if(simd_){ordered_update_avx2(target,b_,left,right,rows,cols,depth,b_,row==col,Fused,n_);return;}
#endif
    for(std::size_t j=0;j<rows;++j) {
      auto* destination=target+j*b_;const auto end=row==col?std::min(cols,j+1):cols;std::size_t h=0;
      for(;h+CHOL_UPDATE_WIDTH<=end;h+=CHOL_UPDATE_WIDTH)update_group<CHOL_UPDATE_WIDTH,Fused>(destination,left,right,j,h,depth);
      for(;h<end;++h) {
        auto value=destination[h];
        for(std::size_t k=0;k<depth;++k)value=ordered_madd<Fused>(left[k*b_+j],right[k*b_+h],value);
        destination[h]=value;
      }
    }
  }
#endif
#endif
  void export_output(unsigned workers) {
    (void)workers;
#ifdef CHOL_COLUMN_WORKSPACE
    auto* output=output_.values.data();
    auto export_rows=[&](std::size_t worker,std::size_t count) {
      for(std::size_t row=worker;row<tiles_;row+=count)for(std::size_t col=0;col<=row;++col) {
        const auto* source=packed(row,col);const auto rows=std::min(b_,n_-row*b_),cols=std::min(b_,n_-col*b_);
#if defined(CHOL_TRANSPOSE_EXPORT) && defined(CHOL_HAVE_X86_SIMD)
        if(simd_){transpose_factor_export_avx2(output+row*b_*n_+col*b_,n_,source,rows,cols,b_,row==col);continue;}
#endif
        for(std::size_t r=0;r<rows;++r)for(std::size_t c=0;c<(row==col?std::min(cols,r+1):cols);++c)
          output[(row*b_+r)*n_+col*b_+c]=source[c*b_+r];
      }
    };
#ifdef CHOL_TRANSPOSE_EXPORT
    const auto count=std::min(std::size_t(workers),tiles_);
    if(n_>=2048&&count>1) {
      std::vector<std::jthread> exporters;exporters.reserve(count);
      for(std::size_t worker=0;worker<count;++worker)exporters.emplace_back([&,worker]{export_rows(worker,count);});
      return; // jthread destruction joins before leaving this function.
    }
#endif
    export_rows(0,1);
#endif
  }
  void execute_task(const Task& task,[[maybe_unused]]std::vector<double>& scratch) {
#ifdef CHOL_TILE_FIRST_TOUCH
    if(task.panel==0) {
      // Row accumulator layout. Every destination has exactly one first
      // task: P(0), T(row,0), or U(row,col,0). Padding is never read.
      auto* target=packed(task.row,task.col);
      const auto rows=std::min(b_,n_-task.row*b_),cols=std::min(b_,n_-task.col*b_);
      for(std::size_t row=0;row<rows;++row)
        std::fill_n(target+row*b_,task.row==task.col?std::min(cols,row+1):cols,0.0);
    }
#endif
    switch(task.kind) {
#ifdef CHOL_COLUMN_WORKSPACE
#ifdef CHOL_ROW_TILE_WORKSPACE
      case Kind::Factor:if(fused_)row_tile_factor<true>(task.panel,scratch);else row_tile_factor<false>(task.panel,scratch);break;
      case Kind::Solve:if(fused_)row_tile_solve<true>(task.row,task.panel,scratch);else row_tile_solve<false>(task.row,task.panel,scratch);break;
      case Kind::Update:if(fused_)row_tile_update<true>(task.row,task.col,task.panel);else row_tile_update<false>(task.row,task.col,task.panel);break;
#else
      case Kind::Factor:if(fused_)column_factor<true>(task.panel);else column_factor<false>(task.panel);break;
      case Kind::Solve:if(fused_)column_solve<true>(task.row,task.panel);else column_solve<false>(task.row,task.panel);break;
      case Kind::Update:if(fused_)column_update<true>(task.row,task.col,task.panel);else column_update<false>(task.row,task.col,task.panel);break;
#endif
#else
      case Kind::Factor:factor(task.panel);break;
      case Kind::Solve:solve(task.row,task.panel);break;
      case Kind::Update:update(task.row,task.col,task.panel);break;
#endif
    }
  }
#ifdef CHOL_LAZY_TILE_GRAPH
  void run_lazy(unsigned threads,bool bucket,std::uint64_t* queue_peak,[[maybe_unused]] ExecutionContext* context) {
#ifdef CHOL_LAZY_CACHED_WAIT
    // 0..2 are blocked with that many current factor prerequisites remaining.
    constexpr std::uint8_t Blocked=0,Queued=4,Running=5,Done=6;
    // T(row,k) needs T(row,k-1), and P(row) needs its last T. Each row's
    // completed factor panels therefore form a prefix. This tiny directory
    // replaces triangular-index/random task-state reads when arming panel k.
    std::vector<std::int16_t> completed_panel(tiles_,-1);
#else
    constexpr std::uint8_t Blocked=0,Queued=1,Running=2,Done=3;
#endif
    std::mutex mutex;std::condition_variable condition;
#ifdef CHOL_PACKED_READY_KEYS
    // The existing 16-million task cap fits the low 32-bit ID. The high
    // fields reproduce the old (column, panel, task index) order exactly;
    // Task coordinates are already uint16_t. Heap entries remain 8 bytes.
    auto ready_key=[&](std::size_t index) {
      const auto& task=tasks[index];
      return (std::uint64_t(task.col)<<48)|(std::uint64_t(task.panel)<<32)|std::uint64_t(index);
    };
    std::priority_queue<std::uint64_t,std::vector<std::uint64_t>,std::greater<std::uint64_t>> heap;
#else
    auto lower_priority=[&](std::size_t a,std::size_t b) {
      const auto& x=tasks[a];const auto& y=tasks[b];
      const auto px=std::pair{x.col,x.panel},py=std::pair{y.col,y.panel};return px!=py?px>py:a>b;
    };
    std::priority_queue<std::size_t,std::vector<std::size_t>,decltype(lower_priority)> heap(lower_priority);
#endif
    std::vector<std::deque<std::size_t>> columns(bucket?tiles_:0);
    std::vector<std::uint64_t> nonempty(bucket?(tiles_+63)/64:0,0);
    std::deque<std::size_t> factors;
    std::size_t ready_count=0,peak=0,active=0;std::uint64_t completed=0;
    bool failed=false;std::exception_ptr error;
    auto id=[](std::size_t row,std::size_t col){return row*(row+1)/2+col;};
    auto push=[&](std::size_t index,bool after_update) {
      auto& task=tasks[index];task.pending=Queued;
      if(!bucket) {
#ifdef CHOL_PACKED_READY_KEYS
        heap.push(ready_key(index));
#else
        heap.push(index);
#endif
      }
      else if(task.kind==Kind::Factor)factors.push_back(index);
      else {
        auto& queue=columns[task.col];
        if((task.kind==Kind::Update&&task.row==task.col)||(task.kind==Kind::Solve&&after_update))queue.push_front(index);
        else queue.push_back(index);
        nonempty[task.col/64]|=std::uint64_t(1)<<(task.col%64);
      }
      peak=std::max(peak,++ready_count);
    };
    auto ready_if=[&](std::size_t index,bool after_update=false) {
      auto& task=tasks[index];
#ifdef CHOL_LAZY_CACHED_WAIT
      if(task.pending>=Queued)return;
#else
      if(task.pending!=Blocked)return;
#endif
      const std::size_t row=task.row,col=task.col,k=task.panel;
#ifdef CHOL_LAZY_CACHED_WAIT
      std::uint8_t waiting=0;
      if(k<col) {
        waiting=completed_panel[row]<static_cast<int>(k);
        if(row!=col)waiting+=completed_panel[col]<static_cast<int>(k);
        task.kind=Kind::Update;
      } else {
        if(k!=col)throw std::runtime_error("lazy tile panel exceeds target column");
        if(row==col)task.kind=Kind::Factor;
        else {waiting=completed_panel[col]<static_cast<int>(col);task.kind=Kind::Solve;}
      }
      task.pending=waiting;if(waiting)return;
#else
      if(k<col) {
        if(tasks[id(row,k)].pending!=Done||tasks[id(col,k)].pending!=Done)return;
        task.kind=Kind::Update;
      } else {
        if(k!=col)throw std::runtime_error("lazy tile panel exceeds target column");
        if(row==col)task.kind=Kind::Factor;
        else {if(tasks[id(col,col)].pending!=Done)return;task.kind=Kind::Solve;}
      }
#endif
      push(index,after_update);
    };
    auto factor_retired=[&](std::size_t index) {
#ifdef CHOL_LAZY_CACHED_WAIT
      auto& task=tasks[index];if(task.pending>=Queued)return;
      if(!task.pending)throw std::runtime_error("duplicate lazy factor notification");
      if(--task.pending==0)push(index,false);
#else
      ready_if(index);
#endif
    };
    auto pop=[&] {
      std::size_t index;
      if(!bucket){
#ifdef CHOL_PACKED_READY_KEYS
        index=static_cast<std::uint32_t>(heap.top());
#else
        index=heap.top();
#endif
        heap.pop();
      }
      else if(!factors.empty()){index=factors.front();factors.pop_front();}
      else {
        std::size_t word=0;while(word<nonempty.size()&&!nonempty[word])++word;
        if(word==nonempty.size())throw std::runtime_error("lazy ready bucket mask inconsistent");
        const auto col=word*64+std::countr_zero(nonempty[word]);auto& queue=columns[col];index=queue.front();queue.pop_front();
        if(queue.empty())nonempty[col/64]&=~(std::uint64_t(1)<<(col%64));
      }
      --ready_count;++active;
      if(tasks[index].pending!=Queued)throw std::runtime_error("lazy tile queued twice");
      tasks[index].pending=Running;return index;
    };
    ready_if(id(0,0));
    std::vector<std::jthread> workers;
    auto work=[&] {
      std::vector<double> scratch;
      for(;;) {
        std::unique_lock lock(mutex);
        try {
          condition.wait(lock,[&]{return failed||completed==logical_tasks_||ready_count;});
          if(failed||completed==logical_tasks_)return;
          const auto index=pop();const auto task=tasks[index];lock.unlock();execute_task(task,scratch);lock.lock();
          if(tasks[index].pending!=Running||tasks[index].panel!=task.panel)throw std::runtime_error("lazy tile ownership changed while running");
          --active;++completed;const auto before=ready_count;
          if(task.kind==Kind::Update) {
            ++tasks[index].panel;tasks[index].pending=Blocked;ready_if(index,true);
          } else {
            tasks[index].pending=Done;const std::size_t row=task.row,k=task.panel;
#ifdef CHOL_LAZY_CACHED_WAIT
            if(completed_panel[row]+1!=static_cast<int>(k))throw std::runtime_error("lazy factor row completed out of order");
            completed_panel[row]=static_cast<std::int16_t>(k);
#endif
            if(task.kind==Kind::Factor) {
              for(std::size_t m=k+1;m<tiles_;++m)if(tasks[id(m,k)].panel==k)factor_retired(id(m,k));
            } else {
              for(std::size_t col=k+1;col<=row;++col)if(tasks[id(row,col)].panel==k)factor_retired(id(row,col));
              for(std::size_t m=row+1;m<tiles_;++m)if(tasks[id(m,row)].panel==k)factor_retired(id(m,row));
            }
          }
          if(!ready_count&&!active&&completed!=logical_tasks_)throw std::runtime_error("lazy tile graph stalled before completion");
          [[maybe_unused]]const auto released=ready_count-before;[[maybe_unused]]const bool finished=completed==logical_tasks_;
#ifdef CHOL_BOUNDED_NOTIFY
          const auto wakes=std::min(released,std::size_t(threads>1?threads-1:0));lock.unlock();
          if(finished)condition.notify_all();else for(std::size_t wake=0;wake<wakes;++wake)condition.notify_one();
#elif defined(CHOL_UNLOCK_NOTIFY)
          lock.unlock();if(finished||released>1)condition.notify_all();else if(released)condition.notify_one();
#elif defined(CHOL_SELECTIVE_NOTIFY)
          if(finished||released>1)condition.notify_all();else if(released)condition.notify_one();
#else
          condition.notify_all();
#endif
        } catch(...) {
          if(!lock.owns_lock())lock.lock();
          if(!failed)error=std::current_exception();
          failed=true;condition.notify_all();return;
        }
      }
    };
    if(threads<=1)work();
#ifdef CHOL_REUSE_WORKERS
    else if(context)context->run_workers(threads,std::ref(work));
#endif
    else {
      workers.reserve(threads);for(unsigned i=0;i<threads;++i)workers.emplace_back(work);workers.clear();
    }
    if(error)std::rethrow_exception(error);
    if(completed!=logical_tasks_)throw std::runtime_error("lazy tile graph missed logical tasks");
    for(const auto& task:tasks)if(task.pending!=Done)throw std::runtime_error("lazy tile factor state unfinished");
    if(queue_peak)*queue_peak=peak;
  }
#endif
  void run(unsigned threads,bool bucket,std::uint64_t* queue_peak,[[maybe_unused]] ExecutionContext* context) {
#ifdef CHOL_SERIAL_TILE_WALK
    if(threads<=1) {
      // Every factor in columns <col is complete. Each target sees panels in
      // ascending order, then its P/T; this is a closed topological traversal.
      // It matches heap's column/panel/row order without locks or ready states.
      std::vector<double> scratch;std::uint64_t completed=0;
      auto execute=[&](Kind kind,std::size_t k,std::size_t row,std::size_t col) {
        execute_task({static_cast<std::uint16_t>(k),static_cast<std::uint16_t>(row),static_cast<std::uint16_t>(col),kind,0},scratch);++completed;
      };
      for(std::size_t col=0;col<tiles_;++col) {
        for(std::size_t k=0;k<col;++k)for(std::size_t row=col;row<tiles_;++row)execute(Kind::Update,k,row,col);
        execute(Kind::Factor,col,col,col);
        for(std::size_t row=col+1;row<tiles_;++row)execute(Kind::Solve,col,row,col);
      }
      if(completed!=logical_tasks_)throw std::runtime_error("serial tile walk missed logical tasks");
      if(queue_peak)*queue_peak=0;
      return;
    }
#endif
#ifdef CHOL_LAZY_TILE_GRAPH
    run_lazy(threads,bucket,queue_peak,context);return;
#endif
    std::mutex mutex;
    std::condition_variable condition;
    // A factor/solve closer to the diagonal is on the critical path. Group by
    // target column, then panel: next panels can progress before far updates.
#ifdef CHOL_PACKED_READY_KEYS
    auto ready_key=[&](std::size_t index) {
      const auto& task=tasks[index];
      return (std::uint64_t(task.col)<<48)|(std::uint64_t(task.panel)<<32)|std::uint64_t(index);
    };
    std::priority_queue<std::uint64_t,std::vector<std::uint64_t>,std::greater<std::uint64_t>> heap;
#else
    auto lower_priority=[&](std::size_t a,std::size_t b) {
      const auto& x=tasks[a]; const auto& y=tasks[b];
      const auto px=std::pair{x.col,x.panel},py=std::pair{y.col,y.panel};
      return px!=py?px>py:a>b;
    };
    std::priority_queue<std::size_t,std::vector<std::size_t>,decltype(lower_priority)> heap(lower_priority);
#endif
    std::vector<std::deque<std::size_t>> columns(bucket?tiles_:0);
    std::vector<std::uint64_t> nonempty(bucket?(tiles_+63)/64:0,0);
    std::deque<std::size_t> factors;
    std::size_t ready_count=0,peak=0;
    auto push=[&](std::size_t index,bool solve_after_update=false) {
      if(!bucket) {
#ifdef CHOL_PACKED_READY_KEYS
        heap.push(ready_key(index));
#else
        heap.push(index);
#endif
      }
      else {
        const auto& task=tasks[index];
        if(task.kind==Kind::Factor)factors.push_back(index);
        else {
          auto& column=columns[task.col];
          if((task.kind==Kind::Update&&task.row==task.col)||(task.kind==Kind::Solve&&solve_after_update))column.push_front(index);
          else column.push_back(index);
          nonempty[task.col/64]|=std::uint64_t(1)<<(task.col%64);
        }
      }
      peak=std::max(peak,++ready_count);
    };
    auto pop=[&]() {
      std::size_t index;
      if(!bucket){
#ifdef CHOL_PACKED_READY_KEYS
        index=static_cast<std::uint32_t>(heap.top());
#else
        index=heap.top();
#endif
        heap.pop();
      }
      else if(!factors.empty()){index=factors.front();factors.pop_front();}
      else {
        std::size_t word=0;while(word<nonempty.size()&&!nonempty[word])++word;
        if(word==nonempty.size())throw std::runtime_error("ready bucket mask inconsistent");
        const auto col=word*64+std::countr_zero(nonempty[word]);auto& column=columns[col];
        index=column.front();column.pop_front();
        if(column.empty())nonempty[word]&=~(std::uint64_t(1)<<(col%64));
      }
      --ready_count;return index;
    };
    for(std::size_t i=0;i<tasks.size();++i) if(tasks[i].pending==0)push(i);
    std::size_t completed=0;
    bool failed=false;
    std::exception_ptr error;
    std::vector<std::jthread> workers;
    auto work=[&] {
      std::vector<double> scratch; // Lazy, worker-local P/T factor staging.
      for(;;) {
        std::unique_lock lock(mutex);
        try {
          condition.wait(lock,[&]{return failed||completed==tasks.size()||ready_count;});
          if(failed||completed==tasks.size()) return;
          const auto index=pop();lock.unlock();execute_task(tasks[index],scratch);
          lock.lock();++completed;
          [[maybe_unused]]std::size_t released=0;
          users(index,[&](std::size_t user) {
            if(tasks[user].pending==0)throw std::runtime_error("duplicate tile retirement");
            if(--tasks[user].pending==0){push(user,tasks[index].kind==Kind::Update);++released;}
          });
#ifdef CHOL_BOUNDED_NOTIFY
          // Publish predicates under the same mutex used by wait; notification
          // needs no lock. The current worker also resumes, so at most threads-1
          // sleepers can use the newly released tasks. Completion wakes all.
          const bool finished=completed==tasks.size();
          const auto wake_count=std::min(released,std::size_t(threads>1?threads-1:0));
          lock.unlock();
          if(finished)condition.notify_all();
          else for(std::size_t wake=0;wake<wake_count;++wake)condition.notify_one();
#elif defined(CHOL_UNLOCK_NOTIFY)
          const bool finished=completed==tasks.size();
          lock.unlock();
          if(finished||released>1)condition.notify_all();
          else if(released==1)condition.notify_one();
#elif defined(CHOL_SELECTIVE_NOTIFY)
          if(completed==tasks.size()||released>1)condition.notify_all();
          else if(released==1)condition.notify_one();
#else
          condition.notify_all();
#endif
        } catch(...) {
          if(!lock.owns_lock())lock.lock();
          if(!failed)error=std::current_exception();
          failed=true;condition.notify_all();return;
        }
      }
    };
    if(threads<=1) work();
#ifdef CHOL_REUSE_WORKERS
    else if(context)context->run_workers(threads,std::ref(work));
#endif
    else {
      workers.reserve(threads);
      for(unsigned i=0;i<threads;++i)workers.emplace_back(work);
      workers.clear();
    }
    if(error)std::rethrow_exception(error);
    if(completed!=tasks.size())throw std::runtime_error("tile graph failed to retire all tasks");
    if(queue_peak)*queue_peak=peak;
  }
};
}

Matrix tiled_cholesky(const Matrix& input,Options options,bool fused,Matrix* owned_input) {
  return tiled_cholesky(input,std::move(options),fused,owned_input,nullptr);
}
Matrix tiled_cholesky(const Matrix& input,Options options,bool fused,Matrix* owned_input,const NativeInputScan* scan) {
  bool recycle=false;
#ifdef CHOL_REUSE_INPUT_BUFFER
  // Reusing A is valid only for the column workspace: all accumulators/factors
  // are packed, so P/T/U never access output. Classify structure before output
  // allocation: proven bands may factor in the owned buffer; other inputs
  // retain empty output until every P/T/U input read completes.
  recycle=owned_input!=nullptr;
#else
  (void)owned_input;
#endif
  Matrix output{input.n,{}};
  if(!recycle) {
    output.values.assign(input.values.size(),0.0);
  }
  if(try_structured_factor(input,output,options,fused,scan,owned_input))return output;
  const auto graph_start=Clock::now();
  bool simd=false;
  bool avx512=false;
#ifdef CHOL_HAVE_X86_SIMD
  simd=options.simd!="portable"&&__builtin_cpu_supports("avx2")&&__builtin_cpu_supports("fma");
#endif
#ifdef CHOL_HAVE_AVX512_KERNEL
  avx512=options.simd=="avx512"&&usable_avx512(detect_simd_capabilities());
#endif
  // Local milestone evidence favors B32 for smaller matrices and B64 once
  // factor reuse dominates. This changes task geometry, never result semantics.
  const auto workers=options.parallel?std::max(1u,options.threads):1u;
  const auto small_limit=workers==1?1536u:1024u;
  const auto tile_size=options.tile_size?options.tile_size:(input.n<=small_limit?32u:(workers>=8&&input.n>=4096?96u:64u));
  [[maybe_unused]]bool serial_walk=false;
#ifdef CHOL_SERIAL_TILE_WALK
  serial_walk=workers==1;
#endif
  double* leased_factors=nullptr;
#ifdef CHOL_CACHE_NATIVE_WORKSPACE
  // Declare lease before program so every return/throw destroys the program
  // before unlocking shared capacity. Worker-context locking alone is too late.
  std::optional<NativeWorkspace::Lease> workspace_lease;
  if(options.native_workspace) {
    const auto tiles=(std::size_t(input.n)+tile_size-1)/tile_size;
    if(std::uint64_t(tiles)*(tiles+1)*(tiles+2)/6>16000000)
      throw std::runtime_error("tile graph exceeds 16 million tasks; increase --tile-size");
    const auto start=Clock::now();
    workspace_lease.emplace(options.native_workspace->acquire(tiles*(tiles+1)/2*tile_size*tile_size));
    leased_factors=workspace_lease->data();
    if(options.metrics) {
      options.metrics->workspace_acquire_ms=elapsed(start);
      options.metrics->workspace_capacity_bytes=workspace_lease->capacity_elements()*sizeof(double);
      options.metrics->workspace_reused=workspace_lease->reused();
    }
  }
#endif
  TileProgram program(input,output,tile_size,fused,simd,serial_walk,avx512,leased_factors);
  if(options.metrics) {
    options.metrics->engine="tiled";options.metrics->tasks=program.logical_tasks();
    options.metrics->resident_task_states=program.tasks.size();
    options.metrics->packed_bytes=program.bytes();options.metrics->graph_ms=elapsed(graph_start);
    options.metrics->task_metadata_bytes=program.graph_bytes();
    options.metrics->vector_kernel=avx512?(fused?"avx512_explicit_fma":"avx512_separate_mul_add"):(simd?(fused?"avx2_explicit_fma":"avx2_separate_mul_add"):"portable_ordered_lanes");
    options.metrics->ready_queue=serial_walk?"closed_serial":options.ready_queue;
    options.metrics->effective_tile_size=tile_size;
    options.metrics->vector_rows=simd?(CHOL_AVX_ROW_GROUP?CHOL_AVX_ROW_GROUP:(input.n>=2048?4u:2u)):0u;
    if(avx512)options.metrics->vector_rows=4;
#ifdef CHOL_COLUMN_WORKSPACE
#ifdef CHOL_ROW_TILE_WORKSPACE
    options.metrics->workspace_layout="tile_row_accumulator_column_factor";
#else
    options.metrics->workspace_layout="tile_column_lower_unified";
    options.metrics->vector_rows=simd?8u:0u;
#endif
#else
    options.metrics->workspace_layout="row_major_plus_packed_factors";
#endif
  }
  const auto compute_start=Clock::now();
  if(options.metrics)options.metrics->worker_threads=workers;
  program.run(workers,options.ready_queue=="bucket",options.metrics?&options.metrics->ready_peak:nullptr,options.execution_context);
  if(options.metrics)options.metrics->kernel_ms=elapsed(compute_start);
  const auto export_start=Clock::now();
  if(recycle) {
    // run completes every worker job and checks completion before this point. The only
    // later operation, export_output, reads packed factors and cached n_/b_;
    // it never reads input_. Lower entries will all be overwritten; upper
    // entries must be explicit +0, independent of their original A bit values.
    const auto recycle_start=Clock::now();
    output.values.swap(owned_input->values);
    for(std::size_t row=0;row<output.n;++row)
      std::fill(output.values.begin()+row*output.n+row+1,
                output.values.begin()+(row+1)*output.n,0.0);
    if(options.metrics) {
      options.metrics->input_buffer_reused=true;
      options.metrics->input_recycle_ms=elapsed(recycle_start);
    }
  }
  program.export_output(workers);
  if(options.metrics)options.metrics->export_ms=elapsed(export_start);
  return output;
}
}
