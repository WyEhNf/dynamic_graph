"""Verify the promoted bytes and all terminal gates, then save one audit manifest."""
from pathlib import Path
import datetime,hashlib,json
ROOT=Path(__file__).resolve().parents[1];BASE=Path('G:/Hackathon-stage2-artifacts/project27/20261013');OUT=BASE/'r64'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    api=json.loads((BASE/'r63/api/report.json').read_text());actual=json.loads((OUT/'default-api/report.json').read_text())
    regression=json.loads((OUT/'regression/report.json').read_text());ctest=json.loads((OUT/'ctest-final15.json').read_text())
    audit=json.loads((BASE/'r63/bigint-audit.json').read_text());disabled=json.loads((OUT/'recovery-disabled-report.json').read_text())
    assert api['complete'] and actual['passed'] and regression['complete'] and regression['records']==1099
    assert ctest['passed'] and ctest['tests']==15 and audit['passed'] and audit['recovered']==22 and disabled['passed']
    assert sha(ROOT/'solution/solution.cpp')==sha(ROOT/'research/batch64/solution.cpp')==actual['actual_default_source_sha256']==regression['source_sha256']
    assert sha(ROOT/'build/aicore_bench.exe')==actual['actual_default_exe_sha256']
    paths=[ROOT/'solution/solution.cpp',ROOT/'build/aicore_bench.exe',ROOT/'CMakeLists.txt',ROOT/'tests/test_macro_recovery_budget.cpp',ROOT/'research/batch52/remaining63-input-only.json',
           ROOT/'data/hard-corpus-resumed.json',ROOT/'data/projection-retention-heldout-batch45.json',
           BASE/'r63/api/report.json',OUT/'default-api/report.json',OUT/'default-api/hard202.json',OUT/'default-api/held48.json',
           OUT/'default-api/hard202-failures.json',OUT/'default-api/held48-failures.json',OUT/'regression/report.json',OUT/'ctest-final15.json',OUT/'ctest-final15.log',
           OUT/'validation-receipt.json',OUT/'budget.log',OUT/'recovery-disabled-report.json',OUT/'recovery-disabled-held48.json',
           BASE/'r63/bigint-audit.json',BASE/'r63/remaining63-helper.json',BASE/'r63/controls/controls-report.json',OUT/'promotion.json',
           OUT/'previous-default/solution.cpp',OUT/'previous-default/aicore_bench.exe',Path(__file__)]
    report={'status':'promoted_and_verified','candidate':'R64','timestamp':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
            'default_source':str(ROOT/'solution/solution.cpp'),'default_exe':str(ROOT/'build/aicore_bench.exe'),
            'change':'Original-DAG workspace-completion beam; original direct users and BEGIN lifetime replay; in-place reversible candidates; full done-set dedup; bounded retained-state heap; failed-legacy-only fallback.',
            'hard202':{'before':145,'after':161,'remaining':41},'retention48':{'before':42,'after':48,'remaining':0},
            'previous_unresolved':63,'recovered':22,'remaining':41,'regression_records':1099,'regression_exact_plans':True,'old202_plus48_success_plans_identical':187,
            'ctest':{'passed':15,'total':15},'controls':{'small_bigint_subset_dp':420,'candidate_returned':17,'no_small_graph_completeness_claim':True,'work_limits':10,'disabled_legacy_replay_records':48},
            'budget':{'default':160000000,'primary':{'width':32,'work':128000000,'rank':'live,peak,area','max_nodes':4096},
                      'fallbacks':[{'width':32,'work':16000000,'rank':'peak,live,area','max_nodes':512},{'width':32,'work':16000000,'rank':'area,live,peak','max_nodes':512}],
                      'cmake_or_preprocessor_option':'AICORE_MACRO_RECOVERY_WORK_LIMIT','zero_disables':True,'meaning':'logical search work, not milliseconds or proof of global infeasibility'},
            'all_failure_costs_included':True,'cost_measurement':{'scope':'one shared-load functional before/after comparison, both GCC O2; no stable speed claim','hard202':api['results']['hard202']['costs'],'retention48':api['results']['held48']['costs'],
                                                           'helper63_cpu_us':audit['cpu_us'],'helper63_wall_us':audit['wall_us'],'helper63_max_wall_us':audit['max_wall_us']},
            'build':{'compiler':'MinGW GCC 15.2.0','standard':'C++17','default':'CMake Release -O3 -DNDEBUG; standalone standard library implementation','comparison':'both -O2'},
            'limits':['41 known-feasible records still unresolved','beam width and fixed greedy closure execution are heuristic','all benchmark sets are development data; no official hidden score claim'],
            'sha256':{str(p.resolve()):sha(p) for p in paths}}
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/macro-recovery-r64-2026-10-13.json').write_text(json.dumps(report,indent=2))
    readme=ROOT/'README.md';text=readme.read_text(encoding="utf-8");header='2026-10-13 R64：默认新增仅在旧路线失败后触发的原图闭包beam恢复。原202困难 **145→161**、新48 **42→48**，原63未解恢复22、剩41；1099历史记录及187条共同成功计划逐项相同，15/15 CTest、420大整数DP控制、10档预算和预算0关闭回放通过。原202全流程CPU单轮33.41→49.13秒，含全部失败；不称加速。可通过 `-DAICORE_MACRO_RECOVERY_WORK_LIMIT=0` 关闭，默认逻辑预算160M。详见 [完整可核验报告](reports/macro-recovery-r64-2026-10-13.json)。\n\n'
    if header not in text:readme.write_text(text.replace('\n\n','\n\n'+header,1),encoding="utf-8")
    validation=ROOT/'docs/validation.json';doc=json.loads(validation.read_text(encoding="utf-8"));doc['latest_optimization_2026_10_13']={'candidate':'R64','default_source_sha256':sha(ROOT/'solution/solution.cpp'),'report':'reports/macro-recovery-r64-2026-10-13.json','hard202':161,'retention48':48,'known_feasible_unresolved':41,'regression_exact_plans':1099,'ctest':15};validation.write_text(json.dumps(doc,indent=2),encoding="utf-8")
    print(json.dumps({'manifest':str(OUT/'manifest.json'),'sha256':sha(OUT/'manifest.json'),'recovered':22,'remaining':41,'verified':True}))


if __name__=='__main__':main()
