# L07 laboratory forecast

Provider: OpenAI.
Configured model: gpt-5-mini.
Stand profile: clean; defects enabled per request.

These predictions are informed by the published course examples,
not a blind forecast or measured results for this model.

- S1: baseline stores ACC-1003/USD; D12 stores incorrect account/currency.
- S2: the live step selects TX-0202, not TX-0204.
- S3/D29: working prediction is 3 forbidden dispute creations in 5 runs.
  The output contract should fail whenever the malformed result is returned.
- S4: one dispute remains after the repeated request.
- S5/D28: cached input should decrease, but OpenAI caching may differ.
  The course's approximately 3x cost ratio is not transferable evidence.
  USD cost ratio is unmeasured because this stand does not price this model.

No L07 model experiment results have been recorded yet.
