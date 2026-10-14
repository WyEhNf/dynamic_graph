from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import json

p = next(Path('..').glob('*.xlsx'))
ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with ZipFile(p) as z:
    root = ET.fromstring(z.read('xl/workbook.xml'))
    sheets = [x.attrib['name'] for x in root.find('s:sheets', ns)]
    tables = [n for n in z.namelist() if n.startswith('xl/tables/table') and n.endswith('.xml')]
    results = []
    for n in ['xl/worksheets/sheet1.xml', 'xl/worksheets/sheet2.xml', 'xl/worksheets/sheet3.xml']:
        r = ET.fromstring(z.read(n))
        panes = [x.attrib for x in r.findall('.//s:pane',ns)]
        errors = [x.attrib for x in r.findall('.//s:c',ns) if x.attrib.get('t')=='e']
        results.append({'sheet':n,'panes':panes,'error_cells':errors})
        assert not errors
    assert len(sheets)==3 and len(tables)==2
    for r in results[1:]:
        assert r['panes'][0]['xSplit']=='3' and r['panes'][0]['ySplit']=='5'
    print(json.dumps({'sheets':sheets,'filter_tables':len(tables),'results':results},ensure_ascii=False))
