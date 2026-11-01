# S6 observation

Baseline: PASS, one dispute for TX-0801, ACC-1009, 120 USD.
D11 condition: PASS with the same correct stored currency.

Both live calls explicitly supplied amount=120 and currency=USD.
The tool therefore bypassed the faulty currency-derivation branch.

Conclusion: this pair verifies the observed write but does not
demonstrate detection of D11. The minimal-argument path remains
uncovered. Preserve both results; do not retry for a desired failure.
