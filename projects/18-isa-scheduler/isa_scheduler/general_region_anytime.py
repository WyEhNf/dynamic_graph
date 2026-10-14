"""Explicit general-DAG region search. No default strategy integration.

Latest-copy/deadline transitions are a restricted proposal family, not an
infeasibility oracle. All costs refer to complete original+COPY physical rows.
"""
from collections import Counter
import heapq
import json
from time import perf_counter

from .model import parse_block
from .identity_witness import check_identity_witness


class RegionStop(Exception):
    pass


class RegionAgenda:
    def __init__(self):
        self.labels = []; self.heap = []; self.best = {}; self.pending = set()
        self.expanded = {}; self.reopens = self.stale = 0

    def offer(self, state, g, h, predecessor, action):
        old = self.best.get(state)
        if old is not None and self.labels[old][1] <= g: return False
        if state in self.expanded: self.reopens += 1
        version = len(self.labels)
        self.labels.append((state, g, h, predecessor, action))
        self.best[state] = version; self.pending.add(state)
        heapq.heappush(self.heap, (g + 2*h, h, version))
        return True

    def pop(self):
        while self.heap:
            _, _, version = heapq.heappop(self.heap)
            state, g, h, _, _ = self.labels[version]
            if self.best.get(state) != version or state not in self.pending:
                self.stale += 1; continue
            self.pending.remove(state)
            return version, state, g, h
        return None


def resource_layout(data, incumbent):
    """Serialized per-record bounds, including real N/W and baseline F.

    Arbitrarily redundant baseline COPY is allowed, so N*W alone does not
    bound the preserved prefix. F+N*W is the conservative whole-output bound.
    Complete outputs are streamed; 1024 outputs are NOT reserved in memory.
    """
    n = len(data['instructions']); w = 2**data['bit_width']
    f = len(incumbent['output']['optimized_instructions']); rows = f+n*w
    encode = lambda item: len(json.dumps(item, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    roles = tuple((max(0,n-1),w) for _ in range(w))
    label = {'kind':'immutable_label','label_version':20063,'done_mask':2**32-1,
             'roles':roles,'g':rows,'h':n,'predecessor_label':20063,'action':max(0,n-1)}
    opened = dict(label, kind='unfinished_expansion', phase='prepare_neighbors',
                  next_ready_cursor=32, buffered_unpublished=32, reason='transition_budget')
    copy_row = {'id':rows,'op':'COPY','source':f't#{w}'}
    original_bytes = 0
    for row in data['instructions']:
        prototype = {'id':rows,'op':row['op']}
        if 'reg' in row: prototype['reg'] = row['reg']
        if row.get('inputs'): prototype['inputs'] = [f't#{w}']*len(row['inputs'])
        elif row['op']=='GET': prototype['inputs'] = []  # Legal redundant baseline field.
        original_bytes += encode(prototype)+1
    proposal = original_bytes + max(0,rows-n)*(encode(copy_row)+1)
    proposal += encode({'block_id':data['block_id'],'optimized_instructions':[]})+n*len(str(max(0,n-1)))+n+256
    return {'N':n,'W':w,'initial_physical_F':f,'whole_rows_bound_F_plus_NW':rows,
            'label_record_bound_bytes':encode(label)+1,'open_record_bound_bytes':encode(opened)+1,
            'complete_proposal_bound_bytes':proposal,'max_labels':20064,'max_complete_outputs':1024,
            'diagnostic_bound_bytes':20064*(1024+2048)+64*4096,
            'reserve_bytes':512*1024*1024,
            'scope':'Compact UTF-8 JSONL records; complete outputs streamed, disk availability checked by producer. Planned bounds, not measured RSS.'}


def _prepare(data, incumbent, check):
    check(); block = parse_block(data); nodes = block.instructions; n = len(nodes)
    if n > 16384: raise ValueError('input_size_unsupported: research N<=16384')
    if any(node.op == 'COPY' for node in nodes): raise ValueError('Original COPY unsupported')
    check_identity_witness(data, incumbent['output'], incumbent['original_order']); check()
    order = tuple(incumbent['original_order']); ranks = {node:i for i,node in enumerate(order)}
    users = [set() for _ in nodes]
    for node in nodes:
        check()
        for source in set(node.args): users[source].add(node.index)
        if any(nodes[source].op == 'SET' for source in node.args): raise ValueError('SET has no output identity')
    layout = resource_layout(data, incumbent); check()
    if layout['label_record_bound_bytes'] > 1024 or layout['open_record_bound_bytes'] > 2048:
        raise ValueError('serialized_record_size_unsupported')
    return {'block':block,'nodes':nodes,'n':n,'order':order,'ranks':ranks,'users':users,'layout':layout}


def _prefix(graph, incumbent, start, check):
    """Include ALL baseline COPY rows preceding the first regional original."""
    rows = []; history = []; completed = set(); latest = {}; cursor = 0
    w = graph['block'].window; order = graph['order']
    for row in incumbent['output']['optimized_instructions']:
        check()
        if row['op'] != 'COPY' and cursor == start: break
        position = len(rows)
        if row['op'] == 'COPY':
            distance = int(row['source'][2:])
            if not 1 <= distance <= min(w,position): raise ValueError('Invalid physical prefix COPY')
            identity = history[position-distance]
            if identity is None: raise ValueError('Prefix COPY of non-result')
        else:
            identity = order[cursor]; cursor += 1; completed.add(identity)
            if row['op'] == 'SET': identity = None
        rows.append(dict(row)); history.append(identity)
        if identity is not None: latest[identity] = position
    if cursor != start: raise ValueError('Missing physical prefix')
    live = {node:len(rows)-latest[node] for node in completed
            if any(user not in completed for user in graph['users'][node])}
    if any(not 1 <= age <= w for age in live.values()): raise ValueError('Expired prefix future role')
    return rows, completed, tuple(sorted(live.items()))


def _step(graph, index, completed, roles, check):
    """One charged transition: latest/deadline COPY with true last use."""
    node = graph['nodes'][index]; users = graph['users']; w = graph['block'].window
    args = set(node.args); ages = dict(roles); after = completed | {index}
    last = {source for source in args if not (users[source]-after)}
    if not (args | set(node.order_deps)) <= completed: return None
    if not args <= ages.keys(): return None
    emitted = []
    rotations = 0
    while ages and max(ages.values()) == w:
        check(); oldest = min(ages, key=lambda source:(-ages[source],source))
        if oldest in last: break
        if rotations >= w: return None
        emitted.append({'op':'COPY','source':f't#{ages[oldest]}'})
        ages = {source:age+1 for source,age in ages.items()}; ages[oldest] = 1
        if max(ages.values()) > w: return None
        rotations += 1
    if any(not 1 <= ages[source] <= w for source in args): return None
    row = {'op':node.op}
    if node.reg is not None: row['reg'] = node.reg
    if node.args: row['inputs'] = [f't#{ages[source]}' for source in node.args]
    emitted.append(row)
    ages = {source:age+1 for source,age in ages.items() if source not in last}
    if users[index]-after: ages[index] = 1
    if any(age > w for age in ages.values()): return None
    return tuple(sorted(ages.items())), emitted


class RegionDiagnostics:
    def __init__(self, agenda, unfinished):
        self.agenda = agenda; self.unfinished = unfinished


def iter_region_frontier(diagnostics):
    """Producer-only export; no post-deadline materialization in core."""
    agenda = diagnostics.agenda
    yield {'kind':'header','open_count':len(agenda.pending),'labels':len(agenda.labels)}
    for version,(state,g,h,predecessor,action) in enumerate(agenda.labels):
        yield {'kind':'immutable_label','label_version':version,'done_mask':state[0],
               'roles':state[1],'g':g,'h':h,'predecessor_label':predecessor,'action':action}
    for state in agenda.pending:
        version = agenda.best[state]; _,g,h,_,_ = agenda.labels[version]
        yield {'kind':'open','done_mask':state[0],'roles':state[1],'g':g,'h':h,'label_version':version}
    if diagnostics.unfinished is not None: yield dict(diagnostics.unfinished,kind='unfinished_expansion')


def search_general_region(data, incumbent, start, *, region_nodes=32, time_budget_ms=500,
        max_states=20000, max_transitions=20000, max_outcomes=16,
        absolute_deadline=None, on_completed=None, prepared=None):
    started = perf_counter(); deadline = started+time_budget_ms/1000
    if absolute_deadline is not None: deadline = min(deadline,absolute_deadline)
    if min(time_budget_ms,max_states,max_transitions,max_outcomes,region_nodes)<=0 or region_nodes>32:
        raise ValueError('Positive budgets and region<=32 required')
    agenda = RegionAgenda(); processed = attempted = goals = 0; max_open = 0
    unfinished = None; outcome = 'exhausted_improvement_search'; current = None
    phase = 'prepare'; cursor = 0; buffered = []; best = dict(incumbent)
    best['copies'] = sum(row['op']=='COPY' for row in incumbent['output']['optimized_instructions'])
    upper = len(incumbent['output']['optimized_instructions']); first_goal = None
    def check():
        if perf_counter() >= deadline: raise RegionStop('total_deadline')
    def append_rows(rows, additions):
        for item in additions:
            check(); rows.append(dict(item,id=len(rows)))
    try:
        graph = prepared if prepared is not None else _prepare(data,incumbent,check)
        if prepared is not None and (prepared['raw_data'] != data or prepared['incumbent'] != incumbent):
            raise ValueError('Prepared graph belongs to another input/incumbent')
        check(); n = graph['n']; order = graph['order']
        if type(start) is not int or not 0 <= start < n: raise ValueError('Invalid region start')
        stop = min(n,start+region_nodes); members = order[start:stop]
        local = {node:i for i,node in enumerate(members)}; full = (1<<len(members))-1
        prefix, prefix_done, incoming = _prefix(graph,incumbent,start,check)
        for index in members:
            check()
            if any(dep not in prefix_done and dep not in local for dep in set(graph['nodes'][index].args)|set(graph['nodes'][index].order_deps)):
                raise ValueError('Regional predecessor in suffix')
        agenda.offer((0,incoming),len(prefix),n-start,None,None)
        phase = 'search'
        while agenda.heap:
            check(); current = agenda.pop()
            if current is None: break
            version,state,g,h = current; mask,roles = state
            if g+h >= upper: continue
            completed = prefix_done | {node for node in members if mask & (1<<local[node])}
            if mask == full:
                phase = 'restore_suffix'; rows = [dict(row) for row in prefix]; path = []; label = version
                while agenda.labels[label][3] is not None:
                    check(); _,_,_,parent,action = agenda.labels[label]; path.append(action); label = parent
                path.reverse(); live = incoming; issued = set(prefix_done)
                for index in path:
                    check(); moved = _step(graph,index,issued,live,check)
                    if moved is None: raise AssertionError('Regional path cannot restore')
                    live,additions = moved; append_rows(rows,additions); issued.add(index)
                if len(rows)!=g or live!=roles: raise AssertionError('Exact regional endpoint mismatch')
                for index in order[stop:]:
                    moved = _step(graph,index,issued,live,check)
                    if moved is None: raise RegionStop('restricted_suffix_failure')
                    live,additions = moved; append_rows(rows,additions); issued.add(index)
                proposed = list(order[:start])+path+list(order[stop:])
                copies = len(rows)-n
                if issued != set(range(n)) or copies != sum(row['op']=='COPY' for row in rows):
                    raise AssertionError('Whole original+COPY objective mismatch')
                candidate = {'output':{'block_id':graph['block'].block_id,'optimized_instructions':rows},
                             'original_order':proposed,'copies':copies}
                goals += 1
                if first_goal is None: first_goal = {'processed_states':processed,'attempted_transitions':attempted,'search_emit_ms':(perf_counter()-started)*1000}
                if len(rows)<upper: best=candidate; upper=len(rows)
                if on_completed is not None: on_completed(candidate)
                check()
                if goals>=max_outcomes: raise RegionStop('complete_outlet_limit')
                phase='search'; continue
            if processed>=max_states: raise RegionStop('state_budget')
            processed += 1; phase='prepare_neighbors'; cursor=0; buffered=[]
            ready = [index for index in members if not mask & (1<<local[index]) and
                     (set(graph['nodes'][index].args)|set(graph['nodes'][index].order_deps)) <= completed]
            for cursor,index in enumerate(ready):
                check()
                if attempted>=max_transitions: raise RegionStop('transition_budget')
                attempted += 1; moved = _step(graph,index,completed,roles,check)
                if moved is None: continue
                next_roles,additions = moved; ng=g+len(additions); nh=h-1
                if ng+nh >= upper: continue
                consumers = len(graph['users'][index]-(completed|{index})) if graph['nodes'][index].op=='GET' else 0
                key = (len(additions)-1,len(next_roles)-len(roles),consumers,graph['ranks'][index])
                buffered.append((key,index,next_roles,ng,nh))
            phase='publish_neighbors'; buffered.sort(key=lambda item:item[0])
            for cursor,(_,index,next_roles,ng,nh) in enumerate(buffered):
                check(); agenda.offer((mask|(1<<local[index]),next_roles),ng,nh,version,index)
            agenda.expanded[state]=g; max_open=max(max_open,len(agenda.pending)); buffered=[]; phase='search'
    except RegionStop as error:
        outcome='partial_outlet_limit' if str(error)=='complete_outlet_limit' else 'partial_'+str(error)
        if current is not None:
            version,state,g,h=current
            unfinished={'done_mask':state[0],'roles':state[1],'g':g,'h':h,'label_version':version,
                        'reason':str(error),'phase':phase,'next_ready_cursor':cursor,
                        'buffered_unpublished':len(buffered) if phase=='prepare_neighbors' else max(0,len(buffered)-cursor)}
    return {'best':best,'diagnostics':RegionDiagnostics(agenda,unfinished),'stats':{
        'outcome':outcome,'processed_states':processed,'attempted_transitions':attempted,
        'accepted_labels':len(agenda.labels),'complete_outputs':goals,'first_complete':first_goal,
        'reopens':agenda.reopens,'stale':agenda.stale,'max_open':max_open,
        'search_emit_ms':(perf_counter()-started)*1000,
        'scope':'Restricted latest/deadline COPY region family; no infeasibility or COPY approximation claim.'}}
