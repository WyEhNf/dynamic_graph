"""External-source adapter: C source -> metadata -> binary runtime -> C oracle.

The oracle is compiled independently from actual C source. The source AST VM or
optimized kernels are never used to generate reference bytes. Strict IEEE bytes
are the default and cannot silently degrade to a tolerance comparison.
"""
from __future__ import annotations
import argparse
from array import array
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import time
from analyze_source import analyze


def make_input(path, sizes, diagonal=False, signed_zero=False):
    with Path(path).open("wb") as stream:
        stream.write(struct.pack("<I", len(sizes)))
        for n in sizes:
            stream.write(struct.pack("<I", n))
            for i in range(n):
                if diagonal:
                    row = array("d", [0.0]) * n
                    row[i] = float(4 ** (i % 4))
                    if signed_zero and i: row[(i * 13) % i] = -0.0
                else:
                    row = array("d", (float(n + 2) if i == j else (((min(i,j)*1315423911) ^ (max(i,j)*2654435761) ^ 42) % 1001 - 500) / 32768.0 for j in range(n)))
                stream.write(row.tobytes())


def exact_compare(left, right):
    total = 0
    digest = hashlib.sha256()
    with Path(left).open("rb") as a, Path(right).open("rb") as b:
        while True:
            x, y = a.read(1024*1024), b.read(1024*1024)
            if x != y:
                first = next((i for i,(u,v) in enumerate(zip(x,y)) if u != v), min(len(x),len(y)))
                raise AssertionError(f"byte mismatch at offset {total+first}: {left} vs {right}")
            if not x: break
            total += len(x); digest.update(x)
    return {"byte_identical": True, "bytes": total, "sha256": digest.hexdigest()}


def compile_oracle(source, function, folder, gcc, block_argument=False):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    source_path = Path(source).resolve().as_posix().replace('"', '\\"')
    if not function.isidentifier(): raise ValueError("invalid C function identifier")
    call = f"{function}(a,l,(int)n" + (",block" if block_argument else "") + ");"
    harness = folder / "oracle.c"
    harness.write_text('''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
''' .replace("#include <stdlib.h>\n", "") + f'#include "{source_path}"\n' + '''
/* stdlib declarations avoid conflicting with the official image's div helper. */
extern void *calloc(size_t,size_t);
extern void free(void *);
extern int atoi(const char *);
int main(int argc, char **argv) {
  if(argc != 4) return 10;
  FILE *in=fopen(argv[1],"rb"), *out=fopen(argv[2],"wb");
  if(!in || !out) return 11;
  int block=atoi(argv[3]); uint32_t m;
  if(fread(&m,4,1,in)!=1 || fwrite(&m,4,1,out)!=1) return 12;
  for(uint32_t z=0;z<m;z++) {
    uint32_t n; if(fread(&n,4,1,in)!=1 || n<3 || n>10000) return 13;
    size_t count=(size_t)n*n;
    double *a=(double*)calloc(count,sizeof(double)), *l=(double*)calloc(count,sizeof(double));
    if(!a || !l || fread(a,sizeof(double),count,in)!=count) return 14;
    ''' + call + '''
    if(fwrite(&n,4,1,out)!=1 || fwrite(l,sizeof(double),count,out)!=count) return 15;
    free(a); free(l);
  }
  if(fgetc(in)!=EOF) return 16;
  fclose(in); if(fclose(out)) return 17; return 0;
}
''', encoding="utf-8")
    executable = folder / "oracle.exe"
    subprocess.run([gcc, "-std=c11", "-O2", "-fno-fast-math", "-ffp-contract=off", str(harness), "-o", str(executable)], capture_output=True, text=True, check=True)
    return executable


def run_runtime(runtime, metadata, input_path, output, scheduler="parallel", threads=4, block=32, engine="auto", step_limit=1000000000, tile_size=64, simd=None,ready_queue=None,structure=None,band_limit=None,probe_resources=False):
    output = Path(output); output.unlink(missing_ok=True)
    started = time.perf_counter()
    command=[str(Path(runtime).resolve()), "--metadata", str(Path(metadata).resolve()), "--input", str(Path(input_path).resolve()), "--output", str(output.resolve()), "--scheduler", scheduler, "--threads", str(threads), "--block-size", str(block), "--engine", engine, "--vm-step-limit", str(step_limit)]
    if engine=="tiled":command.extend(("--tile-size",str(tile_size)))
    if simd is not None:command.extend(("--simd",simd))
    if ready_queue is not None:command.extend(("--ready-queue",ready_queue))
    if structure is not None:command.extend(("--structure",structure))
    if band_limit is not None:command.extend(("--band-limit",str(band_limit)))
    resource_metrics={}
    if probe_resources:
        from windows_resource_probe import monitored_run
        run,resource_metrics=monitored_run(command)
    else:run = subprocess.run(command, capture_output=True, text=True, check=True)
    metrics = json.loads(run.stdout)
    metrics.update(resource_metrics)
    metrics.update({"wall_ms": (time.perf_counter()-started)*1000, "scheduler": scheduler, "threads": threads, "block_size": block, "engine": engine, "tile_size":tile_size,"tile_size_requested":tile_size if engine=='tiled'else None,"simd_requested":simd,"ready_queue_requested":ready_queue,"structure_requested":structure,"band_limit_requested":band_limit})
    return metrics


def evaluate(source, function, runtime, folder, sizes, clang="clang", gcc="gcc", blocks=(32,), threads=(1,4), include_vm=True, include_tiled=True):
    if not sizes or any(n < 3 or n > 10000 for n in sizes):
        raise ValueError("test sizes must be in [3,10000]")
    if not blocks or any(n < 1 or n > 10000 for n in blocks):
        raise ValueError("test block sizes must be in [1,10000]")
    if not threads or any(n < 1 or n > 256 for n in threads):
        raise ValueError("test thread counts must be in [1,256]")
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    metadata = folder / "program.meta"
    analysis = analyze(source, metadata, clang, function)
    input_path = folder / "input.bin"; make_input(input_path,sizes)
    block_argument = "block_slot=-1\n" not in metadata.read_text(encoding="utf-8")
    oracle = compile_oracle(source,function,folder,gcc,block_argument)
    records = []
    for block in blocks:
        reference = folder / f"oracle-{block}.bin"
        subprocess.run([str(oracle.resolve()),str(input_path.resolve()),str(reference.resolve()),str(block)], check=True)
        for count in threads:
            target = folder / f"runtime-{block}-{count}.bin"
            metrics = run_runtime(runtime,metadata,input_path,target,threads=count,block=block)
            metrics.update(exact_compare(reference,target)); records.append(metrics)
        if include_tiled:
            for tile in (7,32):
                for count in (1,4):
                    target=folder/f"tiled-{block}-{tile}-{count}.bin"
                    metrics=run_runtime(runtime,metadata,input_path,target,threads=count,block=block,engine="tiled",tile_size=tile)
                    metrics.update(exact_compare(reference,target));records.append(metrics)
        if include_vm:
            target = folder / f"vm-{block}.bin"
            metrics = run_runtime(runtime,metadata,input_path,target,threads=4,block=block,engine="vm")
            metrics.update(exact_compare(reference,target)); records.append(metrics)
    return {"source": str(Path(source).resolve()), "function": function, "sizes": sizes, "metadata_bytes": analysis["metadata_bytes"], "instructions": analysis["instructions"], "optimized": analysis["optimized"], "loops": len(analysis["loops"]), "accesses": len(analysis["accesses"]), "oracle": "independently compiled source; GCC -O2 -fno-fast-math -ffp-contract=off", "comparison": "strict bytes including all matrix/header bytes", "runs": records}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--function", required=True)
    parser.add_argument("--runtime", type=Path, default=Path("build/cholesky_runtime.exe"))
    parser.add_argument("--sizes", default="3,7,17,33,65")
    parser.add_argument("--blocks", default="1,7,32,100")
    parser.add_argument("--threads", default="1,2,4")
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--gcc", default="gcc")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/external-evaluation"))
    parser.add_argument("--skip-vm", action="store_true")
    args = parser.parse_args()
    report = evaluate(args.source,args.function,args.runtime,args.output_dir,[int(n) for n in args.sizes.split(',')],args.clang,args.gcc,[int(n) for n in args.blocks.split(',')],[int(n) for n in args.threads.split(',')],not args.skip_vm)
    (args.output_dir/"evaluation.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__ == "__main__": main()
