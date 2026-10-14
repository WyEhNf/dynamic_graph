"""Counted-while proof coverage, unsafe steps and real changed-source behavior."""
from pathlib import Path
import argparse,hashlib,json,time
from datetime import datetime,timezone
from analyze_source import analyze
from evaluate_source import evaluate

LEFT='''#include <math.h>
int factor(const double*a,double*l,int n){
int i=0;while(i<n){
  int j=0;while(j<=i){
    double s=0;int k=0;while(k<j){s+=l[i*n+k]*l[j*n+k];k=k+1;}
    if(i==j)l[i*n+j]=sqrt(a[i*n+i]-s);else l[i*n+j]=(a[i*n+j]-s)/l[j*n+j];
    j+=1;
  }i++;
}return 0;}
'''
RIGHT='''#include <math.h>
static double division(double x,double y){return x/y;}
static double madd(double x,double y,double z){return x*y+z;}
void factor(const double*a,double*l,int n){
int i=0;while(i<=n-1){
  l[i*n+i]=sqrt(a[i*n+i]-l[i*n+i]);
  int j=i+1;while(j<n){
    l[j*n+i]=division(a[j*n+i]-l[j*n+i],l[i*n+i]);
    int k=i+1;while(k<j+1){l[j*n+k]=madd(l[j*n+i],l[k*n+i],l[j*n+k]);++k;}
    j=j+1;
  }i+=1;
}}
'''
BLOCKED='''#include <math.h>
static double division(double x,double y){return x/y;}
static double madd(double x,double y,double z){return x*y+z;}
int factor(const double*a,double*l,int n,int block){
int panel=0;while(panel<n){
  int panel_end=panel+block<n?panel+block:n;
  int i=panel;while(i<panel_end){
    l[i*n+i]=sqrt(a[i*n+i]-l[i*n+i]);
    int row_tile=i+1;while(row_tile<n){
      int row_end=row_tile+block<n?row_tile+block:n;
      int j=row_tile;while(j<row_end){
        l[j*n+i]=division(a[j*n+i]-l[j*n+i],l[i*n+i]);
        int col_tile=i+1;while(col_tile<=j){
          int col_end=col_tile+block<j+1?col_tile+block:j+1;
          int k=col_tile;while(k<col_end){l[j*n+k]=madd(l[j*n+i],l[k*n+i],l[j*n+k]);k++;}
          col_tile+=block;
        }j++;
      }row_tile+=block;
    }++i;
  }panel+=block;
}return 0;}
'''

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path,default=Path('artifacts/baseline-shape-runtime.exe'));parser.add_argument('--gcc',default='gcc');parser.add_argument('--clang',default='clang');parser.add_argument('--output-dir',type=Path,default=Path('artifacts/while-proof-milestone'));args=parser.parse_args();project=Path(__file__).resolve().parent.parent;root=args.output_dir.resolve();root.mkdir(exist_ok=True,parents=True);runtime=args.runtime.resolve();started=time.perf_counter()
    report={'passed':False,'runtime_sha256':hashlib.sha256(runtime.read_bytes()).hexdigest(),'checked_at_utc':datetime.now(timezone.utc).isoformat(),'cases':[],'contract':'bytecode retains actual while control flow; native proof checks normalized initializer/domain/step plus complete typed operations; all output bytes match independent original C'}
    sources={'left':LEFT,'right':RIGHT,'right-fma':RIGHT.replace('return x*y+z;','return fma(x,y,z);'),'changed-step':RIGHT.replace('j=j+1','j=j+2'),'changed-operation':RIGHT.replace('return x*y+z;','return x*y*0.5+z;'),'blocked-while':BLOCKED}
    for label,text in sources.items():
        source=root/f'{label}.c';source.write_text(text);case=evaluate(source,'factor',runtime,root/label,[3,7,17,33,65,129],args.clang,args.gcc,(1,7,32,100)if label=='blocked-while'else(7,),(1,4),True,True)
        expected='none' if label.startswith('changed')else 'scalar_cholesky_column_dag' if label=='left'else 'rightlooking_cholesky_column_dag_fma' if label=='right-fma'else 'rightlooking_cholesky_column_dag'
        if case['optimized']!=expected:raise AssertionError(f'incorrect proof for {label}: {case["optimized"]}')
        analysis=json.loads((root/label/'program.analysis.json').read_text())
        if not any(loop['kind']=='while'for loop in analysis['loops']):raise AssertionError('actual while AST replaced in emitted audit')
        report['cases'].append({'case':label,**case});print(f'PASS counted while {label}: {case["optimized"]}',flush=True)
    report['passed']=True;report['elapsed_seconds']=time.perf_counter()-started;(root/'while-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'comparisons':sum(len(c['runs'])for c in report['cases']),'report':str(root/'while-report.json')}),flush=True)

if __name__=='__main__':main()
