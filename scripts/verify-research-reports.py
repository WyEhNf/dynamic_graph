"""Compile standalone reports twice and render every page for visual QA.

This is document validation, not a solver benchmark. Sources are never edited.
Inspect the PNGs before marking a report visually reviewed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
from PIL import Image, ImageOps, ImageDraw


PROJECTS={11:'11-context-governance',18:'18-isa-scheduler',19:'19-dynamic-graph',27:'27-aicore-streams'}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--projects',nargs='+',type=int,default=list(PROJECTS))
    args=parser.parse_args(); root=Path(__file__).resolve().parents[1]
    xelatex=shutil.which('xelatex') or r'E:\texlive\2025\bin\windows\xelatex.exe'
    renderer=shutil.which('pdftoppm')
    if not renderer: raise RuntimeError('pdftoppm is required for visual review')
    for number in args.projects:
        project=root/'projects'/PROJECTS[number]; stem=f'project{number}-research'
        source=project/'reports'/f'{stem}.tex'; output=root/'outputs'/'report-qa'/str(number)
        output.mkdir(parents=True,exist_ok=True); start=time.time()
        source_digest=hashlib.sha256(source.read_bytes()).hexdigest()
        for run in range(2):
            result=subprocess.run([xelatex,'-interaction=nonstopmode','-halt-on-error','-output-directory=reports',f'reports/{stem}.tex'],
                                  cwd=project,capture_output=True,timeout=60)
            (output/f'compile-{run+1}.txt').write_bytes(result.stdout+result.stderr)
            if result.returncode: raise RuntimeError(f'{number}: compile failed; see {output}')
        log=(project/'reports'/f'{stem}.log').read_text(encoding='utf-8',errors='replace')
        warnings=[line.strip() for line in log.splitlines()
                  if 'Overfull' in line or 'undefined' in line.lower()
                  or 'Missing character' in line or 'LaTeX Warning' in line
                  or ('Package ' in line and ' Warning' in line)]
        pdf=project/'reports'/f'{stem}.pdf'
        if hashlib.sha256(source.read_bytes()).hexdigest()!=source_digest:
            raise RuntimeError(f'{number}: source changed while compiling; rerun after the report update')
        for previous in [*output.glob('page-*.png'),*output.glob('contact-*.png')]:
            if previous.resolve().parent != output.resolve(): raise RuntimeError('invalid generated-page path')
            previous.unlink()
        subprocess.run([renderer,'-r','110','-png',str(pdf),str(output/'page')],check=True,capture_output=True,timeout=60)
        pages=sorted(output.glob('page-*.png'))
        # Contact sheets are for overview; full-resolution pages remain saved.
        for begin in range(0,len(pages),4):
            canvas=Image.new('RGB',(1440,2110),'#d9dce1'); draw=ImageDraw.Draw(canvas)
            for offset,page in enumerate(pages[begin:begin+4]):
                with Image.open(page) as loaded:
                    preview=ImageOps.contain(loaded.convert('RGB'),(700,1000))
                left=20+(offset%2)*720; top=35+(offset//2)*1040
                canvas.paste(preview,(left,top)); draw.text((left,top-20),page.name,fill='black')
            canvas.save(output/f'contact-{begin//4+1}.png')
        metadata={'project':number,'source':str(source),'source_sha256':source_digest,
                  'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pages':len(pages),'warnings':warnings,
                  'compile_render_wall_seconds':time.time()-start,'visual_review':'pending human/agent PNG inspection'}
        (output/'validation.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(metadata,ensure_ascii=False),flush=True)


if __name__=='__main__': main()
