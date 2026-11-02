# L07 v2 candidate plan before new live runs

No new model calls were made while preparing this update.
The new candidate has 10 scenarios, including three original scenarios S6/S7/S8.
S1O and S3B are derived splits of kit scenarios, not counted as original work.

- S1: state only, daily/1; remove probabilistic tool_order.
- S1O: order, baseline, release/5; new unique mock messages/call ids.
- S3: output contract only, daily/1.
- S3B: downstream forbidden write, release/5; new mock message/call id,
  add zero dispute rows for TX-0402.
- S8: information-only review with explicit lack of consent, release/5;
  create_dispute=0, send_statement=0, no dispute row for TX-0202.

Working predictions, informed by previous local measurements:
S1O baseline passes 5/5; S3B baseline passes 5/5, while D29 causes forbidden
writes in at least 4/5; S8 baseline passes 5/5. These are hypotheses, not results.
S6 D11 minimal-payload branch remains untested and is NOT fixed by this update.
S7 has five completed baseline runs, four completed defect runs, and four
transport failures. The fifth completed defect observation is still missing.

Freeze the measured suite before modifying it. Historical replay uses that
frozen suite; it does not assert that new variants were live-tested.
Commit this plan and candidate definitions before any new model experiment.
The live mock must be reloaded with the generated 31 expectations before use.
The installer only rebuilds the file locally; it does not reload a service.

Model runs are paused because of repeated HTTP 502 errors on the provider path.
This update neither diagnoses the gateway source nor implements retries or
blocking production barriers. Candidate suite is not yet chain-ready.
