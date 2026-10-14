"""Persist every paired request and session totals without averaging ratios."""
import json
import math
from pathlib import Path
import sqlite3
import statistics
import time
from contextlib import contextmanager


class SessionMetrics:
    def __init__(self, database):
        database=Path(database); database.parent.mkdir(parents=True,exist_ok=True)
        self.database=str(database)
        with self.connect() as connection:
            connection.execute('PRAGMA journal_mode=WAL')
            connection.execute('''CREATE TABLE IF NOT EXISTS requests (
                session TEXT NOT NULL, request TEXT NOT NULL, payload TEXT NOT NULL,
                recorded REAL NOT NULL, PRIMARY KEY(session,request))''')

    @contextmanager
    def connect(self):
        connection=sqlite3.connect(self.database,timeout=30)
        try:
            with connection:
                yield connection
        finally:
            # sqlite's own context manager commits/rolls back but does not close
            # the handle. Closing is needed for Windows cleanup and long runs.
            connection.close()

    def record_pair(self, session, request, *, baseline_tokens, compressed_tokens,
                    baseline_ttft_ms, compressed_ttft_ms, baseline_correct,
                    compressed_correct, importance_ms, governance_ms, provenance=None):
        if not session or not request: raise ValueError('session and request identifiers are required')
        if (isinstance(baseline_tokens,bool) or isinstance(compressed_tokens,bool)
            or not isinstance(baseline_tokens,int) or not isinstance(compressed_tokens,int)
            or baseline_tokens<=0 or compressed_tokens<0):
            raise ValueError('actual token counts must be nonnegative integers with positive baseline')
        if not all(math.isfinite(value) and value>=0 for value in
                   [baseline_ttft_ms,compressed_ttft_ms,importance_ms,governance_ms]):
            raise ValueError('timings must be finite and nonnegative')
        if baseline_ttft_ms==0: raise ValueError('baseline TTFT must be positive')
        if type(baseline_correct) is not bool or type(compressed_correct) is not bool:
            raise ValueError('functional outcomes must be measured booleans')
        data=dict(baseline_tokens=baseline_tokens,compressed_tokens=compressed_tokens,
                  baseline_ttft_ms=baseline_ttft_ms,compressed_ttft_ms=compressed_ttft_ms,
                  baseline_correct=baseline_correct,compressed_correct=compressed_correct,
                  importance_ms=importance_ms,governance_ms=governance_ms,provenance=provenance)
        # Duplicate IDs fail rather than silently double-counting or overwriting
        # an earlier measured result. SQLite transactions serialize writers.
        with self.connect() as connection:
            connection.execute('INSERT INTO requests VALUES (?,?,?,?)',
                               (str(session),str(request),json.dumps(data,ensure_ascii=False),time.time()))

    def summary(self, session):
        with self.connect() as connection:
            rows=connection.execute('SELECT request,payload FROM requests WHERE session=? ORDER BY request',(str(session),)).fetchall()
        values=[json.loads(row[1]) for row in rows]
        if not values: return {'session':str(session),'requests':0,'quality_gate_passed':None}
        baseline=sum(x['baseline_tokens'] for x in values)
        compressed=sum(x['compressed_tokens'] for x in values)
        regressions=[request for (request,_),value in zip(rows,values) if value['baseline_correct'] and not value['compressed_correct']]
        baseline_pass=sum(x['baseline_correct'] for x in values)
        compressed_pass=sum(x['compressed_correct'] for x in values)
        return {'session':str(session),'requests':len(values),
                'baseline_tokens_total':baseline,'compressed_tokens_total':compressed,
                'aggregate_compression_ratio':1-compressed/baseline,
                'baseline_correct':baseline_pass,'compressed_correct':compressed_pass,
                'paired_regressions':regressions,
                'quality_gate_passed':baseline_pass>0 and not regressions and compressed_pass>=baseline_pass,
                'all_compressed_correct':compressed_pass==len(values),
                'median_request_ttft_reduction':statistics.median(1-x['compressed_ttft_ms']/x['baseline_ttft_ms'] for x in values),
                'importance_max_ms':max(x['importance_ms'] for x in values),
                'governance_total_ms':sum(x['governance_ms'] for x in values),
                'measurement_scope':'Weighted actual prompt-token totals; per-request paired TTFT; functional outcomes supplied by trusted evaluator.'}
