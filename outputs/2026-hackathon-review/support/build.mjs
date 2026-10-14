import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
import { records, categories, generalNotes as notes } from './data.mjs';
const out = path.resolve('..');
const expected = Array.from({length:34},(_,i)=>i+1);
if (JSON.stringify(records.map(r=>r.id))!==JSON.stringify(expected)) throw new Error('编号不完整');
const required = ['title','official','analysis','stack','software','hardware','cpu','memory','storage','gpu','device','env','data','deliverable','unknown','source','category'];
for(const r of records) for(const k of required) if(!r[k]) throw new Error(`${r.id}缺少${k}`);
if(new Set(categories.flatMap(c=>c[1])).size!==34 || categories.reduce((s,c)=>s+c[1].length,0)!==34) throw new Error('分类覆盖不正确');
await fs.mkdir(out,{recursive:true});
const wb = Workbook.create();
const overview = wb.worksheets.add('方向总览');
const tech = wb.worksheets.add('技术分析');
const res = wb.worksheets.add('资源清单');
const cols = n => {let s=''; for(;n;n=Math.floor((n-1)/26)) s=String.fromCharCode(65+(n-1)%26)+s;return s;};
function base(sheet,endRow,endCol){
 sheet.showGridLines=false;
 sheet.getRange(`A1:${cols(endCol)}${endRow}`).format={font:{name:'Arial',size:10,color:'#243247'},verticalAlignment:'center'};
 sheet.getRange(`A2:${cols(endCol)}2`).format.font={name:'Arial',size:14,bold:true,color:'#14263E'};
 sheet.getRange(`A2:${cols(endCol)}2`).format.rowHeight=27;
 sheet.getRange(`A3:${cols(endCol)}3`).format.borders={bottom:{style:'thin',color:'#8E9AAD'}};
}
function table(sheet,headers,rows,widths,name){
 const last=5+rows.length, end=cols(headers.length);
 base(sheet,last,headers.length);
 sheet.getRange(`A5:${end}${last}`).values=[headers,...rows];
 const t=sheet.tables.add(`A5:${end}${last}`,true,name); t.style='TableStyleLight9'; t.showFilterButton=true;
 sheet.getRange(`A5:${end}5`).format={fill:'#263F60',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true,rowHeight:32};
 sheet.getRange(`A6:${end}${last}`).format.wrapText=true;
 sheet.getRange(`A6:${end}${last}`).format.verticalAlignment='top';
 widths.forEach((w,i)=>sheet.getRange(`${cols(i+1)}1:${cols(i+1)}${last}`).format.columnWidthPx=w);
 sheet.getRange(`A6:A${last}`).setNumberFormat('0');
 sheet.getRange(`A6:A${last}`).format.horizontalAlignment='right';
 for(let i=0;i<rows.length;i++){
  let lines=1;
  rows[i].forEach((v,j)=>{
   // conservative Chinese/Latin line-width estimate, with extra padding for word wrapping
   const weight=Array.from(String(v)).reduce((s,c)=>s+(/[\u2e80-\uffff]/.test(c)?13:7),0);
   lines=Math.max(lines,Math.ceil(weight/Math.max(30,widths[j]-24))+1);
  });
  sheet.getRange(`A${i+6}:${end}${i+6}`).format.rowHeightPx=Math.max(70,lines*19+22);
 }
 sheet.freezePanes.freezeRows(5); sheet.freezePanes.freezeColumns(3);
 return last;
}
const techHeaders=['编号','赛题','主方向','官方任务与关键要求','简要技术分析（工程判断）','建议技术栈','软件能力','硬件/架构能力','交付物','官方详情来源'];
table(tech,techHeaders,records.map(r=>[r.id,r.title,r.category,r.official,r.analysis,r.stack,r.software,r.hardware,r.deliverable,r.source]),[55,300,180,460,450,300,260,240,260,370],'TechnicalTopics');
tech.getRange('A2').values=[['2026 Hackathon 技术分析']];
tech.getRange('A4').values=[['复核日期：2026-10-10。D列为官方摘要；E–H列为工程分析。第18题正文补齐，第21题范围与10秒时限更新。']];
res.tabColor='#263F60'; tech.tabColor='#3B5C82'; overview.tabColor='#182D47';
const resHeaders=['编号','赛题','主方向','评测/部署形式','CPU：官方与开发建议','RAM：官方与开发建议','存储：官方与开发建议','GPU/NPU：必需性与建议','设备/外设','环境与权限','数据及主办方资源','待确认事项'];
table(res,resHeaders,records.map(r=>[r.id,r.title,r.category,r.mode,r.cpu,r.memory,r.storage,r.gpu,r.device,r.env,r.data,r.unknown]),[55,300,180,210,340,320,350,350,290,330,330,420],'TopicResources');
res.getRange('A2').values=[['2026 Hackathon 资源清单']];
res.getRange('A4').values=[['建议值用于原型和实验规划，并非赛事门槛。仿真中的卡数/显存不是设备需求。来源按编号见“技术分析”。']];
res.getRange('D6:D39').conditionalFormats.add('containsText',{text:'正文缺失',format:{fill:'#FFF0D8',font:{color:'#8C4800',bold:true}}});
base(overview,38,4);
const overviewWidths=[360,80,340,610]; overviewWidths.forEach((w,i)=>overview.getRange(`${cols(i+1)}1:${cols(i+1)}38`).format.columnWidthPx=w);
overview.getRange('A2').values=[['2026 Hackathon 赛题方向与资源总览']];
overview.getRange('A4').values=[['复核日期：2026-10-10。按官方编号归类；18题新增间接索引/COPY要求，21题更新规模与时限。']];
overview.getRange('A5:D13').values=[['主方向','题数','官方编号','技术主题'],...categories.map(c=>[c[0],null,c[1].join('、'),c[2]])];
for(let i=0;i<categories.length;i++) overview.getRange(`B${i+6}`).formulas=[[`=COUNTIFS('技术分析'!$C$6:$C$39,A${i+6})`]];
overview.getRange('A14').values=[['合计']]; overview.getRange('B14').formulas=[['=SUM(B6:B13)']];
overview.getRange('A5:D5').format={fill:'#263F60',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',rowHeight:27};
overview.getRange('A6:D14').format.rowHeight=28;
overview.getRange('B6:B14').setNumberFormat('0');
overview.getRange('B6:B14').format.horizontalAlignment='right';
overview.getRange('A14:D14').format={font:{name:'Arial',size:10,bold:true},borders:{top:{style:'thin',color:'#8E9AAD'}}};
const summaryRows=[
 ['阅读情况','34题目录与详情重新访问；18完整正文已补齐；22、23、31图片说明沿用10月9日补读。'],
 ['估算口径','官方要求与开发建议分开标注。CPU、RAM、SSD和显存建议是原型规划值，并非赛事门槛。'],
 ['资源获取','11/18/19/27本地基座已运行验证；官方SDK/数据包仍待取得，基座验证不是赛事成绩。'],
 ['CPU仿真','17、20、21、22、24、25、27、29可先用CPU完成核心评测，不需购买仿真中的卡数或HBM。'],
 ['实物资源','8需GPU实验；9、10、12、30涉及目标端；4、7、33需ARM环境；14需评估全量数据和NVMe。'],
 ['规则待确认','4、6、7、12、19、21、22、34存在冲突或尚未定稿的口径，详细问题保留在资源清单中。'],
 ['算力时长','数据量和训练轮次不充分时，GPU小时、费用与训练时长不可可靠估算。先测基线，再按规模扩算。']
];
overview.getRange('A17').values=[['阅读范围与资源解释']]; overview.getRange('A17').format.font={name:'Arial',size:10,bold:true};
for(let i=0;i<summaryRows.length;i++){
 const rr=18+i;overview.getRange(`A${rr}`).values=[[summaryRows[i][0]+'：'+summaryRows[i][1]]];
 overview.getRange(`A${rr}:D${rr}`).format.rowHeight=26;
 overview.getRange(`A${rr}:D${rr}`).format.wrapText=false;
}
wb.recalculate();
const countVals=overview.getRange('B6:B14').values.flat();
const want=[4,5,2,5,3,8,6,1,34];
if(JSON.stringify(countVals)!==JSON.stringify(want)) throw new Error('分类计数公式不正确：'+JSON.stringify(countVals));
const inspected=await wb.inspect({kind:'table',range:'方向总览!A5:D14',include:'values,formulas',tableMaxRows:10,tableMaxCols:4,maxChars:5000});
console.log(inspected.ndjson);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},maxChars:2500});
console.log(errors.ndjson);
const previews=[['方向总览','A1:D24','overview'],['技术分析','A1:F8','technical-left'],['技术分析','G5:J8','technical-right'],['资源清单','A1:G8','resources-left'],['资源清单','H5:L8','resources-right']];
for(const [sheetName,range,file] of previews){
 const blob=await wb.render({sheetName,range,scale:1.3,format:'png'});
 await fs.writeFile(`${file}.png`,new Uint8Array(await blob.arrayBuffer()));
}
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(path.join(out,'赛题与资源清单.xlsx'));
// Offline reading report. No external libraries, services, fonts or image requests.
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const paragraphs = ['official','analysis','stack','software','hardware','deliverable'];
const labels={official:'官方任务与关键要求',analysis:'简要技术分析（工程判断）',stack:'建议技术栈',software:'软件能力',hardware:'硬件与架构能力',deliverable:'交付物'};
const resourceKeys=['cpu','memory','storage','gpu','device','env','data','unknown'];
const resourceLabels={cpu:'CPU',memory:'RAM',storage:'存储',gpu:'GPU / NPU',device:'设备与外设',env:'环境与权限',data:'数据与主办方资源',unknown:'待确认事项'};
const cards=records.map(r=>`<article id="topic-${r.id}" data-category="${esc(r.category)}" data-search="${esc(Object.values(r).join(' '))}"><div class="meta">${esc(r.category)} <span>${esc(r.mode)}</span></div><h2>${r.id}．${esc(r.title)}</h2>${r.id===18?'<p class="warning">更新：2026-10-10 09:18正文已补齐。以间接索引窗口和COPY占比为核心目标；官方示意语义待确认。</p>':''}${paragraphs.map(k=>`<section><h3>${labels[k]}</h3><p>${esc(r[k])}</p></section>`).join('')}<h3>资源清单</h3><p class="note">带“官方”的值来自题面；带“建议/暂拟”的值是开发规划估算。主机RAM、GPU显存和仿真容量分开理解。</p><table class="resources"><tbody>${resourceKeys.map(k=>`<tr><th>${resourceLabels[k]}</th><td${k==='unknown'&&r.issue?' class="uncertain"':''}>${esc(r[k])}</td></tr>`).join('')}</tbody></table><p class="source">来源：<a href="${r.source}" target="_blank" rel="noopener">查思派第${r.id}题官方详情</a>，复核于2026-10-10（图片说明补读于10月9日）。</p><a class="back" href="#top">返回总览</a></article>`).join('');
const toc=categories.map(c=>`<tr><th>${esc(c[0])}</th><td>${c[1].length}</td><td>${c[1].map(id=>`<a href="#topic-${id}">${id}</a>`).join('、')}</td><td>${esc(c[2])}</td></tr>`).join('');
const html=`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>2026 Hackathon 34题技术分析与资源清单</title><style>
:root{color-scheme:light;--ink:#223249;--accent:#234f86;--line:#d7dfe8}*{box-sizing:border-box}body{margin:0;background:#f4f6f9;color:var(--ink);font:16px/1.8 'Microsoft YaHei','Noto Sans CJK SC',Arial,sans-serif}main{max-width:1120px;margin:auto;padding:42px 24px 80px}header,article{background:#fff;border:1px solid var(--line);border-radius:12px;padding:32px;margin-bottom:26px}h1{font-size:30px;line-height:1.45;margin:0 0 12px}h2{font-size:25px;line-height:1.5;margin:8px 0 24px}h3{font-size:17px;margin:20px 0 6px;color:var(--accent)}p{margin:0 0 12px}a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}table{border-collapse:collapse;width:100%;margin:18px 0}th,td{padding:13px 16px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}thead{background:#eef3f9}.resources th{width:160px;background:#f8fafc;white-space:nowrap}.resources td{overflow-wrap:anywhere}.meta{font-size:14px;color:#4d6180}.meta span{margin-left:16px}.note,.source,.back{font-size:14px;color:#58687d}.warning,.uncertain{background:#fff3dc;color:#825116}.warning{padding:16px;border-radius:6px}.controls{position:sticky;top:0;background:#f4f6f9f5;padding:12px 0;display:flex;gap:12px;z-index:1;margin:12px 0 22px}input,select{font:inherit;padding:10px 14px;border:1px solid #b9c6d7;border-radius:6px;background:white}input{flex:1;min-width:0}select{max-width:310px}.hidden{display:none}section p{margin:0}.summary{padding:16px;background:#eef3f9;border-radius:6px}.counts{font-size:14px;margin:0 0 18px}.empty{display:none;padding:20px}footer{font-size:14px;color:#58687d}.toc-wrap{overflow:auto}.toc td:nth-child(3){white-space:nowrap}article{scroll-margin-top:85px}@media(max-width:700px){main{padding:20px 12px}header,article{padding:20px}h1{font-size:25px}h2{font-size:22px}.controls{flex-direction:column}.resources th{width:100px;white-space:normal}th,td{padding:10px}select{max-width:100%}}@media print{body{background:white}main{max-width:none;padding:0}.controls,.back,.counts{display:none}header,article{border:0;margin:0 0 25px;padding:0;border-radius:0}article{break-before:page}section,.resources tr{break-inside:avoid}a{color:inherit}.hidden{display:block}}
</style></head><body><main id="top"><header><h1>2026 Hackathon：34道赛题技术分析与资源清单</h1><p class="note">依据查思派官网逐题读取，复核日期：2026年10月10日。</p><p>${esc(notes.scope)}</p><p class="summary">${esc(notes.estimates)}</p><h3>方向分类</h3><div class="toc-wrap"><table class="toc"><thead><tr><th>方向</th><th>题数</th><th>官方编号</th><th>主题</th></tr></thead><tbody>${toc}<tr><th>合计</th><td>34</td><td colspan="2">每题仅归入一个主方向</td></tr></tbody></table></div><h3>资源判断</h3><p>${esc(notes.resources)}</p><h3>信息完整性</h3><p>${esc(notes.missing)}</p><p>${esc(notes.evidence)}</p><p class="source">总入口：<a href="https://www.chaspark.com/#/s/2026Hackathon?multi=zh" target="_blank" rel="noopener">2026 Hackathon 官方专题</a>。每题末尾附官方详情链接。</p></header><div class="controls"><input id="search" aria-label="按编号、名称、技术或资源搜索" placeholder="搜索编号、题名、技术栈、设备…"><select id="category" aria-label="筛选方向"><option value="">全部方向（34题）</option>${categories.map(c=>`<option>${esc(c[0])}</option>`).join('')}</select></div><p class="counts" id="counts">显示34题</p><p class="empty" id="empty">没有匹配赛题，请调整搜索条件。</p>${cards}<footer>官方限制、目标指标和开发建议应分开使用。对未发布或相互冲突的规则，先获取最终SDK与评测口径再确定方案和资源。</footer></main><script>const search=document.querySelector('#search'),category=document.querySelector('#category'),articles=[...document.querySelectorAll('article')];function filter(){const q=search.value.trim().toLowerCase(),c=category.value;let n=0;articles.forEach(a=>{const ok=(!c||a.dataset.category===c)&&(!q||a.dataset.search.toLowerCase().includes(q));a.classList.toggle('hidden',!ok);if(ok)n++});document.querySelector('#counts').textContent='显示'+n+'题';document.querySelector('#empty').style.display=n?'none':'block'}search.addEventListener('input',filter);category.addEventListener('change',filter);document.querySelectorAll('.toc a').forEach(a=>a.addEventListener('click',()=>{search.value='';category.value='';filter()}));</script></body></html>`;
await fs.writeFile(path.join(out,'赛题技术分析.html'),html,'utf8');
await fs.writeFile('validation.json',JSON.stringify({records:34,categories:categories.map((c,i)=>({name:c[0],count:countVals[i],ids:c[1]})),blankBody:[],reviewDate:"2026-10-10",updatedTopics:[18,21],sources:records.map(r=>({id:r.id,url:r.source})),files:['赛题与资源清单.xlsx','赛题技术分析.html']},null,2));
console.log('已生成34题、8方向、3个工作表；分类计数和字段检查通过。');
