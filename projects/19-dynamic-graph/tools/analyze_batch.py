"""Emit multiple functions/Metadata encodings from one explicit source snapshot.

Each job is {"function": "name", "output": "path.meta", "options": {...}}.
Relative output paths resolve beside the jobs JSON. Audit IR remains enabled
unless a job explicitly sets options.emit_ir=false.
"""
import argparse
import json
from pathlib import Path
import subprocess
from analyze_source import PreparedSource


def analyze_batch(source,jobs,clang='clang',base_directory=None,protected_paths=(),report_path=None):
    if not isinstance(jobs,list) or not 1<=len(jobs)<=1000:raise ValueError('jobs must be a nonempty list of at most 1000 records')
    base=Path.cwd() if base_directory is None else Path(base_directory)
    protected={Path(path).resolve() for path in protected_paths}
    protected.add(Path(source).resolve())
    report_target=None if report_path is None else Path(report_path).resolve()
    allowed={'symbolic_format','include_provenance','compact_bytecode','metadata_schema','smallest_metadata','compress_metadata','metadata_newlines','emit_ir'}
    destinations=set();normalized=[]
    for job in jobs:
        if not isinstance(job,dict) or set(job)-{'function','output','options'} or not isinstance(job.get('function'),str) or not isinstance(job.get('output'),str):raise ValueError('job requires function and output strings and optional options object')
        options=job.get('options',{})
        if not isinstance(options,dict) or set(options)-allowed:raise ValueError('unsupported batch analysis option')
        output=(base/Path(job['output'])).resolve()
        artifacts=[output,output.with_suffix('.analysis.json')]
        if options.get('emit_ir',True):artifacts.append(output.with_suffix('.ll'))
        if len(set(artifacts))!=len(artifacts) or any(path in destinations for path in artifacts):raise ValueError('batch output artifacts must be distinct')
        destinations.update(artifacts);normalized.append((job['function'],output,options))
    if destinations&protected:raise ValueError('batch output would overwrite a protected input')
    if report_target is not None and report_target in destinations|protected:raise ValueError('batch report would overwrite an input or output artifact')
    prepared=PreparedSource(source,clang)
    if any(path in prepared.dependencies for path in destinations):raise ValueError('batch output would overwrite a source dependency')
    if report_target in prepared.dependencies:raise ValueError('batch report would overwrite a source dependency')
    reports=[prepared.emit(output,function,**options) for function,output,options in normalized]
    return {'source':str(prepared.source),'source_sha256':prepared.source_sha256,'clang':prepared.clang_version,
            'dependencies':{str(path):digest for path,digest in prepared.dependencies.items()},
            'dependency_invocations':1,'ast_invocations':1,'ir_invocations':int(prepared._ir is not None),'jobs':reports}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--jobs',required=True,type=Path)
    parser.add_argument('--clang',default='clang')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    try:
        report=analyze_batch(args.source,json.loads(args.jobs.read_text(encoding='utf-8')),args.clang,args.jobs.resolve().parent,protected_paths=(args.jobs,),report_path=args.report)
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False))
    except (ValueError,subprocess.CalledProcessError) as error:raise SystemExit(str(error))


if __name__=='__main__':main()
