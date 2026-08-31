# Quick Task 260831-tnv Summary

## Completed

- Updated the Dify retrieval sanitizer to accept the actual Knowledge Retrieval wrapper `{ "result": [...] }`.
- Preserved support for the existing `records` wrapper, serialized JSON, and bare lists.
- Added a regression test using the real workflow result shape with metadata, source URL, and locator.

## Verification

- `pytest -q tests/platform/test_dify_dsl.py`: 26 passed.
- `ruff check tests/platform/test_dify_dsl.py`: passed.
- Authoritative DSL YAML parse: passed; 9 workflow nodes detected.
- GitHub `origin/master`: matches commit `0f8136122225f1c32fce6b745b8acc5d6377287d`.

## Remaining manual step

Re-import and publish `platform/dify/app.dsl.yml` in Dify, then rerun the same case. The expected result is that valid Knowledge Retrieval records populate `retrieval_trace.hits` instead of being discarded as empty.
