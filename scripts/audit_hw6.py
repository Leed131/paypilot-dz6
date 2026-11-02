"""Audit the final HW6 catalog and recorded verification, offline."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
base = root / 'reports/hw6-v3/final-verification-timeout60'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
catalog = {s['id']: s for p in (root/'scenarios').glob('*.json') for s in [read(p)]}
assert len(catalog) == 10
assert {'S6', 'S7', 'S8'} <= set(catalog)
allowed = {'tool_called', 'tool_not_called', 'tool_call_count', 'tool_order', 'tool_sequence', 'max_tool_calls', 'tool_result_schema', 'state_row', 'cache_read_min'}
for s in catalog.values():
    assert s['dimension'] and set(s['level']) <= {1,2,3,4} and s['level'], s['id']
    assert s['gate'] in {'daily','release'}
    assert s['runs'] == (1 if s['gate']=='daily' else 5)
    assert sum(bool(t.get('live')) for t in s['turns']) == 1
    assert all(c['profile']=='clean' for c in s['conditions'].values())
    assert all(a['kind'] in allowed for a in s['assertions'])
daily = {k for k,v in catalog.items() if v['gate']=='daily'}
assert daily == {'S1','S3','S4','S6'}
assert len(catalog)-len(daily) >= 2
# Metadata edits do not alter the executable scenarios that were tested.
metadata = {'title','dimension','level'}
for p in (base/'catalog').glob('*.json'):
    old=read(p); current=catalog[old['id']]
    assert {k:v for k,v in old.items() if k not in metadata} == {k:v for k,v in current.items() if k not in metadata}, old['id']
assert sha(root/'run_step.py') == sha(base/'run_step.py'), 'Tested runner differs'
spec=importlib.util.spec_from_file_location('mock_builder', root/'build_mock.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
expectations=[]
for p in sorted((root/'scenarios').glob('*.json')):
    expectations += builder.expectations_for(read(p))
assert expectations == read(root/'mock/expectations.json')
assert len(expectations) == len({e['id'] for e in expectations}) == 32
assert 'MOCKSERVER_MAX_SOCKET_TIMEOUT: "60000"' in (root/'docker-compose.yml').read_text()
rows=[]; trace_ids=set()
def children(t):
    for s in t.get('children',[]):
        yield s
        yield from children(s)
for stage in ['daily','all-baseline']:
    folder=base/stage
    assert (folder/'exit-status.txt').read_text().strip() == '0'
    assert 'ERROR:' not in (folder/'terminal.log').read_text()
    data=read(folder/'results.json')
    required=daily if stage=='daily' else set(catalog)
    baseline=[b for b in data if b['condition']=='baseline']
    assert {b['scenario'] for b in baseline} == required
    assert len(baseline) == len(required)
    assert all(len(b['runs'])==1 and b['runs'][0]['passed'] for b in baseline)
    expected_conditions={(s,c) for s in required for c in catalog[s]['conditions'] if stage=='daily' or c=='baseline'}
    assert {(b['scenario'],b['condition']) for b in data} == expected_conditions
    trees=read(folder/'traces.json')['traces']; before=float('inf'); matched=[]
    for block in reversed(data):
        s=catalog[block['scenario']]; row=block['runs'][0]
        assert row['passed'] == all(v['ok'] for v in row['verdicts'])
        assert [v['kind'] for v in row['verdicts']] == [a['kind'] for a in s['assertions']]
        assert block['settings'] == s['conditions'][block['condition']]
        found=[]
        for t in trees:
            a=t.get('attributes',{}); llm=[x for x in children(t) if x['name']=='llm.call']; tools=[x for x in children(t) if x['name'].startswith('tool.')]
            if (t['started_at']<before and a.get('dialog.step_number')==row['live_step']
                and a.get('session.customer_id')==s['customer_id']
                and set(a.get('run.active_defects',[]))==set(filter(None,block['settings'].get('defects','').split(',')))
                and [x['attributes']['tool.name'] for x in tools]==row['tools']
                and len(llm)==row['model_calls']
                and [x['attributes'].get('gen_ai.usage.cache_read_input_tokens',0) for x in llm]==row['cache_read']): found.append(t)
        assert found, (stage,block['scenario'],block['condition'])
        t=max(found,key=lambda t:t['started_at']);before=t['started_at']
        assert t['request_id'] not in trace_ids;trace_ids.add(t['request_id'])
        matched.append({'stage':stage,'scenario':s['id'],'condition':block['condition'],
            'passed':row['passed'],'request_id':t['request_id'],'live_step':row['live_step'],
            'models':sorted({x['attributes'].get('gen_ai.request.model') for x in children(t) if x['name']=='llm.call'}),
            'verdicts':row['verdicts'],'report':str((folder/'results.json').relative_to(root)),
            'report_sha256':sha(folder/'results.json'),'trace_sha256':sha(folder/'traces.json')})
    rows.extend(reversed(matched))
assert len(rows)==17
for scenario,kind in [('S1','state_row'),('S3','tool_result_schema'),('S6','state_row')]:
    row=next(r for r in rows if r['stage']=='daily' and r['scenario']==scenario and r['condition']=='defect')
    assert not next(v['ok'] for v in row['verdicts'] if v['kind']==kind)
report={'scope':'Offline audit of final 17 completed steps; no model calls. State checks are the recorded native-runner verdicts, not independent replay against the final table snapshot.',
    'scenarios':10,'original_scenarios':['S6','S7','S8'],'expectations':32,
    'daily_baseline':'4/4 PASS','daily_technical_errors':0,'all_baseline':'10/10 PASS',
    'final_completed_steps':17,'daily_expected_defects_detected':['D12','D29','D11'],
    'metadata_only_changes':['S1 title names step 4','S3 level corrected to exact contract [1]'],
    'rows':rows}
out=root/'evidence/hw6-final-audit.json';out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('HW6 offline audit passed: 10 scenarios; 32 expectations; 17 unique completed steps.')
print('Daily: 4/4 baseline PASS; all baseline: 10/10 PASS; D12/D29/D11 detected.')
