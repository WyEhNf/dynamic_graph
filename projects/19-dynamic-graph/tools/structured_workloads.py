"""Explicit SPD workload families; structured families stay separately labelled."""
from array import array
from pathlib import Path
import struct

def make_workload(path,sizes,kind,width=7,mode='normal'):
    if kind not in('band','toeplitz','low-rank'):raise ValueError('unknown workload')
    with Path(path).open('wb')as stream:
        stream.write(struct.pack('<I',len(sizes)))
        for n in sizes:
            stream.write(struct.pack('<I',n))
            scale=2.0**(-1030 if mode=='subnormal'else 900 if mode=='large'else 0)
            if kind=='band':
                for i in range(n):
                    row=array('d',[0.0])*n
                    for j in range(1-i%2,n,2):row[j]=-0.0
                    for j in range(max(0,i-width),min(n,i+width+1)):
                        if i==j:value=float(width+3)*scale
                        else:
                            base=(((min(i,j)*1315423911)^(max(i,j)*2654435761)^91)%17-8)/256.0
                            if base==0:value=-0.0 if(i+j)%2 else 0.0
                            else:value=base*(2.0**-600 if mode=='tiny'else scale)
                        row[j]=value
                    stream.write(row.tobytes())
            elif kind=='toeplitz':
                correlation=[(-0.9)**distance for distance in range(n)]
                for i in range(n):stream.write(array('d',(correlation[abs(i-j)]for j in range(n))).tobytes())
            else:
                components=[tuple((((i+offset)*1315423911^91)%17-8)/16.0 for offset in(0,3,11))for i in range(n)]
                for i in range(n):
                    row=array('d',(sum(x*y for x,y in zip(components[i],components[j]))+(4.0+i%13 if i==j else 0.0)for j in range(n)))
                    stream.write(row.tobytes())
