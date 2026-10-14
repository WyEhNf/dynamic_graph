"""Verify an algebraic optimization preserves emitted plans, not only T/peak."""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument("--before",default="batch21");p.add_argument("--after",default="batch22");args=p.parse_args()
    checked=0;details=[]
    for before in Path("reports").glob(f"*-{args.before}.json"):
        name=before.name[:-len(args.before+".json")]
        if name.startswith("paired-") or name.startswith("certificate-audit"):continue
        after=Path("reports")/(name+args.after+".json")
        if not after.exists():continue
        old=json.loads(before.read_text());new=json.loads(after.read_text())
        if "cases" not in old or "cases" not in new:continue
        rows={x["name"]:x for x in new["cases"]}
        for x in old["cases"]:
            y=rows[x["name"]]
            for key in ["plan","valid","pass","T","peak_memory"]:assert x[key]==y[key],(x["name"],key)
            checked+=1
        details.append(dict(before=str(before),after=str(after),records=len(old["cases"])))
    assert checked>=1015,checked
    Path(f"reports/plan-identity-{args.after}.json").write_text(json.dumps(dict(checked=checked,identical=True,scope="emitted plans and validity/T/peak; complements internal 288 old-recurrence assignment tests",reports=details),indent=2))
    print(f"{checked} emitted plans/validity/T/peak identical")


if __name__=="__main__":main()
