"""Check certificates against external exact or independently analytic optima.

No solver or private bound implementation is called. Local exhaustive oracle
values were generated before certificates existed, by a separate executable.
"""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--label",default="batch21")
    p.add_argument("--source",default="solution/solution.cpp")
    args=p.parse_args();rows=[];certified=0
    suites=[("oracle4","parallel-oracle"),("oracle4-holdout","parallel-oracle-holdout"),("oracle5","parallel-oracle5"),("oracle5-holdout","parallel-oracle5-holdout"),("oracle6","parallel-oracle6"),("oracle6-holdout","parallel-oracle6-holdout"),("certificate-controls","certificate-controls")]
    for report,source in suites:
        path=Path(f"data/{source}.json");cases={x["name"]:x for x in json.loads(path.read_text())["cases"]}
        results=json.loads(Path(f"reports/{report}-{args.label}.json").read_text())
        for r in results["cases"]:
            meta=cases[r["name"]]["generation"]
            T=meta.get("oracle_T",meta.get("analytic_T"));P=meta.get("oracle_peak",meta.get("analytic_peak"))
            assert r["pass"] and r["models_equal"] and r["time_lower_bound"]<=T,r["name"]
            # The strengthened peak bound is conditional on attaining the time
            # bound. Only compare it with optimal peak when that condition holds.
            if r["time_lower_bound"]==T:assert r["memory_lower_bound"]<=P,r["name"]
            if r["optimal_certificate"]:
                assert (r["T"],r["peak_memory"])==(T,P),r["name"]
                certified+=1
            if "analytic_T" in meta:assert (r["T"],r["peak_memory"])==(T,P),r["name"]
            rows.append(dict(name=r["name"],n=r["n"],certificate=r["optimal_certificate"],time_bound=r["time_lower_bound"],memory_bound=r["memory_lower_bound"],optimal_T=T,optimal_peak=P))
    result=dict(checked=len(rows),certified=certified,oracle_scope="complete <=6 nodes/<=2 flows/explicit direct sync; analytic total chains and two-task controls",source_sha256=hashlib.sha256(Path(args.source).read_bytes()).hexdigest(),rows=rows)
    Path(f"reports/certificate-audit-{args.label}.json").write_text(json.dumps(result,indent=2))
    print(f"{len(rows)} external optimum checks passed, {certified} certificates")


if __name__=="__main__":main()
