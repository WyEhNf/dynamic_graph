"""Independent physical-ring induction, including backbone cursor and suffix.

Only standalone raw JSON helpers are imported. Production states/ages/graphs
and its step/prefix functions are never imported or called.
"""
from scripts.general_region_raw_checks import problem, raw_prefix


class MobilePhysicalReplay:
    def __init__(self, data, initial, region):
        originals, args, deps, width, users = problem(data)
        self.rows, self.args, self.deps, self.width, self.users = originals, args, deps, width, users
        self.n = len(originals)
        self.left, self.right = region['L'], region['R']
        self.order = tuple(initial['original_order'])
        self.ranks = {node: rank for rank, node in enumerate(self.order)}
        self.members = tuple(region['mobile'])
        self.local = {node: rank for rank, node in enumerate(self.members)}
        self.backbone = tuple(node for node in self.order[self.left:self.right + 1] if node not in self.local)
        self.backbone_rank = {node: rank for rank, node in enumerate(self.backbone)}
        physical, issued, history = raw_prefix(data, initial, self.left)
        if issued != set(self.order[:self.left]):
            raise AssertionError('Independent fixed physical prefix has different original permutation')
        self.seed = (0, 0, history, len(physical))
        self.labels, self.replayed = {}, 0

    def done(self, node, mask, cursor):
        if self.ranks[node] < self.left:
            return True
        if node in self.local:
            return bool(mask & (1 << self.local[node]))
        return node in self.backbone_rank and self.backbone_rank[node] < cursor

    def needed(self, node, mask, cursor):
        # All true future DATA consumers: unfinished mobile, backbone, suffix.
        return any(not self.done(user, mask, cursor) for user in self.users[node])

    def roles(self, mask, cursor, ring):
        latest = {identity: offset for offset, identity in enumerate(ring) if identity is not None}
        return tuple(sorted((identity, len(ring) - offset) for identity, offset in latest.items()
                            if self.needed(identity, mask, cursor)))

    def advance(self, state, node):
        mask, cursor, history, g = state
        if self.done(node, mask, cursor) or any(not self.done(dep, mask, cursor) for dep in self.deps[node]):
            raise AssertionError('Original emitted twice or before data/hazard predecessor')
        if node in self.local:
            after_mask, after_cursor = mask | (1 << self.local[node]), cursor
        else:
            if cursor >= len(self.backbone) or self.backbone[cursor] != node:
                raise AssertionError('Backbone skipped/reordered or suffix emitted inside region')
            after_mask, after_cursor = mask, cursor + 1
        ring, rotations = list(history), 0
        last = {src for src in self.args[node] if not self.needed(src, after_mask, after_cursor)}
        while len(ring) >= self.width:
            oldest = ring[0]
            sole = oldest not in ring[1:]
            if oldest is None or not sole or not self.needed(oldest, mask, cursor) or oldest in last:
                break
            if rotations >= self.width:
                raise AssertionError('Physical ring cannot retain true future data identity')
            ring = (ring + [oldest])[-self.width:]
            rotations += 1
            g += 1
        if any(src not in ring for src in self.args[node]):
            raise AssertionError('Original ordered argument absent from physical window')
        # Choosing latest operands is checked through the physical ring, not by
        # copying production age dictionaries or next-state logic.
        distances = [len(ring) - max(index for index, identity in enumerate(ring) if identity == src) for src in self.args[node]]
        if any(not 1 <= distance <= self.width for distance in distances):
            raise AssertionError('Physical original operand outside W')
        before_roles = self.roles(mask, cursor, ring)
        ring = tuple((ring + [None if self.rows[node]['op'] == 'SET' else node])[-self.width:])
        g += 1
        actual_roles = self.roles(after_mask, after_cursor, ring)
        expected = {src for src, _ in before_roles if self.needed(src, after_mask, after_cursor)}
        if self.rows[node]['op'] != 'SET' and self.needed(node, after_mask, after_cursor):
            expected.add(node)
        if {src for src, _ in actual_roles} != expected:
            raise AssertionError('Original emission lost a future suffix/backbone/mobile identity')
        return after_mask, after_cursor, ring, g

    def accept(self, record):
        kind = record['kind']
        if kind == 'header':
            if record['region'] != {'L': self.left, 'R': self.right, 'mobile': list(self.members)}:
                raise AssertionError('Different mobile region header')
            return
        version = record['label_version']
        if kind == 'immutable_label':
            parent = record['predecessor_label']
            if parent is None:
                if record['action'] is not None:
                    raise AssertionError('Seed has an action')
                state = self.seed
            else:
                if parent not in self.labels or parent >= version:
                    raise AssertionError('Missing/cyclic/mutated immutable predecessor')
                state = self.advance(self.labels[parent], record['action'])
            if version in self.labels:
                raise AssertionError('Immutable label repeated')
            self.labels[version] = state
        else:
            if kind not in ('open', 'unfinished_expansion') or version not in self.labels:
                raise AssertionError('Unknown frontier reference')
            state = self.labels[version]
        mask, cursor, ring, g = state
        if record['done_mask'] != mask or record['backbone_cursor'] != cursor:
            raise AssertionError('Full completed state/cursor mismatch')
        if tuple(tuple(pair) for pair in record['roles']) != self.roles(mask, cursor, ring):
            raise AssertionError('Independent actual physical roles/ages disagree')
        if record['g'] != g or record['h'] != self.n - self.left - mask.bit_count() - cursor:
            raise AssertionError('Whole original+COPY g/h disagree')
        self.replayed += 1
