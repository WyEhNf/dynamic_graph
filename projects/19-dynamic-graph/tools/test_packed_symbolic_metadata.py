"""Presence, literal type, full audit graph and malformed wire contracts."""
import copy,json,random,unittest,tempfile,os
from pathlib import Path
from packed_symbolic_metadata import pack_records,unpack_records,pack_symbols,unpack_symbols

class PackedContracts(unittest.TestCase):
    def test_complete_compressed_candidate_selection(self):
        from analyze_source import PreparedSource
        from metadata_container import encode,decode
        project=Path(__file__).resolve().parents[1]
        for name,fn in [('cholesky_reference.c','cholesky_reference'),
                        ('official_naive_transcribed.c','cholesky'),('cholesky_blocked.c','cholesky_blocked')]:
            with tempfile.TemporaryDirectory(prefix='packed-selector-') as directory:
                root=Path(directory);prepared=PreparedSource(project/'fixtures'/name,os.environ.get('CHOL_TEST_CLANG','clang'))
                candidates=[]
                for schema in (2,3):
                    for mode in ('dag','table','expanded','packed'):
                        path=root/f'{schema}-{mode}.meta'
                        prepared.emit(path,function=fn,metadata_schema=schema,symbolic_format=mode,emit_ir=False)
                        raw=path.read_bytes();container=encode(raw)
                        self.assertEqual(decode(container),raw)
                        candidates.append((schema,mode,raw,container))
                expected=min(candidates,key=lambda x:(len(x[3]),x[0],('dag','table','expanded','packed').index(x[1])))
                out=root/'minimum.meta'
                analysis=prepared.emit(out,function=fn,smallest_metadata=True,compress_metadata=True,emit_ir=False)
                self.assertEqual(out.read_bytes(),expected[3])
                self.assertEqual(decode(out.read_bytes()),expected[2])
                self.assertEqual(len(analysis['encoding_candidates']),8)

    def test_golden(self):
        source=[{'id':0,'kind':'for','parent':None},{'id':1,'kind':'while','parent':0}]
        self.assertEqual(pack_records(source),[[0,1,4],7,[[0,0,None],[1,1,0]]])
        self.assertEqual(unpack_records(pack_records(source)),source)
        pool=[['var','n'],['const',3],['add',0,1]]
        wire=pack_symbols(pool,source,[])
        self.assertEqual(wire[0],['var','const','add'])
        self.assertEqual(wire[1],[[0,'n'],[1,3],[2,0,1]])
        self.assertEqual(unpack_symbols(*wire),(pool,source,[]))

    def test_presence_literal_types(self):
        randomizer=random.Random(190034)
        keys=['id','kind','mode','array','parent','condition','loop_ids','unknown']
        literals=[None,True,False,0,1,-1,'for','read','input','unknown',['=',0],{},[1,None]]
        for case in range(500):
            records=[{k:copy.deepcopy(randomizer.choice(literals)) for k in keys if randomizer.randrange(3)}
                     for _ in range(randomizer.randrange(12))]
            restored=unpack_records(json.loads(json.dumps(pack_records(records))))
            # JSON serialization distinguishes bool/int and absent/null.
            self.assertEqual(json.dumps(restored,sort_keys=True),json.dumps(records,sort_keys=True),case)

    def test_invalid_records(self):
        malformed=[None,[],[[],0],[[0,0],3,[[0,1]]],[[True],1,[[0]]],
                   [[99],1,[[0]]],[['id'],1,[[0]]],[[0],True,[[0]]],
                   [[0],2,[[0]]],[[0],1,[[]]],[[0],None,[[1,[0,1]]]],
                   [[1],1,[[99]]],[[1],1,[[True]]],[[1],1,[[['=',0,1]]]]]
        for wire in malformed:
            with self.assertRaises(ValueError,msg=repr(wire)):unpack_records(wire)

    def test_invalid_operators(self):
        for ops,pool in [(['a','a'],[]),([True],[]),(['a'],[[True]]),(['a'],[[1]]),(['a'],[[]]),(['a'],None)]:
            with self.assertRaises(ValueError):unpack_symbols(ops,pool,[[],None,[]],[[],None,[]])

if __name__=='__main__':unittest.main()
