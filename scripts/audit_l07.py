"""Replay recorded L07 evidence offline. Run from the kit root; no model calls."""
import hashlib
import importlib.util
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
output = Path(sys.argv[2]) if len(sys.argv) > 2 else root / 'evidence/l07-audit.json'
recorded_root = root / 'evidence/l07-recorded-suite'
runner_path = recorded_root / 'run_step.py' if (recorded_root / 'run_step.py').exists() else root / 'run_step.py'
spec = importlib.util.spec_from_file_location('l07_native_runner', runner_path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
recorded = root / 'evidence/l07-recorded-suite/scenarios'
scenario_dir = recorded if recorded.exists() else root / 'scenarios'
scenarios = {s['id']: s for p in scenario_dir.glob('*.json') for s in [json.loads(p.read_text())]}

def spans(tree):
    yield tree
    for child in tree.get('children', []):
        yield from spans(child)

sessions = []
for report in sorted((root / 'reports').rglob('results.json')):
    trace_file = report.parent / 'traces.json'
    trees = json.loads(trace_file.read_text())['traces']
    state_file = report.parent / 'disputes.json'
    state = json.loads(state_file.read_text()) if state_file.exists() else None
    for block in json.loads(report.read_text()):
        scenario = scenarios[block['scenario']]
        for row in block['runs']:
            required_defects = set(filter(None, block['settings'].get('defects', '').split(',')))
            candidates = [t for t in trees
                          if t['attributes'].get('dialog.step_number') == row['live_step']
                          and t['attributes'].get('session.customer_id') == scenario['customer_id']
                          and set(t['attributes'].get('run.active_defects', [])) == required_defects]
            assert candidates, f'No live trace: {report}'
            tree = max(candidates, key=lambda t: t['started_at'])
            tool_spans = runner._tool_spans(tree)
            llm_spans = runner._llm_spans(tree)
            assert [t['attributes']['tool.name'] for t in tool_spans] == row['tools'], report
            cache = [s['attributes'].get('gen_ai.usage.cache_read_input_tokens', 0) for s in llm_spans]
            assert cache == row['cache_read'], report
            assert len(llm_spans) == row['model_calls'], report
            def recorded_state(*args, **kwargs):
                assert args[2].startswith('/api/_test/state/'), 'Unexpected access in offline replay'
                assert state is not None, f'Missing state: {report}'
                return state
            runner._call = recorded_state
            replay = [(a['kind'], *runner.check(a, tree)) for a in scenario['assertions']]
            assert [r[1] for r in replay] == [v['ok'] for v in row['verdicts']], report
            assert all(r[1] for r in replay) == row['passed'], report
            forecast_file = {'S6': 's6-forecast-commit.txt', 'S7': 's7-forecast-commit.txt'}.get(block['scenario'], 'l07-forecast-commit.txt')
            commits = root / 'evidence' / forecast_file
            forecast = commits.read_text().splitlines()
            assert datetime.fromisoformat(forecast[2]).timestamp() < tree['started_at'], 'Forecast chronology'
            rows = state['rows'] if state else []
            sessions.append({
                'report': str(report.relative_to(root)), 'scenario': block['scenario'],
                'condition': block['condition'], 'settings': block['settings'],
                'request_id': tree['request_id'], 'session_id': tree['attributes'].get('session.id'),
                'started_at_utc': datetime.fromtimestamp(tree['started_at'], __import__('datetime').timezone.utc).isoformat(),
                'passed': row['passed'], 'assertion_replay': [{'kind': k, 'passed': ok, 'detail': detail} for k, ok, detail in replay],
                'model_calls': len(llm_spans), 'cache_read': cache,
                'models': sorted({s['attributes'].get('gen_ai.request.model', '') for s in llm_spans}),
                'input_tokens': sum(s['attributes'].get('gen_ai.usage.input_tokens', 0) for s in llm_spans),
                'output_tokens': sum(s['attributes'].get('gen_ai.usage.output_tokens', 0) for s in llm_spans),
                'create_dispute_calls': [s['attributes']['tool.arguments'] for s in tool_spans if s['attributes']['tool.name'] == 'create_dispute'],
                'disputes': rows if state is not None else None,
                'forecast_commit': forecast[0],
                'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest(),
                'trace_file_sha256': hashlib.sha256(trace_file.read_bytes()).hexdigest()
            })
assert len({s['request_id'] for s in sessions}) == len(sessions), 'Duplicate live requests'
errors = []
for log in sorted((root / 'reports').rglob('terminal.log')):
    text = log.read_text()
    lines = [line for line in text.splitlines() if 'ERROR:' in line]
    if lines:
        snapshot_path = log.parent / 'traces.json'
        snapshots = json.loads(snapshot_path.read_text()).get('traces', []) if snapshot_path.exists() else []
        latest = max(snapshots, key=lambda t: t['started_at']) if snapshots else None
        errors.append({'log': str(log.relative_to(root)), 'errors': lines,
                       'latest_snapshot_request_id': latest.get('request_id') if latest else None,
                       'snapshot_is_a_completed_step_elsewhere': latest.get('request_id') in {s['request_id'] for s in sessions} if latest else False,
                       'classification': 'setup incompatibility; snapshots may be stale' if 'does not know' in text else 'incomplete transport attempt; excluded from completed-run rates'})
summary = {
    'scope': 'Offline replay of supplied reports, selected live-step spans and state snapshots. No network or model calls.',
    'completed_sessions': len(sessions),
    'groups': dict(Counter(s['scenario'] + '/' + s['condition'] for s in sessions)),
    'completed_model_calls': sum(s['model_calls'] for s in sessions),
    'recorded_completed_input_tokens': sum(s['input_tokens'] for s in sessions),
    'recorded_completed_output_tokens': sum(s['output_tokens'] for s in sessions),
    'technical_errors': errors, 'sessions': sessions
}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
print('Offline audit passed:', len(sessions), 'unique completed live steps; technical errors:', len(errors))
print(json.dumps(summary['groups'], ensure_ascii=False))
