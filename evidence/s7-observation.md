# S7 observation

Baseline: 5 completed runs, all PASS.
D13: 4 completed runs, all FAIL.
The fifth completed D13 run is still missing.

Observed failures include forbidden get_transactions calls and/or
missing check_limits. Do not describe every failure as the same route.

HTTP 502 failures surfaced as stand HTTP 500.
Incomplete attempts are preserved separately and excluded from
completed-run rates. The source of the gateway error is unresolved.
Model experiments paused after the failed defect-5-retry attempt.
The planned five-run D13 series is not complete.
