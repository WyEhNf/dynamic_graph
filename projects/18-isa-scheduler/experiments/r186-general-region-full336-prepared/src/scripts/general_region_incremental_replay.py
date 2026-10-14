"""Independent per-label physical-ring induction for complete corpus export.

Reuses only raw JSON checks, never production graphs/ages/transitions.
The prefix is physically checked once; immutable parents transfer real W slots.
"""
from scripts.general_region_raw_checks import problem,raw_prefix


class IncrementalRegionReplay:
    def __init__(self,data,initial,start):
        originals,args,deps,w,users=problem(data)
        self.originals=originals; self.args=args; self.deps=deps; self.w=w
        self.n=len(originals); self.start=start; self.stop=min(self.n,start+32)
        self.order=initial['original_order']; self.ranks={node:i for i,node in enumerate(self.order)}
        self.members=self.order[start:self.stop]; self.local={node:i for i,node in enumerate(self.members)}
        self.user_mask=[]; self.suffix=[]
        for consumers in users:
            self.user_mask.append(sum(1<<self.local[user] for user in consumers if user in self.local))
            self.suffix.append(any(self.ranks[user]>=self.stop for user in consumers))
        rows,done,history=raw_prefix(data,initial,start)
        if done!=set(self.order[:start]): raise AssertionError('Independent prefix permutation differs')
        self.seed=(0,history,len(rows)); self.labels={}; self.replayed=0

    def done(self,index,mask):
        return self.ranks[index]<self.start or (index in self.local and bool(mask&(1<<self.local[index])))

    def needed(self,index,mask):
        return self.suffix[index] or bool(self.user_mask[index]&~mask)

    def roles(self,mask,ring):
        latest={value:offset for offset,value in enumerate(ring) if value is not None}
        return tuple(sorted((source,len(ring)-offset) for source,offset in latest.items() if self.needed(source,mask)))

    def advance(self,parent,index):
        mask,history,g=parent
        if index not in self.local or self.done(index,mask) or any(not self.done(dep,mask) for dep in self.deps[index]):
            raise AssertionError('Independent label action/dependency/hazard invalid')
        after=mask|(1<<self.local[index]); ring=list(history); rotations=0
        last={source for source in self.args[index] if not self.needed(source,after)}
        while len(ring)>=self.w:
            oldest=ring[-self.w]
            sole=oldest not in ring[-self.w+1:]
            if oldest is None or not self.needed(oldest,mask) or oldest in last or not sole: break
            if rotations>=self.w: raise AssertionError('Independent ring cannot retain label action')
            ring=(ring+[oldest])[-self.w:]; g+=1; rotations+=1
        if any(source not in ring for source in self.args[index]): raise AssertionError('Original ordered operand absent from physical ring')
        # Preserve exact original ordered operands, including repeated identity.
        operand_distances=[len(ring)-max(i for i,value in enumerate(ring) if value==source) for source in self.args[index]]
        if any(not 1<=distance<=self.w for distance in operand_distances): raise AssertionError('Illegal original t# window')
        before_roles=self.roles(mask,ring)
        ring=tuple((ring+[None if self.originals[index]['op']=='SET' else index])[-self.w:]); g+=1
        after_roles=self.roles(after,ring)
        expected={source for source,_ in before_roles if self.needed(source,after)}
        if self.originals[index]['op']!='SET' and self.needed(index,after): expected.add(index)
        if {source for source,_ in after_roles}!=expected: raise AssertionError('Physical future identity was lost')
        return after,ring,g

    def accept(self,record):
        kind=record['kind']
        if kind=='header': return
        version=record['label_version']
        if kind=='immutable_label':
            parent=record['predecessor_label']
            if parent is None:
                if record['action'] is not None: raise AssertionError('Seed action is not empty')
                state=self.seed
            else:
                if parent not in self.labels or parent>=version: raise AssertionError('Nonimmutable/cyclic predecessor')
                state=self.advance(self.labels[parent],record['action'])
            if version in self.labels: raise AssertionError('Duplicate immutable label version')
            self.labels[version]=state
        else:
            if kind not in ('open','unfinished_expansion') or version not in self.labels: raise AssertionError('Unknown diagnostic/reference')
            state=self.labels[version]
        mask,ring,g=state; roles=tuple(tuple(pair) for pair in record['roles'])
        if mask!=record['done_mask'] or roles!=self.roles(mask,ring) or g!=record['g'] or record['h']!=self.n-self.start-mask.bit_count():
            raise AssertionError('Physical induction done/roles/g/h disagreement')
        self.replayed+=1
