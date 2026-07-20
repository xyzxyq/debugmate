# Phase 04 — UI Review

**Audited:** 2026-07-20
**Baseline:** `04-UI-SPEC.md` plus student/beginner usability criteria
**Screenshots:** no new capture (no server on 3000/5173/8080); inspected current Playwright captures in `output/playwright/` and committed real Edge evidence. The committed `evidence/course-v0.1` screenshots predate commits `0144efc`/`f031c6b` and are not evidence of the synchronized light theme.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 2/4 | Friendlier headings help, but the page mixes onboarding, replay, backend jargon, static advice, and exact-contract drift. |
| 2. Visuals | 2/4 | The light theme is clearer, yet the update mostly restyles the same dense three-column workbench and adds card-within-card chrome. |
| 3. Color | 2/4 | Contrast is strong, but persistent red/pink diagnosis styling and green waiting treatment communicate the wrong state. |
| 4. Typography | 3/4 | Text is readable and technical literals are distinct, with minor scale/contract inconsistencies and dense ID-heavy areas. |
| 5. Spacing | 2/4 | Consistent enough visually, but 14/18 px values, large shadows, and nested padding depart from the 4 px scale and inflate the page. |
| 6. Experience Design | 3/4 | State safety, recovery, accessibility, and responsive tests are strong; novice progression and result-first prioritization remain weak. |

**Overall: 14/24**

---

## Top 3 Priority Fixes

1. **Make the middle column state-derived instead of showing generic advice at all times** — beginners may interpret the current red “问题概览” and static repair steps as an actual diagnosis before a run exists — show a neutral 1→2 onboarding checklist while idle, the verified cause/plan only after completion, and the seven-field recovery guidance for partial/failed states.
2. **Turn the input rail into one guided primary path** — “生成本地脱敏预览”, disabled “确认预览并开始本地诊断”, replay, backend provenance, correction, and retry compete in one narrow column — present numbered steps (`1. 生成脱敏预览` → `2. 确认并开始诊断`), move replay into a secondary “查看示例” disclosure, and reveal correction only after a verified result.
3. **Remove decorative depth and restore semantic state colors** — shadows on the command bar, all regions, buttons, and nested summaries make the interface heavier without improving comprehension — use the UI-SPEC's 8 px radius/1 px border surfaces, one shadow level at most, neutral idle styling, and green/yellow/red only when the actual state is completed/partial/failed.

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

The synchronized labels `开始诊断`, `问题概览`, and `结果查看` are more approachable than the former operator-oriented terminology and better fit a student audience ([app.py](../../../src/debugmate/ui/app.py#L1219), [app.py](../../../src/debugmate/ui/app.py#L1286), [app.py](../../../src/debugmate/ui/app.py#L1322)). The two privacy actions also describe the security boundary honestly.

Notable gaps:

- The product label and live CTA no longer match the approved contract: `DebugMate 学习诊断助手` replaces `DebugMate 诊断工作台`, while the implemented live path uses two longer CTA labels instead of the contract's `开始诊断` ([app.py](../../../src/debugmate/ui/app.py#L1188), [app.py](../../../src/debugmate/ui/app.py#L1201), [app.py](../../../src/debugmate/ui/app.py#L1233)). This may be an intentional audience change, but the design contract has not been updated.
- `下一步怎么做` always displays three dependency-repair steps, including in the idle screenshot ([app.py](../../../src/debugmate/ui/app.py#L1291)). Because this copy is not derived from `ResultViewState`, it reads like verified advice before diagnosis and is especially risky for beginners.
- The input rail repeats `开始` and `示例案例` as both kicker and field label, while `后端：local-rule-v1（本地规则，无云端调用）` exposes implementation language before it helps the user choose an action ([app.py](../../../src/debugmate/ui/app.py#L1219), [app.py](../../../src/debugmate/ui/app.py#L1243), [app.py](../../../src/debugmate/ui/app.py#L1244), [app.py](../../../src/debugmate/ui/app.py#L1250)).
- `安全重试` is visible but disabled in idle/completed views ([app.py](../../../src/debugmate/ui/app.py#L1312), [app.py](../../../src/debugmate/ui/app.py#L1176)). Hide it until a retryable partial state exists instead of asking novices to interpret an unavailable expert action.
- Error and partial copy is a strength: status, safe code, completed/inherited stages, available results, retry scope, and recommended action are all explicitly mapped ([presentation.py](../../../src/debugmate/ui/presentation.py#L29), [presentation.py](../../../src/debugmate/ui/presentation.py#L176)).

### Pillar 2: Visuals (2/4)

The light update improves legibility and creates a clearer title/status area. The current completed desktop capture shows a recognizable left-to-right flow and a large result surface.

However, commits `0144efc` and `f031c6b` primarily changed palette, radii, shadows, and labels while retaining the same three-region information architecture. The desktop capture remains cognitively dense: the narrow left rail contains live diagnosis, replay, provenance, and correction; the middle combines an alarm-colored summary, generic steps, evidence table, commands, and retry; the right exposes a long report with raw IDs and English enum values. The result is visually polished but not materially simpler.

The update also adds depth at nearly every level: command-bar shadow/blur ([app.py](../../../src/debugmate/ui/app.py#L81)), shadows on all three regions ([app.py](../../../src/debugmate/ui/app.py#L135)), shadows on every button ([app.py](../../../src/debugmate/ui/app.py#L174)), and another shadow on the nested diagnosis summary ([app.py](../../../src/debugmate/ui/app.py#L205)). This conflicts with the UI-SPEC rejection of oversized shadows and cards-within-cards.

Immediate visual hierarchy change: make the verified result summary the strongest completed-state focal point; render evidence IDs, full commands, and generation metadata as secondary disclosures. The current full report and evidence table compete for attention rather than supporting a quick “what happened / what should I do” scan.

### Pillar 3: Color (2/4)

The light canvas, dark text, blue action color, and test-covered 4.5:1 contrast are a substantial improvement over the older dark screenshots. The current token set is centralized at [app.py](../../../src/debugmate/ui/app.py#L38), and browser tests explicitly inspect light-surface leakage and contrast.

Semantic color is the main issue:

- `.diagnosis-summary` is always pink/red with a red border, including idle and successful states ([app.py](../../../src/debugmate/ui/app.py#L205)). In the current idle capture this makes “等待诊断” look like an error.
- The idle status is visually treated as a green pill through the generic first-paragraph rule ([app.py](../../../src/debugmate/ui/app.py#L97)). Green should mean completed, not waiting.
- The middle region keeps a red top border while the result region keeps blue regardless of state ([app.py](../../../src/debugmate/ui/app.py#L144)). This makes structural decoration compete with the real completed/partial/failed semantics.

Use neutral gray/blue for idle, blue for running, green for completed, amber for partial/fallback, and red only for failed. Bind those styles to state-specific classes or component variants rather than static column identity.

### Pillar 4: Typography (3/4)

The latest screenshots have readable Chinese body text, clear section headings, and usable 12 px metadata/table text. Monospace treatment helps distinguish IDs and technical values ([app.py](../../../src/debugmate/ui/app.py#L159)). The browser suite also protects contrast and 200% zoom behavior.

Contract drift remains: the page title is 20 px rather than the declared 18 px, and region headings are 18 px rather than 16 px ([app.py](../../../src/debugmate/ui/app.py#L87), [app.py](../../../src/debugmate/ui/app.py#L152)). More importantly, raw `case_…`, `run_…`, hashes, `dependency_environment`, and fact IDs dominate the result/report scan. Keep these copyable, but shorten them visually and place the full value in a details/metadata disclosure so a novice first sees the Chinese diagnosis and recommended action.

The 375 px capture shows the title wrapping awkwardly across two lines. A shorter mobile label (`DebugMate`) plus a secondary subtitle, or responsive 18 px sizing, would preserve hierarchy without consuming the entire header.

### Pillar 5: Spacing (2/4)

The page is internally consistent, but it does not follow the approved 4 px scale. Examples include 14 px page padding/gaps/margins, 18 px padding, and 11/14 px radii ([app.py](../../../src/debugmate/ui/app.py#L52), [app.py](../../../src/debugmate/ui/app.py#L77), [app.py](../../../src/debugmate/ui/app.py#L123), [app.py](../../../src/debugmate/ui/app.py#L174), [app.py](../../../src/debugmate/ui/app.py#L205)). The 18×45 px and 14×34 px shadow extents add large decorative whitespace not present in the contract.

On mobile, stacking is technically correct but produces a long sequence of control card → overview card → result card. Reducing nested padding/shadows and removing idle-only expert controls would shorten the path to results more effectively than further breakpoint tuning.

Recommended normalization: 8 px control radius, 8/12/16/24 px spacing only, 16 px grid gap, 16 px region padding, and either no shadow or one subtle 0 2px 8px surface shadow.

### Pillar 6: Experience Design (3/4)

The underlying experience engineering is the strongest part of the implementation:

- Idle, seven ordered running stages, completed, partial, failed, replay, and fallback states are explicitly mapped rather than inferred ([presentation.py](../../../src/debugmate/ui/presentation.py#L8), [presentation.py](../../../src/debugmate/ui/presentation.py#L220)).
- Partial states preserve valid artifacts and expose scoped retry; failed states show safe, structured guidance without raw tracebacks.
- Preview approval is a separate, one-time action; duplicate actions are disabled during running; correction creates a new run only after confirmation ([app.py](../../../src/debugmate/ui/app.py#L1495), [app.py](../../../src/debugmate/ui/app.py#L1569)).
- The implementation provides `aria-live`, visible focus, keyboard tests, 200% zoom tests, and 1024/768 responsive coverage ([app.py](../../../src/debugmate/ui/app.py#L1205), [app.py](../../../src/debugmate/ui/app.py#L276), [test_browser.py](../../../tests/ui/test_browser.py#L1444)).

For a novice, though, the initial decision is not obvious. Two live buttons, replay, technical backend provenance, a correction accordion, a generic retry button, and result tabs are all present before a run. The current mobile capture makes the user traverse the entire control and overview stack before results. The six extraction fields are also hidden inside an accordion ([app.py](../../../src/debugmate/ui/app.py#L1256)), contrary to the UI-SPEC requirement that the six fields remain visible as a compact editable group; if the intentional novice design is to hide them initially, the contract should be revised and they should automatically reveal after a verified result.

The result tabs remain operable in idle even though `ComponentViewModel.tabs_enabled=False` is never wired to the Gradio Tabs component ([presentation.py](../../../src/debugmate/ui/presentation.py#L230), [app.py](../../../src/debugmate/ui/app.py#L1323)). This creates empty destinations instead of a guided sequence. Disable or visually lock result tabs until a verified result exists, then focus/announce the summary when the run completes.

---

## Student/Beginner Verdict

The synchronized UI is easier to read and less intimidating than the former dark technical workbench, but it is primarily a visual restyle, not a workflow simplification. It meets many safety and state-truth requirements, yet still asks a beginner to understand three simultaneous columns, multiple paths, backend terminology, raw identities, and generic repair advice. The next iteration should spend less effort on macOS-like depth and more on progressive disclosure, state-derived guidance, and one unmistakable next action.

## Evidence Notes

- Current light-theme captures inspected: `output/playwright/before-desktop.png`, `before-completed-desktop-2.png`, and `before-mobile.png`.
- Committed course screenshots inspected: completed, TTS-partial, and card-partial. Their manifest names source commit `57613c9`, so they document the pre-sync dark UI and should be regenerated before course submission if the light theme is the intended final design.
- No app server was available on ports 3000, 5173, or 8080. The focused pytest command could not run because this checkout has no `.venv`; the review therefore relies on source, existing browser tests, and real screenshot evidence.
- Registry audit skipped: `components.json` is absent and the UI-SPEC prohibits third-party registries.

---

## Files Audited

- `.planning/phases/04-multimodal-results-ui/04-UI-SPEC.md`, `04-CONTEXT.md`, `04-VERIFICATION.md`
- All `04-01-PLAN.md` through `04-12-PLAN.md` and all available `04-01-SUMMARY.md` through `04-10-SUMMARY.md`
- `src/debugmate/ui/app.py`, `presentation.py`, `local_live.py`, `serve.py`, and `src/debugmate/results/service.py`
- `tests/ui/test_app.py`, `tests/ui/test_browser.py`
- `docs/course/README.md`, `evidence/course-v0.1/manifest.json`, and five real Edge screenshots
- Git changes `0144efc` and merge synchronization `f031c6b`
