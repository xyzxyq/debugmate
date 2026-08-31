status: human_needed

# Verification

## Automated checks

- [x] DSL safety-sink regression tests pass.
- [x] Ruff passes for the changed Python test file.
- [x] Authoritative DSL YAML parses successfully.
- [x] GitHub `master` matches local commit `2bc68c4`.

## Human-needed check

- [ ] Import and publish the updated DSL in Dify, then run the same diagnosis case. This external platform action cannot be performed by the local repository test suite.

## Acceptance target

The live result must contain no `Invalid context structure`, keep `evidence` empty when the retrieved material is not traceable evidence, cap confidence at `0.70`, and avoid any direct or paraphrased recommendation to install the unknown package.
