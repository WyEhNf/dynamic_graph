"""DYNCHZ01: full Metadata bytes in one bounded RFC1950 zlib stream."""
import struct,zlib
MAGIC=b'DYNCHZ01'
LIMIT=16*1024*1024

def encode(data):
    if not 0<len(data)<=LIMIT:raise ValueError('compressed Metadata raw length out of bounds')
    payload=zlib.compress(data,9)
    if not 6<=len(payload)<=LIMIT:raise ValueError('compressed Metadata payload length out of bounds')
    return MAGIC+struct.pack('<II',len(data),len(payload))+payload

def decode(data):
    if len(data)<16 or data[:8]!=MAGIC:raise ValueError('invalid compressed Metadata header')
    raw,size=struct.unpack('<II',data[8:16])
    if not 0<raw<=LIMIT or not 6<=size<=LIMIT or len(data)!=16+size:raise ValueError('compressed Metadata size mismatch')
    # RFC1950 only, no raw DEFLATE/gzip/dictionary/concatenation/trailing bytes.
    decoder=zlib.decompressobj(15)
    try:output=decoder.decompress(data[16:],raw+1)
    except zlib.error as error:raise ValueError('invalid compressed Metadata stream') from error
    if len(output)!=raw or not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:raise ValueError('compressed Metadata stream/length mismatch')
    return output
