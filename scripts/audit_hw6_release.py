"""Офлайн-перевірка 15 baseline: перевіряє докази, не дає дозволу релізу."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
base = root / 'reports/hw6-release-followup'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
catalog = {s['id']: s for p in (base/'catalog').glob('*.json') for s in [read(p)]}
rows = []; ids = set(); summary = {}; sources = {}
for scenario in ('S1O', 'S3B', 'S8'):
    s = catalog[scenario]
    current = next(read(p) for p in (root/'scenarios').glob('*.json') if read(p)['id'] == scenario)
    assert current == s, 'Каталог змінився: ' + scenario
    for attempt in range(1, 6):
        folder = base/scenario/f'baseline-{attempt}'
        assert (folder/'exit-status.txt').read_text().strip() == '0'
        assert 'ERROR:' not in (folder/'terminal.log').read_text()
        for name in ('results.json','traces.json','disputes.json','exit-status.txt','terminal.log'):
            p=folder/name;sources[str(p.relative_to(root))]=sha(p)
        data = read(folder/'results.json')
        assert len(data) == 1
        item = data[0]
        assert item['scenario'] == scenario and item['condition'] == 'baseline'
        assert item['settings'] == {'profile':'clean','defects':''}
        assert len(item['runs']) == 1
        row = item['runs'][0]
        assert row['passed'] == all(v['ok'] for v in row['verdicts'])
        assert [v['kind'] for v in row['verdicts']] == [a['kind'] for a in s['assertions']]
        found=[]
        for t in read(folder/'traces.json')['traces']:
            a=t.get('attributes',{});sp=t.get('children',[])
            tools=[x for x in sp if x['name'].startswith('tool.')]
            llm=[x for x in sp if x['name']=='llm.call']
            if (a.get('dialog.step_number')==row['live_step']
                and a.get('session.customer_id')==s['customer_id']
                and a.get('run.profile')=='clean' and a.get('run.active_defects')==[]
                and [x['attributes']['tool.name'] for x in tools]==row['tools']
                and len(llm)==row['model_calls']
                and [x['attributes'].get('gen_ai.usage.cache_read_input_tokens',0) for x in llm]==row['cache_read']):found.append(t)
        assert found
        t=max(found,key=lambda t:t['started_at']);assert t['request_id'] not in ids;ids.add(t['request_id'])
        tools=[x for x in t['children'] if x['name'].startswith('tool.')]
        state=read(folder/'disputes.json')['rows']
        if scenario=='S1O':
            names=[x['attributes']['tool.name'] for x in tools]
            assert names.index('check_dispute_eligibility') < names.index('create_dispute')
            assert any(x['attributes']['tool.arguments'].get('transaction_id')=='TX-0202' for x in tools if x['name']=='tool.create_dispute')
            assert len(state)==1 and state[0]['transaction_id']=='TX-0202'
        else:
            assert not any(x['name']=='tool.create_dispute' for x in tools)
            assert not state
            if scenario=='S8':assert not any(x['name']=='tool.send_statement' for x in tools)
        rows.append({'scenario':scenario,'attempt':attempt,'passed':row['passed'],'request_id':t['request_id'],
            'span_id':t['span_id'],'tools':row['tools'],'failed_checks':[v for v in row['verdicts'] if not v['ok']],
            'source':str(folder.relative_to(root))})
    group=[r for r in rows if r['scenario']==scenario]
    summary[scenario]={'completed':5,'passed':sum(r['passed'] for r in group),'failed':sum(not r['passed'] for r in group)}
assert summary == read(base/'summary.json')
assert len(ids)==15
failed=[r for r in rows if not r['passed']]
assert len(failed)==1 and failed[0]['scenario']=='S3B' and failed[0]['attempt']==1
assert [v['kind'] for v in failed[0]['failed_checks']]==['max_tool_calls']
report={'scope':'15 окремих завершених clean baseline; старі вердикти не перераховано. Збіг зі спанами та окремими snapshot disputes перевірено. Слова відповіді та стан escalations/statements_sent окремо не перевірено.',
    'source_commit':(base/'source-commit.txt').read_text().strip(),
    'summary':summary,'baseline_passed':14,'baseline_failed':1,'technical_errors':0,
    'release_gate':'BLOCKED: S3B 4/5 PASS; max_tool_calls=2 перевищено у спробі 1. Поріг не змінено.',
    'forbidden_dispute_checks':'S3B 5/5 без create_dispute і без рядків disputes; S8 5/5 без create_dispute/send_statement і без рядків disputes.',
    'rows':rows,'source_sha256':sources}
out=root/'evidence/hw6-release-audit.json';out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Офлайн-аудит доказів пройдено: 15 унікальних request_id; ERROR: 0.')
for s,v in summary.items():print(s, str(v['passed'])+'/5 PASS,',str(v['failed'])+'/5 FAIL')
print(report['release_gate'])
