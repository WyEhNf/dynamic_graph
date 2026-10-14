"""Isolated fixed-w=2 anytime search of the frozen fixed-pair family.

Complete N+COPY output is the objective; weighted rows are not a COPY ratio
bound. Only exact role-age states merge. No new COPY timing or default hook.
"""
from collections import Counter
import heapq
from time import perf_counter

from .model import parse_block
from .tree_pipeline import match_forest, _advance


class _Agenda:
    """Immutable labels, exact-state best-g replacement and stale rejection."""
    def __init__(self):
        self.heap = []; self.labels = []; self.best = {}; self.expanded = {}; self.pending = set()
        self.reopens = self.stale = self.replacements = 0

    def offer(self, state, g, h, path):
        prior = self.best.get(state)
        if prior is not None and self.labels[prior][1] <= g: return False
        if prior is not None: self.replacements += 1
        if state in self.expanded: self.reopens += 1
        label = len(self.labels)
        self.labels.append((state, g, h, path)); self.best[state] = label; self.pending.add(state)
        heapq.heappush(self.heap, (g+2*h, h, label))
        return True

    def pop(self):
        while self.heap:
            _, _, label = heapq.heappop(self.heap)
            state, g, h, path = self.labels[label]
            if self.best.get(state) != label or state not in self.pending:
                self.stale += 1; continue
            self.pending.remove(state)
            return state, g, h, path
        return None

    def mark_expanded(self, state, g):
        self.expanded[state] = g

    def frontier(self):
        return [self.labels[self.best[state]] for state in self.pending]


class _Stop(Exception):
    pass


class _FrontierReferences:
    """O(1) ownership transfer of settled search containers, not export.

    Labels/path tuples are immutable. The pending/best/cache containers are
    private stable references: the search never mutates them after returning.
    Only the producer's explicit iterator reads them afterwards.
    """
    def __init__(self, agenda, external, active_cache, unfinished):
        self.agenda = agenda; self.external = external
        self.active_cache = active_cache; self.unfinished = unfinished


def iter_anytime_frontier(diagnostics):
    """Explicit producer-side JSONL records; all export work is outside search.

    Shared immutable predecessor labels avoid serializing every full path in
    every OPEN record. Iteration, JSON encoding and I/O are timed
    separately by the evidence producer. No closed/optimality certificate.
    """
    agenda = diagnostics.agenda
    yield {'kind':'frontier_header','actual_open_count':len(agenda.pending),
           'unfinished_expansion_present':diagnostics.unfinished is not None}
    path_versions = {id(path):version for version,(_,_,_,path) in enumerate(agenda.labels) if path is not None}
    for version,(state,g,h,path) in enumerate(agenda.labels):
        predecessor = None if path is None or path[0] is None else path_versions[id(path[0])]
        yield {'kind':'immutable_path_label','label_version':version,'predecessor_label':predecessor,
               'action':None if path is None else path[1],'prefixes':state[:2],'ages':state[2],'g':g,'h':h}
    for state in agenda.pending:
        version = agenda.best[state]; _,g,h,_ = agenda.labels[version]
        roles = diagnostics.external+diagnostics.active_cache[state[:2]]
        yield {'kind':'open','i':state[0],'j':state[1],'roles':roles,'ages':state[2],
               'g':g,'h':h,'label_version':version}
    if diagnostics.unfinished is not None:
        unfinished = diagnostics.unfinished; state = unfinished['state']
        yield {'kind':'unfinished_expansion','i':state[0],'j':state[1],
               'roles':diagnostics.external+diagnostics.active_cache[state[:2]],'ages':state[2],
               'g':unfinished['g'],'h':unfinished['h'],'label_version':agenda.best[state],
               'reason':unfinished['reason'],'next_side':unfinished.get('next_side')}


def schedule_fixed_tree_pair_anytime(data, incumbent, parent, *, time_budget_ms=500,
        max_states=20000, max_outcomes=16, max_parent_nodes=96, on_completed=None,
        absolute_deadline=None):
    """Return best complete incumbent even at partial interruption.

    Unsupported/malformed input raises ValueError. Budget interruption is not
    infeasibility. Frontier is actual current state data, serialized by callers
    afterwards; a mid-expansion interrupt is explicitly retained as unfinished.
    """
    started = perf_counter(); deadline = started + time_budget_ms/1000
    if absolute_deadline is not None: deadline = min(deadline, absolute_deadline)
    if min(time_budget_ms, max_states, max_outcomes, max_parent_nodes) <= 0:
        raise ValueError('Positive budgets required')
    agenda = _Agenda(); processed = pruned = goals = 0; expanded_depths = Counter()
    max_progress = max_open = max_live = 0; first_goal = first_improvement = None
    unfinished = None; outcome = 'exhausted_improvement_search'; message = None
    external = (); sides = (); initial_ages = (); start = stop = None; prefix = []
    current = None; phase = 'prepare'; results = []; final_g = {}; active_cache = {}
    # Reading incoming cost is inside the total budget.
    baseline_copies = sum(row['op']=='COPY' for row in incumbent['output']['optimized_instructions'])
    best = {'output': incumbent['output'], 'original_order': incumbent['original_order'], 'copies': baseline_copies}
    upper = len(incumbent['output']['optimized_instructions'])

    def check():
        if perf_counter() >= deadline: raise _Stop('total_deadline')

    try:
        check(); block = parse_block(data); forest = match_forest(block); check()
        nodes = block.instructions; children = forest['children']; users = forest['users']; window = block.window
        order = incumbent['original_order']; original_output = incumbent['output']['optimized_instructions']
        if sorted(order) != list(range(len(nodes))): raise ValueError('Complete original permutation required')
        if not 0 <= parent < len(nodes) or len(children[parent]) != 2: raise ValueError('Binary parent required')
        subtrees = []
        for node in nodes:
            check(); subtree = {node.index}
            for child in children[node.index]: subtree.update(subtrees[child])
            subtrees.append(subtree)
        members = subtrees[parent]
        if len(members) > max_parent_nodes: raise ValueError('Parent scope exceeds fixed96 cap')
        ranks = {node: rank for rank, node in enumerate(order)}
        start = min(ranks[node] for node in members); stop = max(ranks[node] for node in members)
        if stop-start+1 != len(members) or order[stop] != parent:
            raise ValueError('Pair subtree must be contiguous in incumbent')
        sides = tuple(tuple(node for node in order[start:stop] if node in subtrees[child]) for child in children[parent])
        if not any(any(len(children[node]) == 2 for node in side) for side in sides):
            raise ValueError('At least one side must contain a binary branch')
        history = []; done = set(); latest = {}; cursor = 0
        for row in original_output:
            check()
            if cursor == start: break
            position = len(prefix)
            if row['op'] == 'COPY':
                distance = int(row['source'][2:])
                if not 1 <= distance <= min(window, position): raise ValueError('Bad prefix COPY')
                identity = history[position-distance]
                if identity is None: raise ValueError('COPY of SET')
            else:
                identity = order[cursor]; cursor += 1; done.add(identity)
                if row['op'] != nodes[identity].op: raise ValueError('Prefix opcode mismatch')
                if row['op'] == 'SET': identity = None
            prefix.append(dict(row)); history.append(identity)
            if identity is not None: latest[identity] = position
        if cursor != start: raise ValueError('Incomplete prefix')
        external = tuple(sorted(node for node in done if any(user not in done for user in users[node])))
        if any(node in members for node in external): raise AssertionError('Preborn subtree member')
        initial_ages = tuple(len(prefix)-latest[node] for node in external)
        if any(not 1 <= age <= window for age in initial_ages): raise ValueError('Expired incoming role')
        lengths = tuple(map(len, sides)); active_cache[(0,0)] = ()

        def active(left, right):
            key = left, right
            if key not in active_cache:
                born = set(sides[0][:left]) | set(sides[1][:right])
                active_cache[key] = tuple(sorted(node for node in born if any(user not in born for user in users[node])))
            return active_cache[key]

        def restore_goal(g, path):
            """Full physical output; no unissued-local or partial output sink."""
            nonlocal goals, best, upper, first_goal, first_improvement, phase
            phase = 'restore_terminal'; actions = []
            while path is not None:
                check(); path, action = path; actions.append(action)
            actions.reverse()
            pair_order = [sides[side][offset] for side, offset in actions] + [parent]
            proposed = order[:start] + pair_order + order[stop+1:]
            rows = [dict(row) for row in prefix]; live = {node:latest[node] for node in external}
            completed = set(done); local_copies = 0
            for rank, node_index in enumerate(proposed[start:], start=start):
                check(); node = nodes[node_index]; operands = set(node.args)
                if not (operands | set(node.order_deps)) <= completed: raise AssertionError('Restored dependencies differ')
                rotations = 0
                while live and max(len(rows)-position for position in live.values()) == window:
                    oldest = min(live, key=live.get)
                    if oldest in operands: break
                    if rotations >= window: raise AssertionError('Fixed suffix cannot rotate, fail closed')
                    rows.append({'id':len(rows), 'op':'COPY', 'source':f't#{len(rows)-live[oldest]}'})
                    live[oldest] = len(rows)-1; rotations += 1
                    if rank <= stop: local_copies += 1
                    check()
                if any(not 1 <= len(rows)-live[source] <= window for source in operands):
                    raise AssertionError('Restored operand expired')
                row = {'id':len(rows), 'op':node.op}
                if node.reg is not None: row['reg'] = node.reg
                if node.args: row['inputs'] = [f't#{len(rows)-live[source]}' for source in node.args]
                rows.append(row); completed.add(node_index)
                for source in operands: del live[source]
                if any(user not in completed for user in users[node_index]): live[node_index] = len(rows)-1
                if rank == stop and len(rows) != g:
                    raise AssertionError('Exact AWA* goal-prefix rows differ from physical restoration')
            if completed != set(range(len(nodes))): raise AssertionError('Missing originals')
            copies = sum(row['op']=='COPY' for row in rows)
            if len(rows) != len(nodes)+copies: raise AssertionError('Whole N+COPY objective differs')
            result = {'output':{'block_id':block.block_id,'optimized_instructions':rows},
                      'original_order':proposed,'copies':copies,'local_copies':local_copies}
            results.append(result); goals += 1
            milestone = {'processed_states':processed,'elapsed_ms':(perf_counter()-started)*1000,'copies':copies}
            if first_goal is None: first_goal = dict(milestone)
            if len(rows) < upper:
                best = result; upper = len(rows)
                if first_improvement is None: first_improvement = dict(milestone)
            if on_completed is not None: on_completed(result)
            check()
            if goals >= max_outcomes: raise _Stop('complete_outlet_limit')
            phase = 'search'

        initial = (0,0,initial_ages)
        agenda.offer(initial,len(prefix),len(nodes)-start,None)
        phase = 'search'
        while agenda.heap:
            check(); current = agenda.pop()
            if current is None: break
            state,g,h,path = current
            if g+h >= upper: pruned += 1; current = None; continue
            if processed >= max_states:
                # Removed from OPEN but never expanded: retain it explicitly.
                unfinished = {'state':state,'g':g,'h':h,'reason':'popped_unexpanded'}
                raise _Stop('processed_state_limit')
            left,right,ages = state; prefixes = left,right; live = external+active(left,right)
            processed += 1; agenda.mark_expanded(state,g)
            expanded_depths[left+right] += 1; max_progress = max(max_progress,left+right); max_live = max(max_live,len(live))
            unfinished = {'state':state,'g':g,'h':h,'next_side':0,'reason':'expansion_in_progress'}
            for side in (0,1):
                unfinished['next_side'] = side; check()
                if prefixes[side] == lengths[side]: continue
                node = sides[side][prefixes[side]]; operands = set(nodes[node].args)
                if not operands <= set(live): raise AssertionError('Fixed side not topological')
                transition = _advance(ages,{live.index(source) for source in operands},True,window)
                check()
                if transition is None: continue
                extra,after = transition
                retained = tuple(source for source in live if source not in operands)+(node,)
                ages_by_role = dict(zip(retained,after)); updated = list(prefixes); updated[side] += 1
                next_live = external+active(*updated)
                if set(next_live) != set(retained): raise AssertionError('Role restoration differs')
                following = (*updated,tuple(ages_by_role[source] for source in next_live))
                next_g = g+1+extra; next_h = h-1; next_path = (path,(side,prefixes[side]))
                if next_g+next_h >= upper: pruned += 1; continue
                if tuple(updated) == lengths:
                    prior = final_g.get(following)
                    if prior is not None and prior <= next_g: continue
                    final_g[following] = next_g
                    parent_advance = _advance(following[2],{next_live.index(v) for v in set(nodes[parent].args)},True,window)
                    check()
                    if parent_advance is None: continue
                    parent_copies,_ = parent_advance
                    parent_g = next_g+1+parent_copies
                    if parent_g+next_h-1 >= upper: pruned += 1; continue
                    restore_goal(parent_g,next_path)
                else:
                    agenda.offer(following,next_g,next_h,next_path)
                max_open = max(max_open,len(agenda.pending))
            unfinished = None; current = None
        check()
    except _Stop as error:
        message = str(error)
        outcome = 'partial_outlet_limit' if message == 'complete_outlet_limit' else 'partial_budget'
        if current is not None and unfinished is None:
            unfinished = {'state':current[0],'g':current[1],'h':current[2],'reason':'terminal_or_pop_interrupt'}
    # Capture stop time before any producer-side frontier/path export.
    # O(1) reference transfer; no pending/labels/roles scan after deadline.
    search_emit_ms = (perf_counter()-started)*1000
    diagnostics = _FrontierReferences(agenda,external,active_cache,unfinished)
    return {'best':best,'completed_outlets':results,'diagnostics':diagnostics,'stats':{
        'strategy':'isolated_fixed_w2_anytime_rows','weight':2,'outcome':outcome,'message':message,
        'parent':parent,'sides':sides,'rank_interval':(start,stop),'external_roles':external,'external_ages':initial_ages,
        'processed_states':processed,'states':processed,'complete_outputs':goals,'pruned_states':pruned,
        'reopens':agenda.reopens,'best_g_replacements':agenda.replacements,'stale_entries':agenda.stale,
        'max_progress':max_progress,'max_live':max_live,'max_open_states':max_open,
        'expanded_by_progress':dict(expanded_depths),'first_complete':first_goal,'first_improvement':first_improvement,
        'unfinished_expansion':unfinished,'terminal_phase':phase,'actual_open_count':len(agenda.pending),
        'search_emit_ms':search_emit_ms,'elapsed_ms':search_emit_ms,
        'diagnostics_scope':'Stable exact-state references returned in O(1); producer-side frontier/path export and JSON/I/O are outside search budget and measured separately. No interrupted-frontier lower-bound certificate.',
        'baseline_copies':baseline_copies,'best_copies':best['copies'],
        'parameters':{'total_time_budget_ms':time_budget_ms,'max_states':max_states,'max_outcomes':max_outcomes,'max_parent_nodes':max_parent_nodes},
        'scope':'Fixed side original orders/exact role ages/deadline COPY. Complete N+COPY objective; no COPY multiplicative bound or arbitrary DAG optimality. Interrupted expansion has no closed certificate.'}}
