"""Portfolio optimizer retaining only independently verified candidates."""
from time import perf_counter
from collections import Counter
from math import isfinite

from .model import BudgetExceeded, InfeasibleSchedule, InvalidBlock, VerificationFailed, parse_block
from .bounds import forest_capacity_bound
from .spine_bounds import spine_capacity_bound
from .paired_bounds import paired_network_capacity_bound
from .sink_bounds import sink_spine_capacity_bound
from .rectangle_bounds import rectangle_capacity_bound
from .dot_prefix_bounds import shared_prefix_capacity_bound
from .branch_dp import schedule_branches
from .branch_copy import schedule_branch_copy
from .alias_schedule import schedule_aliases
from .local_order import improve_order
from .minor_bounds import contraction_bound,check_contraction_certificate
from .spine_copy_bound import spine_copy_bound,check_spine_copy_certificate
from .consumer_copy_bound import consumer_copy_bound,check_consumer_copy_certificate
from .pair_copy_bound import pair_copy_bound,check_pair_copy_certificate
from .identity_witness import check_identity_witness
from .terminal_pairs import recognize as recognize_terminal_pairs,schedule_terminal_pairs
from .reverse_pressure import schedule_reverse_pressure
from .root_spines import schedule_root_spines,recognize_root_spines
from .comb_forest import schedule_comb_forest,recognize_comb_forest
from .reduction_columns import schedule_reduction_columns,recognize_reduction_columns
from .root_phases import schedule_root_phases
from .scheduler import schedule
from .incremental import schedule_incremental, PreparedGraph
from .forest_linear import emit_forest,emit_single_source_chains,eligible as forest_eligible
from .search import search
from .verify import verify, VerificationContext


def verified(data, candidate, context=None):
    try:
        return context.check(candidate) if context is not None else verify(data, candidate)
    except InvalidBlock as exc:
        raise VerificationFailed(f"Candidate was rejected by independent verifier: {exc}") from exc


def original_candidate(block, remaining_ms):
    """A legal original ordering already attains the zero-insertion lower bound."""
    tick = perf_counter()
    deadline = tick + remaining_ms / 1000
    output = []
    for node in block.instructions:
        if node.index % 128 == 0 and perf_counter() >= deadline:
            raise BudgetExceeded("Original-order export budget exhausted")
        row = {"id": node.index, "op": node.op}
        if node.reg is not None:
            row["reg"] = node.reg
        tokens = [f"t#{node.index-source}" for source in node.args]
        if node.op == "COPY":
            row["source"] = tokens[0]
        elif tokens:
            row["inputs"] = tokens
        output.append(row)
    count = len(output)
    copies = sum(row["op"] == "COPY" for row in output)
    return {"block_id": block.block_id, "optimized_instructions": output, "stats": {
        "strategy": "original", "original_instruction_count": count,
        "optimized_instruction_count": count, "inserted_copy_count": 0,
        "total_copy_count": copies, "copy_ratio_output": copies/count if count else 0.0,
        "inserted_copy_ratio_original": 0.0, "elapsed_ms": (perf_counter()-tick)*1000,
        "original_order": list(range(count)),
        "bit_width": block.bit_width, "max_back_distance": block.window}}


def optimize(data, strategy="auto", time_budget_ms=100, max_states=30000, beam_width=128, memory_order="hazard",bound_tolerance=.005):
    if type(bound_tolerance) not in (int,float) or not isfinite(bound_tolerance) or not 0<=bound_tolerance<1:
        raise ValueError('Finite COPY improvement-gap tolerance in [0,1) required')
    if strategy in ('local_swap','local_relocate'):
        tick=perf_counter()
        incumbent=optimize(data,'auto',time_budget_ms,max_states,beam_width,memory_order)
        remaining=time_budget_ms-(perf_counter()-tick)*1000
        if remaining>0:
            block=parse_block(data,memory_order)
            incumbent=improve_order(data,block,incumbent,time_budget_ms=min(50.0,remaining),
                                    neighborhood='relocate' if strategy=='local_relocate' else 'adjacent')
        local=incumbent['stats'].get('local_order',{})
        return {**incumbent,'stats':{**incumbent['stats'],'requested_strategy':strategy,
                'candidate_verify_ms':incumbent['stats'].get('candidate_verify_ms',0)+local.get('verify_ms',0),
                'pure_schedule_ms':incumbent['stats'].get('pure_schedule_ms',0)+max(0,local.get('elapsed_ms',0)-local.get('verify_ms',0)),
                'portfolio_elapsed_ms':(perf_counter()-tick)*1000}}
    started = perf_counter()
    automatic=strategy in ("auto","branch_portfolio","forest_portfolio","minor_portfolio","bound_portfolio","root_portfolio","tree_portfolio","research_portfolio","consumer_portfolio","reduction_portfolio","phase_portfolio")
    if time_budget_ms <= 0 or max_states < 1 or beam_width < 1:
        raise ValueError("Search budgets and beam width must be positive")
    block = parse_block(data, memory_order)
    if strategy in ('research_portfolio','consumer_portfolio','reduction_portfolio','phase_portfolio'):
        # A constructive zero-COPY witness is stronger than trying unrelated
        # negative capacity certificates. Screen/emit it before their scans.
        # The independent verifier still reconstructs original semantics.
        parsed_ms=(perf_counter()-started)*1000
        comb_plan=recognize_comb_forest(block,deadline=started+time_budget_ms/1000)
        if comb_plan is not None:
            remaining=time_budget_ms-(perf_counter()-started)*1000
            if remaining<=0:raise BudgetExceeded('Comb witness preparation exhausted portfolio budget')
            candidate=schedule_comb_forest(block,time_budget_ms=remaining,plan=comb_plan)
            checked=perf_counter();verified(data,candidate);validation_ms=(perf_counter()-checked)*1000
            total_ms=(perf_counter()-started)*1000
            candidate['stats'].update(requested_strategy=strategy,memory_order=memory_order,
               attempts=[{'strategy':'comb_forest','status':'verified','copies':0}],
               search={'outcome':'optimal_under_model','explored_states':0,'reason':'verified zero inserted COPY reaches nonnegative lower bound'},
               optimizer_parse_ms=parsed_ms,candidate_verify_ms=validation_ms,
               pure_schedule_ms=max(0,total_ms-parsed_ms-validation_ms),portfolio_elapsed_ms=total_ms,
               comb_early_witness=True)
            return candidate
    certificate = None
    if automatic or strategy=="exact":
        certificate = forest_capacity_bound(block)
        if certificate and certificate["infeasible_under_model"]:
            raise InfeasibleSchedule(f"proven_infeasible_under_model: {certificate}")
        if sum(node.op=="GET" for node in block.instructions)>=block.window:
            spine_certificate=spine_capacity_bound(block)
            if spine_certificate and spine_certificate["infeasible_under_model"]:
                raise InfeasibleSchedule(f"proven_infeasible_under_model: {spine_certificate}")
            paired_certificate=paired_network_capacity_bound(block)
            if paired_certificate and paired_certificate["infeasible_under_model"]:
                raise InfeasibleSchedule(f"proven_infeasible_under_model: {paired_certificate}")
            sink_certificate=sink_spine_capacity_bound(block)
            if sink_certificate and sink_certificate["infeasible_under_model"]:
                raise InfeasibleSchedule(f"proven_infeasible_under_model: {sink_certificate}")
            rectangle_budget=min(10.0,max(0.0,time_budget_ms-(perf_counter()-started)*1000))
            rectangle_certificate=rectangle_capacity_bound(block,time_budget_ms=rectangle_budget) if rectangle_budget>0 else None
            if rectangle_certificate and rectangle_certificate["infeasible_under_model"]:
                raise InfeasibleSchedule(f"proven_infeasible_under_model: {rectangle_certificate}")
            prefix_budget=min(15.0,max(0.0,time_budget_ms-(perf_counter()-started)*1000))
            prefix_certificate=shared_prefix_capacity_bound(block,time_budget_ms=prefix_budget) if prefix_budget>0 else None
            if prefix_certificate and prefix_certificate['infeasible_under_model']:
                raise InfeasibleSchedule(f"proven_infeasible_under_model: {prefix_certificate}")
        if strategy=='minor_portfolio' and certificate is None and block.bit_width<5 and 128<=len(block.instructions)<=8192:
            minor_budget=min(25.0,max(0.0,time_budget_ms-(perf_counter()-started)*1000))
            minor_certificate=contraction_bound(data,time_budget_ms=minor_budget,parsed_block=block) if minor_budget>0 else None
            if minor_certificate and minor_certificate['lower_bound']>block.window:
                checked=perf_counter();proof=check_contraction_certificate(data,minor_certificate)
                minor_certificate['independent_verify_ms']=(perf_counter()-checked)*1000
                if proof['infeasible_under_identity_model']:
                    raise InfeasibleSchedule(f"proven_infeasible_under_model: {minor_certificate}")
    quality_bound=spine_copy_bound(block) if strategy=='bound_portfolio' and len(block.instructions)>=512 else None
    if strategy=='bound_portfolio' and len(block.instructions)>=512:
        general_bound=consumer_copy_bound(block)
        if general_bound and (quality_bound is None or general_bound['copy_lower_bound']>quality_bound['copy_lower_bound']):quality_bound=general_bound
        pair_bound=pair_copy_bound(block)
        if pair_bound and (quality_bound is None or pair_bound['copy_lower_bound']>quality_bound['copy_lower_bound']):quality_bound=pair_bound
    quality_tolerance=bound_tolerance if strategy=='bound_portfolio' else 0
    if strategy=='terminal_pairs':quality_bound=pair_copy_bound(block)
    sufficient_quality=False
    parse_ms = (perf_counter() - started) * 1000
    validation_ms = 0.0
    context = None  # Construct only after the first viable candidate exists.
    prepared = None
    best, attempts = None, []
    root_plan=comb_plan=column_plan=None
    if automatic:
        legal_original = all(node.index-source <= block.window for node in block.instructions for source in node.args)
        baselines = ("original",) if legal_original else ("stable_fast", "pressure", "ready_fast", "demand", "incremental")
        if not legal_original and certificate and certificate["unequal_work_equal_demand_pairs"]:
            # Work tie-break is reliable only as a forest heuristic. Keep every
            # earlier baseline; finite budget may still prevent reaching one.
            baselines=("stable_fast","size_pressure","pressure","ready_fast","demand","incremental")
        if strategy=="forest_portfolio" and not legal_original and certificate and certificate.get("complete_output_forest"):
            # A complete unshared forest can be emitted directly in postorder.
            # Avoid first verifying a long-lived original ordering; keep it as
            # a later quality candidate and retain a budget for every fallback.
            baselines=((("size_pressure","pressure") if certificate["unequal_work_equal_demand_pairs"] else ("pressure",))+
                       ("stable_fast","ready_fast","demand","incremental"))
        if not legal_original and sum(node.op == "SET" for node in block.instructions) > 1:
            get_uses = Counter(source for node in block.instructions for source in set(node.args)
                               if block.instructions[source].op == "GET")
            # More than one heavily shared input and multiple outputs is a
            # structural opportunity to finish one input's consumers together.
            # No generator family names or seed-specific rules are used.
            if sum(uses >= 4 for uses in get_uses.values()) > 1:
                baselines = ("affinity", "stable_fast", "pressure", "ready_fast", "demand", "incremental")
                if strategy=="branch_portfolio" and sum(node.op=="SET" for node in block.instructions)<=16:
                    baselines=("branch_dp",)+baselines
        if certificate and certificate.get("complete_output_forest") and certificate["minimum_register_slots"]==1:
            baselines=("chain_forest",)
        terminal_plan=recognize_terminal_pairs(block,started+time_budget_ms/1000) if not legal_original and strategy in ('auto','bound_portfolio') else None
        if terminal_plan is not None:
            baselines=('terminal_pairs',)+baselines
            if strategy=='auto':quality_bound=pair_copy_bound(block)
        if strategy in ('root_portfolio','research_portfolio','consumer_portfolio','reduction_portfolio','phase_portfolio') and not legal_original:
            root_plan=recognize_root_spines(block,deadline=started+time_budget_ms/1000)
            if root_plan is not None:baselines=('root_spines',)+baselines
        if strategy in ('tree_portfolio','research_portfolio','consumer_portfolio','reduction_portfolio','phase_portfolio') and not legal_original and certificate and certificate.get('complete_output_forest') and certificate['minimum_register_slots']>1:
            # Establish the old demand-based candidate before testing reverse
            # pressure. Six new padded-tree cases show that reverse alone can
            # be worse; preserve every previous fallback and verified output.
            for position,baseline in enumerate(baselines):
                if baseline in ('pressure','size_pressure'):
                    baselines=baselines[:position+1]+('reverse_pressure',)+baselines[position+1:]
                    break
        if strategy in ('research_portfolio','consumer_portfolio','reduction_portfolio','phase_portfolio') and not legal_original and certificate and certificate.get('complete_output_forest') and certificate['minimum_register_slots']==2:
            comb_plan=recognize_comb_forest(block,deadline=started+time_budget_ms/1000)
            if comb_plan is not None:baselines=('comb_forest',)+baselines
        if strategy=='consumer_portfolio' and not legal_original and root_plan is None and certificate is None:
            consumers=Counter(s for node in block.instructions for s in set(node.args))
            if any(count>1 for count in consumers.values()):
                # Retain the first verified forward candidate and all its
                # fallbacks. Test a consumer closure only on shared DAGs.
                for position,baseline in enumerate(baselines):
                    if baseline in ('affinity','pressure'):
                        baselines=baselines[:position+1]+('consumer_cluster',)+baselines[position+1:]
                        break
        if strategy=='reduction_portfolio' and not legal_original:
            column_plan=recognize_reduction_columns(block,deadline=started+time_budget_ms/1000)
            if column_plan is not None:baselines=('reduction_columns',)+baselines
        if strategy=='phase_portfolio' and not legal_original and root_plan is None and certificate is None and sum(node.op=='SET'for node in block.instructions)<=16:
            # Establish an old incumbent before spending the bounded candidate
            # budget; restricted matcher failures never reject the input.
            for position,baseline in enumerate(baselines):
                if baseline in ('affinity','pressure'):
                    baselines=baselines[:position+1]+('root_phases',)+baselines[position+1:]
                    break
    else:
        baselines = ("ready", "stable") if strategy in ("beam", "exact") else (strategy,)
    deadline = started + time_budget_ms / 1000
    for baseline in baselines:
        remaining = (deadline - perf_counter()) * 1000
        if remaining <= 0:
            attempts.append({"strategy": baseline, "status": "time_budget_exhausted"})
            break
        try:
            if baseline == "original":
                candidate = original_candidate(block, remaining)
            elif baseline == "chain_forest":
                candidate = emit_single_source_chains(block,time_budget_ms=remaining)
            elif baseline=='comb_forest':
                candidate=schedule_comb_forest(block,time_budget_ms=remaining,plan=comb_plan)
            elif baseline=='reduction_columns':
                if automatic:remaining=min(remaining,max(25.0,time_budget_ms*.4))
                candidate=schedule_reduction_columns(block,time_budget_ms=remaining,plan=column_plan)
            elif baseline=='root_phases':
                if automatic:remaining=min(remaining,max(25.0,time_budget_ms*.4))
                candidate=schedule_root_phases(block,time_budget_ms=remaining,prepared=prepared)
            elif baseline=='terminal_pairs':
                if automatic:remaining=min(remaining,max(5.0,min(200.0,time_budget_ms*.5)))
                candidate=schedule_terminal_pairs(block,time_budget_ms=remaining,plan=terminal_plan if automatic else None)
            elif baseline == "alias_pressure":
                candidate = schedule_aliases(block, time_budget_ms=remaining)
            elif baseline == "branch_dp":
                if automatic:remaining=min(remaining,max(25.0,time_budget_ms*0.4))
                prep_started=perf_counter()
                if prepared is None:prepared=PreparedGraph(block,time_budget_ms=remaining)
                remaining-=(perf_counter()-prep_started)*1000
                candidate=schedule_branches(block,prepared,time_budget_ms=remaining)
            elif baseline=='branch_copy':
                prep_started=perf_counter()
                if prepared is None:prepared=PreparedGraph(block,time_budget_ms=remaining)
                remaining-=(perf_counter()-prep_started)*1000
                candidate=schedule_branch_copy(data,block,prepared,time_budget_ms=remaining)
            elif baseline in ("pressure", "demand", "incremental", "stable_fast", "ready_fast", "affinity", "deadline", "age_first", "size_pressure", "forest_work"):
                if automatic and baseline in ("affinity","size_pressure") and best is None:
                    remaining = min(remaining, max(25.0, time_budget_ms * 0.6))
                if strategy=="forest_portfolio" and baseline=="pressure" and best is None and certificate and certificate.get("complete_output_forest"):
                    remaining=min(remaining,max(25.0,time_budget_ms*0.6))
                if strategy=='consumer_portfolio' and baseline=='pressure' and best is None:
                    remaining=min(remaining,max(25.0,time_budget_ms*.6))
                prep_started = perf_counter()
                if prepared is None:
                    prepared = PreparedGraph(block,time_budget_ms=remaining)
                    if automatic and certificate is None:prepared.complete_forest_eligibility=False
                if automatic and baseline == "stable_fast" and prepared.original_peak_live > block.window:
                    attempts.append({"strategy": baseline, "status": "skipped_original_order_capacity",
                                     "peak_live": prepared.original_peak_live, "window": block.window,
                                     "scope": "fixed original order only; not whole-problem infeasibility"})
                    continue
                remaining -= (perf_counter()-prep_started)*1000
                if baseline in ("pressure","demand","size_pressure","forest_work") and forest_eligible(block,prepared):
                    candidate=emit_forest(block,prepared,time_budget_ms=remaining,work_first=baseline=="forest_work",
                                          policy="size_pressure" if baseline=="forest_work" else baseline)
                elif baseline=="forest_work":
                    raise InfeasibleSchedule("forest_work requires complete unshared GET/SET forests")
                else:
                    candidate = schedule_incremental(block, policy=baseline, time_budget_ms=remaining,prepared=prepared)
            elif baseline in ('reverse_pressure','reverse_cluster','reverse_span','consumer_cluster'):
                if automatic:remaining=min(remaining,max(25.0,time_budget_ms*.6))
                if automatic and baseline=='consumer_cluster':remaining=min(remaining,max(10.0,time_budget_ms*.4))
                candidate=schedule_reverse_pressure(block,policy=baseline,time_budget_ms=remaining,prepared=prepared)
            elif baseline=='root_spines':
                # Candidate-first portfolio, no optimality assertion or removed
                # fallback. Already verified incumbents survive budget expiry.
                if automatic:remaining=min(remaining,max(25.0,time_budget_ms*.6))
                candidate=schedule_root_spines(block,time_budget_ms=remaining,plan=root_plan)
            else:
                candidate = schedule(block, strategy=baseline, time_budget_ms=remaining)
            if best is not None and candidate["stats"]["inserted_copy_count"] >= best["stats"]["inserted_copy_count"]:
                attempts.append({"strategy": baseline, "status": "discarded_no_improvement_unverified",
                                 "copies": candidate["stats"]["inserted_copy_count"]})
                continue
            checked = perf_counter()
            if context is None:
                context = VerificationContext(data)
            verified(data, candidate, context)
            validation_ms += (perf_counter() - checked) * 1000
            attempts.append({"strategy": baseline, "status": "verified", "copies": candidate["stats"]["inserted_copy_count"]})
            if best is None or candidate["stats"]["inserted_copy_count"] < best["stats"]["inserted_copy_count"]:
                best = candidate
            if quality_bound and quality_bound['copy_lower_bound']>0:
                cost=best['stats']['inserted_copy_count'];lower=quality_bound['copy_lower_bound']
                if lower>cost:raise VerificationFailed('Spine lower bound contradicted by verified candidate')
                if cost-lower<=cost*quality_tolerance:
                    checked=perf_counter()
                    try:
                        identity_proof=check_identity_witness(data,best,best['stats'].get('original_order'),memory_order=memory_order)
                        identity_verify_ms=(perf_counter()-checked)*1000
                        checked=perf_counter()
                        checker={'distinct_consumer_identity_relay_sum':check_consumer_copy_certificate,'disjoint_terminal_root_pairs_age_sum':check_pair_copy_certificate}.get(quality_bound['kind'],check_spine_copy_certificate)
                        independent_bound=checker(data,quality_bound)
                    except InvalidBlock as exc:raise VerificationFailed(f'Independent COPY quality certificate rejected: {exc}') from exc
                    bound_verify_ms=(perf_counter()-checked)*1000;validation_ms+=bound_verify_ms+identity_verify_ms
                    sufficient_quality=True
                    certificate_key='approximation_certificate' if strategy=='bound_portfolio' else 'optimality_certificate'
                    best['stats'][certificate_key]={**quality_bound,'maximum_relative_copy_reduction':(cost-lower)/cost,
                                                               'tolerance':quality_tolerance,'reason':'explicit bounded-quality early stop' if strategy=='bound_portfolio' else 'exact identity-model lower bound reached',
                                                               'independent_raw_json_verification':independent_bound,
                                                                 'independent_identity_witness':identity_proof,
                                                                 'independent_identity_verify_ms':identity_verify_ms,
                                                               'independent_bound_verify_ms':bound_verify_ms}
                    outcome='bounded_quality_under_spine_identity_model' if quality_bound['kind']=='forced_spine_persistent_age_sum' else 'bounded_quality_under_identity_model'
                    if certificate_key=='optimality_certificate':outcome='optimal_under_model'
                    best['stats']['search']={'outcome':outcome,'explored_states':0}
                    break
            if automatic and best["stats"]["inserted_copy_count"] == 0:
                best["stats"]["search"] = {"outcome": "optimal_under_model", "explored_states": 0,
                                          "reason": "zero inserted COPY reaches the nonnegative lower bound",
                                          "memory_order": memory_order}
                break
        except (InfeasibleSchedule, BudgetExceeded) as exc:
            attempts.append({"strategy": baseline, "status": type(exc).__name__, "error": str(exc)})
    if (automatic or strategy in ("beam", "exact")) and not sufficient_quality and not (automatic and best and best["stats"]["inserted_copy_count"] == 0):
        remaining = (deadline - perf_counter()) * 1000
        # A retained incumbent makes large-graph search an optional quality
        # improvement. Bound that cost instead of consuming the whole budget.
        if automatic and best and len(block.instructions) > 10:
            remaining = min(remaining, max(5.0, min(25.0, time_budget_ms * 0.2)))
        if remaining > 0:
            use_exact = strategy == "exact" or (automatic and len(block.instructions) <= 10)
            try:
                candidate = search(block, best, time_budget_ms=remaining, max_states=max_states,
                                   beam_width=None if use_exact else beam_width)
                checked = perf_counter()
                promoted = best is None or candidate["stats"]["inserted_copy_count"] < best["stats"]["inserted_copy_count"]
                if promoted:
                    if context is None:
                        context = VerificationContext(data)
                    verified(data, candidate, context)
                    validation_ms += (perf_counter() - checked) * 1000
                    best = candidate
                elif "search" in candidate["stats"]:
                    best = {**best, "stats": {**best["stats"], "search": candidate["stats"]["search"]}}
                attempts.append({"strategy": "exact" if use_exact else "beam", "status": "verified" if promoted else "retained_verified_incumbent",
                                 "search_outcome": candidate["stats"]["search"]["outcome"]})
            except (InfeasibleSchedule, BudgetExceeded) as exc:
                attempts.append({"strategy": "exact" if use_exact else "beam", "status": type(exc).__name__, "error": str(exc)})
        else:
            attempts.append({"strategy": "search", "status": "time_budget_exhausted"})
    if best is None:
        if any(a["status"] == "BudgetExceeded" or a["status"] == "time_budget_exhausted" for a in attempts):
            raise BudgetExceeded(f"No verified candidate within budget: {attempts}")
        raise InfeasibleSchedule(f"No verified candidate: {attempts}")
    best = {**best, "stats": {**best["stats"], "requested_strategy": strategy, "attempts": attempts,
                              "memory_order": memory_order,
                              "portfolio_elapsed_ms": (perf_counter() - started) * 1000,
                              "optimizer_parse_ms": parse_ms, "candidate_verify_ms": validation_ms,
                              "pure_schedule_ms": max(0.0, (perf_counter() - started) * 1000 - parse_ms - validation_ms)}}
    if strategy=='bound_portfolio':best['stats']['bound_tolerance']=bound_tolerance
    return best

