# Phase 8: Dify Unified Live Chain - Discussion Log

> **Audit trail only.** Downstream agents must use `08-CONTEXT.md`; this file records auto-selected alternatives.

**Date:** 2026-08-10
**Phase:** 08-dify-unified-live-chain
**Mode:** auto — recommended defaults selected from existing project/user decisions

## Backend selection and consent

| Option | Description | Selected |
|---|---|---|
| Configuration-driven Dify with explicit local fallback | No UI selector; no network before approval; truthful backend label | Yes |
| Always Dify | Crash/block when configuration is missing | No |
| Student backend/key selector | Exposes configuration and secret-handling complexity | No |

## Cloud failure behavior

| Option | Description | Selected |
|---|---|---|
| Typed cloud failure, fresh approval for local retry | Preserves lineage, quota and backend truth | Yes |
| Silent same-run local fallback | Hides a failed Dify attempt | No |
| Mixed cloud/local result | Makes evidence lineage ambiguous | No |

## Workflow and validation contract

| Option | Description | Selected |
|---|---|---|
| DSL-aligned image input plus same-run extraction/retrieval/diagnosis envelope | Proves the complete product chain | Yes |
| Diagnosis JSON only | Cannot independently prove retrieval | No |
| Console screenshots/manual logs | Not reproducible or product-wired evidence | No |

## Retry and concurrency

| Option | Description | Selected |
|---|---|---|
| No ambiguous POST retry; durable approval/run receipt | Prevents duplicate remote runs and quota use | Yes |
| Generic two-attempt POST retry | May duplicate an already-dispatched workflow | No |
| Cosmetic cancel button | Cannot cancel the provider truthfully | No |

## Evidence and scope

| Option | Description | Selected |
|---|---|---|
| One current synthetic redacted E2E bundle; cases/media later | Proves Phase 8 without repeating Phase 9/10 | Yes |
| Reuse historical capability bundle only | Does not prove current Gradio product wiring | No |
| Refresh cases/PPTX/video now | Violates phase boundary and media-last preference | No |

## Agent discretion

- Internal receipt/envelope class names and atomic local persistence format.
- Exact bounded trace/response limits and safe error-code implementation.

## Deferred Ideas

- Phase 9 representative cases and prompt comparisons.
- Phase 10 final course media and screenshots.
