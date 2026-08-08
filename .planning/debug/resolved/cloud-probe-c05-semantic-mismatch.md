---
status: resolved
trigger: "Published Dify workflow authenticates, uploads files, and returns outputs.diagnosis successfully, but repository cloud-probe marks all 7 capabilities fail because its initial workflow call sends only case_id/file_id, then validates the empty/unknown diagnosis against _probe_generation_request containing committed facts/evidence/category. Repair request contains only issue codes/pointers and candidate, so the workflow cannot reconstruct expected facts/evidence. Fix the local probe so C02 remains independently proven by upload and C05 invokes the formal generation request / strict DiagnosisRecord validation without falsely marking C03/C04/C06/C07 pass."
created: 2026-08-08T21:40:52+08:00
updated: 2026-08-08T22:10:00+08:00
---

## Current Focus

hypothesis: Confirmed and resolved.
test: Completed locally and against the published Dify workflow.
expecting: Achieved: exit 0, C01/C02/C05 pass, C03/C04/C06/C07 not-tested, and evidence bundle verification succeeds with zero issues.
next_action: Archive the debug session and commit the scoped fix and records.

## Symptoms

expected: cloud-probe exits 0 and reports C01, C02, C05 pass; C03, C04, C06, C07 remain not-tested when Dify auth/upload and strict structured workflow are successful.
actual: .artifacts/dify-cloud-probe/case_5a95dfcc03634caabd79e5ee4cc3d904 reports 7 fail. dify-upload.json exists. Direct /workflows/run succeeds with output key diagnosis, but local semantic validation reports evidence_set_mismatch, fact_set_mismatch, routing_mismatch.
errors: probe suppresses DifyContractError detail and emits status_counts {fail:7}. Direct run output is valid DiagnosisRecord but empty facts/evidence/category unknown because only case_id/file_id were sent.
reproduction: Load DIFY_* from Windows User environment, PYTHONPATH=current src, run worktree Python -m debugmate.cli cloud-probe --output .artifacts/dify-cloud-probe.
started: First live cloud probe after manually publishing the Dify workflow on 2026-08-08; no prior successful cloud probe claim.

## Eliminated

## Evidence

- timestamp: 2026-08-08T21:45:00+08:00
  checked: src/debugmate/probe.py request path
  found: run_cloud_probe calls backend.run_workflow with only case_id and file_id, then passes that candidate to validation against _probe_generation_request(case_id).
  implication: The cloud model never receives the facts, evidence, final routing category, knowledge build, schema version, or prompt version that local semantic validation requires.

- timestamp: 2026-08-08T21:45:00+08:00
  checked: src/debugmate/diagnosis/generation.py formal candidate-generation path
  found: DiagnosisGenerator.generate without initial_candidate sends request_kind=candidate_generation and the full generation_request before strict schema and semantic validation.
  implication: The probe bypasses the repository's formal generation contract even though that path already exists.

- timestamp: 2026-08-08T21:45:00+08:00
  checked: src/debugmate/probe.py exception-to-capability mapping
  found: Any DifyTransportError or DifyContractError after upload reconstructs all capabilities as FAIL.
  implication: A C05 workflow/validation failure falsely erases C01/C02 evidence and falsely claims unexecuted C03/C04/C06/C07 failed.

- timestamp: 2026-08-08T21:51:00+08:00
  checked: Focused mocked regression before production change
  found: Success-path assertion raises KeyError for generation_request; semantic-failure assertion observes fail for all seven capabilities instead of pass/pass/not-tested/not-tested/fail/not-tested/not-tested.
  implication: Both causal mechanisms reproduce locally without any external API call.

- timestamp: 2026-08-08T21:55:00+08:00
  checked: Focused mocked regressions after production change
  found: Both tests pass; the success request includes nonempty facts/evidence and dependency_environment routing, while semantic failure preserves C01/C02 and isolates failure to C05.
  implication: The minimal change causally addresses both reproduced defects.

- timestamp: 2026-08-08T22:02:00+08:00
  checked: Related local verification suite and static checks
  found: tests/test_probe_cli.py plus tests/diagnosis/test_generation_repair.py report 35 passed; Ruff check, Ruff format check, and git diff --check all exit 0.
  implication: Probe behavior, generation/repair contract behavior, formatting, and patch hygiene pass locally without external API access.

- timestamp: 2026-08-08T22:10:00+08:00
  checked: Human-authorized live cloud probe against the published Dify workflow
  found: Exit 0 with status_counts {pass: 3, not-tested: 4}; C01/C02/C05 pass and C03/C04/C06/C07 remain not-tested. Bundle .artifacts/dify-cloud-probe-live2/case_d2c4d21672c14d9bad7f7fe95ee86653 verifies with zero issues.
  implication: The original live failure is resolved end-to-end without overstating unexercised capabilities.

## Resolution

root_cause: run_cloud_probe sent only case_id/file_id instead of the formal GenerationRequest required by local semantic validation, and broad exception handlers rebuilt all seven capability statuses uniformly, erasing completed upload evidence and misclassifying unexecuted capabilities.
fix: Send generation_request in the initial Dify workflow inputs, validate the returned candidate against the same request object, and maintain per-capability status/evidence across upload, workflow, validation, and error stages.
verification: Focused pre-fix regressions failed on both mechanisms. After the fix, 35 related mocked/local tests pass, Ruff and diff checks pass. Human-authorized published Dify replay exits 0 with exactly C01/C02/C05 pass and four not-tested; the resulting evidence bundle verifies with zero issues.
files_changed: [src/debugmate/probe.py, tests/test_probe_cli.py]
