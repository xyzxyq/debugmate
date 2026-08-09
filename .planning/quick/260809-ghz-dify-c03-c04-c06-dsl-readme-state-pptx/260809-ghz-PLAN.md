---
quick_id: 260809-ghz
phase: quick-260809-ghz-dify-c03-c04-c06-dsl-readme-state-pptx
plan: 01
type: quick
wave: 1
depends_on: []
autonomous: true
description: 补齐 Dify C03/C04/C06 的独立版本化真实证据并同步事实口径，不触碰课程媒体
mode: quick-full
date: 2026-08-09
files_modified:
  - src/debugmate/dify_live_evidence.py
  - scripts/capture_dify_c03_c04_c06.ps1
  - tests/platform/test_dify_live_evidence.py
  - tests/platform/test_dify_dsl.py
  - evidence/dify-live/README.md
  - evidence/dify-live/2026-08-09/c03-c04/input-terminal.png
  - evidence/dify-live/2026-08-09/c03-c04/workflow-request-manifest.json
  - evidence/dify-live/2026-08-09/c03-c04/vision-retrieval-evidence.json
  - evidence/dify-live/2026-08-09/c03-c04/workflow-output.json
  - evidence/dify-live/2026-08-09/c03-c04/retriever-resource.json
  - evidence/dify-live/2026-08-09/c06/reexport.dsl.yml
  - evidence/dify-live/2026-08-09/c06/reconstructed-output.json
  - evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json
  - platform/dify/capability-matrix.json
  - platform/dify/README.md
  - README.md
  - .planning/STATE.md
must_haves:
  truths:
    - "C03 只有在真实 PNG 上传后，同一次正式 Dify Workflow 运行从图像中输出与固定目标文本一致、source_kind=vlm 的事实，并由版本化 allowlisted request manifest + SHA-256 证明 error_text、code、environment、generation_request、issues、candidate 等全部非图像输入不含目标文本且未预置 facts 时才为 pass。"
    - "C04 只有在真实 Dify Workflow 的 Knowledge Retrieval 节点 resource/console run log 直接返回至少一个非空 chunk，且记录 chunk ID、内容摘要、来源标题/ID、来源 URL/定位符和相关性元数据时才为 pass；仅 diagnosis.evidence、本地检索与空 evidence 不计。"
    - "C06 只有在当前 platform/dify/app.dsl.yml 被独立导入/重建为另一应用、重新导出、通过确定性结构比较并在重建应用上复跑成功时才为 pass。"
    - "任一 live 能力因凭据、登录、权限、配额、模型、知识库或接口限制无法证明时，仅该项保持或更新为准确的 not-tested/blocked/fail，其他可验证项继续完成，且绝不从 DSL 节点或历史描述推断 pass。"
    - "C01/C02/C05/C07 的既有 evidence_path、SHA-256 与 pass 状态保持不变；所有新增 pass 也必须指向 Git 跟踪文件并匹配实算 SHA-256。"
    - "能力矩阵、两份 README、live evidence README 与 STATE 使用同一事实口径，同时 PPTX、视频、字幕、最终截图和产品 UI 保持不变。"
  artifacts:
    - path: src/debugmate/dify_live_evidence.py
      provides: "C03/C04/C06 证据脱敏、严格校验、DSL 规范化比较和 SHA-256 绑定"
    - path: evidence/dify-live/2026-08-09/c03-c04/vision-retrieval-evidence.json
      provides: "真实图像上传、视觉抽取和知识检索的逐能力执行记录"
    - path: evidence/dify-live/2026-08-09/c03-c04/workflow-request-manifest.json
      provides: "绑定 PNG 和正式请求 SHA-256、证明全部非图像输入无目标文本且无预置事实的 allowlisted 清单"
    - path: evidence/dify-live/2026-08-09/c03-c04/retriever-resource.json
      provides: "来自 Knowledge Retrieval 节点 resource/console run log 的直接 chunk 与来源元数据"
    - path: evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json
      provides: "当前 DSL 导入、重导出、结构比较和重建应用复跑记录"
    - path: tests/platform/test_dify_live_evidence.py
      provides: "pass→真实记录→Git tracked artifact→SHA-256 与秘密扫描门禁"
    - path: tests/platform/test_dify_dsl.py
      provides: "当前/重导出 DSL 的确定性结构等价与关键节点合同门禁"
    - path: platform/dify/capability-matrix.json
      provides: "保留既有能力并按独立证据更新 C03/C04/C06 的机器可读真值"
    - path: .planning/STATE.md
      provides: "本次真实尝试、逐能力结果、阻塞原因与课程材料冻结边界"
  key_links:
    - from: evidence/dify-live/2026-08-09/c03-c04/vision-retrieval-evidence.json
      to: evidence/dify-live/2026-08-09/c03-c04/input-terminal.png
      via: "workflow-request-manifest.json 绑定实际 PNG/请求哈希并证明所有非图像输入无目标文本；C03 记录同一 run_id 下的 vlm 抽取文本"
      pattern: "request_sha256|input_image|non_image_inputs|run_id|source_kind"
    - from: evidence/dify-live/2026-08-09/c03-c04/vision-retrieval-evidence.json
      to: evidence/dify-live/2026-08-09/c03-c04/workflow-output.json
      via: "C04 的 retrieved_chunks/来源元数据来自 retriever-resource.json 所保存的直接 Knowledge Retrieval node resource/log，而非 diagnosis.evidence"
      pattern: "retriever_resource|node_run_id|chunk_id|source_url|relevance"
    - from: evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json
      to: platform/dify/app.dsl.yml
      via: "source_sha256、reexport_sha256、normalized_structure_sha256 与 reconstructed_run_id 证明导入后结构和运行"
      pattern: "source_dsl|reexport|normalized|reconstructed_run_id"
    - from: platform/dify/capability-matrix.json
      to: evidence/dify-live/2026-08-09/
      via: "每个新增 pass 的 evidence_path 指向对应能力记录且 sha256 为该记录实算值"
      pattern: "C03|C04|C06|evidence_path|sha256"
---

# Quick Task 260809-ghz Plan

<objective>
为 Dify C03 视觉抽取、C04 知识检索和 C06 DSL 导出/重导入建立彼此独立、真实运行、版本化且可复算的证据链，并同步能力矩阵、README 与项目状态。

Purpose: 当前仓库只对 C01/C02/C05/C07 有 Git 跟踪证据；C03/C04/C06 虽在真实 DSL 中有对应配置或历史观察，仍缺少足以支持 `pass` 的运行记录。本计划补齐严格证据门禁，同时允许云端权限不足时逐项诚实保留非 pass。
Output: 可重跑的安全 capture/validation 工具，C03/C04 live Workflow 证据，C06 import→re-export→structure-compare→re-run 证据，更新后的 capability matrix、文档与 STATE，以及执行后的 quick SUMMARY。
</objective>

<context>
@AGENTS.md
@C:/Users/20795/Documents/codex 第一次进化/docs/CODEX_EXPERIENCE_PROFILE.md
@.planning/PROJECT.md
@.planning/REQUIREMENTS.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/quick/260809-fob-dify-c01-c07-readme-pptx/260809-fob-SUMMARY.md
@.planning/quick/260809-fob-dify-c01-c07-readme-pptx/260809-fob-VERIFICATION.md
@platform/dify/capability-matrix.json
@platform/dify/README.md
@platform/dify/app.dsl.yml
@README.md
@evidence/dify-live/README.md
@src/debugmate/adapters/dify.py
@src/debugmate/probe.py
@tests/test_probe_cli.py
@tests/diagnosis/test_dify_diagnosis_cloud.py
@tests/knowledge/test_retrieval_trace.py

Locked evidence boundaries:
- C01/C02/C05/C07 已由 quick 260809-fob 验证为 `pass`；不得改变其 evidence_path、SHA-256 或状态。C03/C04/C06 当前均为 `not-tested`，只有本计划生成的各自独立证据通过全部门禁后才能升级。
- 使用固定虚构目标文本 `ModuleNotFoundError: No module named 'debugmate_demo_pkg'` 生成确定性终端 PNG；这是真实上传的合成测试输入，不是伪造平台截图。C03 必须保存 PNG 哈希、上传成功的脱敏记录、真实 Workflow run ID 和 `source_kind=vlm` 的实际抽取值。另存确定性 `workflow-request-manifest.json`：只 allowlist 图像路径/哈希、上传 ID 指纹、请求 canonical SHA-256、目标文本 SHA-256 和全部非图像输入的实际安全值/哈希；必须证明 `error_text`、`code`、`environment`、`generation_request`、`request_kind`、`schema_version`、`issues`、`candidate` 及任何新增非图像字段均不含目标文本或其大小写/Unicode 规范化等价文本，且没有 observed_facts/evidence/routing 等预置事实。目标原文只能作为 PNG 像素内容进入请求；在任何非图像输入中复述、暗示或预置均使 C03 fail。
- C04 必须保存 Knowledge Retrieval 节点的直接 resource 或 Dify console run/node execution log（安全 allowlist 后的 `retriever-resource.json`），至少一个检索命中含 `chunk_id`、安全 `content_summary`、`source_id`/来源标题、`source_url` 或可核验来源定位、`locator` 和 `relevance_score`（Dify 未返回的可选数值必须明确为 null，不能编造），并绑定 workflow/node run ID。最终 diagnosis 的 `evidence` 只能交叉核对，不能作为 C04 的主证据；本地 fixture/offline retrieval 或 DSL 中存在 knowledge-retrieval 节点均不算通过。
- 优先使用正式 `/files/upload` + `/workflows/run` Application API 完成 C03/C04；图像变量使用当前 Dify Workflow 文件对象合同。可分别运行 C03 与 C04，但证据必须明确各自 `run_id`；若一次运行同时满足，两项可共享该真实输出但仍须分别验证。
- C06 优先使用 Dify console 的正式导入/导出接口；如果应用 API key 无管理权限，则使用已登录浏览器自动化执行 console 导入和重新导出。不得保存 console cookie、CSRF token、Authorization header、应用密钥、完整网络 HAR 或个人绝对路径。导入后必须是独立应用，并通过其正式 Workflow API 或 console Run 完成固定案例复跑；仅出现“导入成功”提示不够。
- DSL 结构比较必须解析 YAML 后忽略纯展示/实例易变字段（节点/边 ID、坐标、viewport、selected、zIndex、应用显示名/图标），再比较：app mode/kind/version、依赖插件标识、start 变量名与类型、节点类型/标题、按标题映射的边拓扑、LLM model/vision/structured-output 合同、knowledge-retrieval 模式/top_k、end 输出变量。不得通过删除模型、视觉、检索或输出合同来制造“相等”。保存源 DSL、重导出 DSL 的原始 SHA-256，以及双方 normalized structure SHA-256 和差异列表。
- 所有 live 配置只从环境变量或当前已认证浏览器会话读取。工具输出和版本化记录只允许安全 allowlist 字段；平台文件 ID/应用 ID 可保存 SHA-256 指纹而非原值。任何 secret/CSRF/header/session/personal absolute path 命中都阻止发布。
- 若缺少凭据、登录会话、console 权限、额度、模型、知识库或导入能力：不要求用户手工补洞，不充值，不无限重试；为已实际尝试的能力写安全的 `blocked`/`fail` 执行记录和原因码，矩阵保持准确非 pass，继续完成其他能力、测试与文档同步。
- 只修改 frontmatter `files_modified` 和本 quick 的 SUMMARY/VERIFICATION。不得触碰 `deliverables/**`、PPTX、MP4、SRT、视频、字幕、最终截图、产品 UI、`.planning/PROJECT.md`、`.planning/REQUIREMENTS.md`、`.planning/ROADMAP.md` 或无关文件。
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 建立严格的 live 证据与 DSL 结构比较工具</name>
  <files>src/debugmate/dify_live_evidence.py, scripts/capture_dify_c03_c04_c06.ps1, tests/platform/test_dify_live_evidence.py, tests/platform/test_dify_dsl.py</files>
  <behavior>
    - "C03 pass 记录必须绑定真实 PNG 文件哈希、allowlisted request manifest/request SHA-256、上传成功指纹、Workflow run ID、固定目标文本和 source_kind=vlm 的完全匹配抽取；任何非图像输入含目标或预置 facts 时拒绝。"
    - "对 error_text、code、environment、generation_request、issues、candidate 及任意新增非图像输入逐一注入目标文本的负向测试，都必须使 C03 validator 拒绝 pass。"
    - "C04 pass 记录必须绑定 Workflow/node run ID 和至少一个来自直接 retriever resource/console log、含 chunk/source 元数据的真实 hit；仅 diagnosis.evidence、空命中、缺来源或本地 backend 拒绝。"
    - "C06 pass 记录必须绑定当前源 DSL、独立重导出 DSL、相等的规范化结构哈希、空差异列表和重建应用复跑输出；仅导入或仅文本比较拒绝。"
    - "Task 1/2 的 candidate validator 只验证内容、路径边界、artifact 存在、SHA-256 和秘密扫描，不要求尚未提交的 evidence 已 Git tracked；Task 3 的 publication validator 才强制所有 pass evidence 已进入 Git。"
    - "证据生成和验证拒绝 API key、Bearer/header、cookie、CSRF/session token、个人绝对路径及未 allowlist 的原始响应字段。"
  </behavior>
  <action>先写 focused tests，再实现 `debugmate.dify_live_evidence`。定义严格 Pydantic 证据模型/验证函数，分别表达 C03、C04、C06 的 `pass|fail|blocked|not-tested`，并用上述字段级条件阻止不完整 pass。为 C03 建立确定性 allowlisted request manifest：枚举当前 Start 节点全部非图像变量，保存安全空值/规范化值及 canonical request SHA-256；validator 必须递归检查每个非图像输入，不允许目标文本或其 Unicode 规范化/大小写等价值，不允许任何 observed_facts/evidence/routing/prebuilt facts。参数化负向测试逐个把目标注入 `error_text`、`code`、`environment`、`generation_request`、`issues`、`candidate` 及未知新增字段并断言拒绝。实现确定性 PNG 生成、`image/png` 上传和 Workflow 调用，只从响应 allowlist 提取 `run_id` 与 `vlm` facts。C04 单独定义 direct retriever resource/log 模型，要求 node run identity 和 chunk/source metadata，显式拒绝以 diagnosis.evidence 代替。实现 YAML 规范化器和结构 diff，明确保留模型、vision、retrieval、start/end 合同及拓扑，仅忽略 context 中列出的易变展示字段。实现两级验证：`validate-candidate` 仅检查内容、artifact、哈希、路径和秘密，允许 evidence 尚未 tracked；`validate-published` 在 Task 3 增加 Git tracked/not-ignored 门禁。PowerShell 包装器使用 `-LiteralPath`、仓库相对 `.artifacts` staging、环境变量名和一次性 capture 子命令，逐项尝试且禁止直接写 capability matrix。不得扩展产品 workflow，也不得记录凭据/headers/console 网络数据。</action>
  <verify>
    <automated>$ErrorActionPreference='Stop'; $python=(Resolve-Path -LiteralPath '.venv\Scripts\python.exe').Path; $env:PYTHONPATH=(Resolve-Path -LiteralPath 'src').Path; & $python -m pytest -q tests\platform\test_dify_live_evidence.py tests\platform\test_dify_dsl.py; if($LASTEXITCODE){ throw 'Dify live evidence contracts failed' }; & $python -m ruff check src\debugmate\dify_live_evidence.py tests\platform\test_dify_live_evidence.py tests\platform\test_dify_dsl.py; if($LASTEXITCODE){ throw 'Ruff failed' }</automated>
  </verify>
  <done>离线测试证明不完整/伪造/泄密的 C03/C04/C06 pass 会被拒绝，DSL 比较保留关键语义，capture 包装器能逐项尝试并安全产生 pass 或准确 non-pass staging 记录。</done>
</task>

<task type="auto">
  <name>Task 2: 执行真实 C03/C04 Workflow 与 C06 独立重建取证</name>
  <files>evidence/dify-live/2026-08-09/c03-c04/input-terminal.png, evidence/dify-live/2026-08-09/c03-c04/workflow-request-manifest.json, evidence/dify-live/2026-08-09/c03-c04/vision-retrieval-evidence.json, evidence/dify-live/2026-08-09/c03-c04/workflow-output.json, evidence/dify-live/2026-08-09/c03-c04/retriever-resource.json, evidence/dify-live/2026-08-09/c06/reexport.dsl.yml, evidence/dify-live/2026-08-09/c06/reconstructed-output.json, evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json, evidence/dify-live/README.md</files>
  <action>在被忽略的专用 `.artifacts/dify-c03-c04-c06-capture` staging 中运行 Task 1 工具。C03：生成固定 PNG；构造请求时令 `error_text`、`code` 为空，`environment`、`generation_request`、`issues`、`candidate` 为空对象且不提供任何 facts，并枚举/拒绝任何未 allowlist 的非图像 Start 变量。先生成 `workflow-request-manifest.json` 和 canonical request SHA-256，运行 target-free/无预置事实 validator 后才调用正式 `/files/upload`；返回 file ID 只保留 SHA-256 指纹。使用唯一含信息的 `image_input` 文件对象调用当前发布 Workflow。只有输出含固定目标文本的 `source_kind=vlm` observed fact 且 manifest 仍与实际请求哈希一致才记录 pass；模型标为 text/ocr、目标出现在任一非图像字段或没有完全匹配均记录 fail。

C04 不得从最终 diagnosis.evidence 取证。优先读取正式 Workflow response 的 `retriever_resources`；若 blocking response 不提供，则通过 Dify console 的 run history/node execution detail API 或已登录浏览器自动化打开同一 run 的 Knowledge Retrieval 节点，只 allowlist 保存 `node_run_id`、workflow run ID、chunk ID、内容摘要、来源 ID/标题/URL/locator/relevance 到 `retriever-resource.json`。如果同次 run 没有合格 direct resource，可做一个专用 retrieval run，但仍必须保存其直接 retriever resource/log 和独立 run ID。登录/权限阻断时 C04 记录 blocked，不得退回 diagnosis.evidence。`workflow-output.json` 只含 case/run ID、安全 VLM facts 和最终状态，用于 C03 交叉验证，不冒充 C04 主证据。

随后执行 C06：核对当前 `platform/dify/app.dsl.yml` 哈希，优先走正式 console import/export 接口；若管理接口不对应用 API key开放，复用当前已认证浏览器会话自动导入为名称可区分的临时独立应用、重新导出到 staging，并在该重建应用上运行固定案例。浏览器出现重新登录、验证码或权限阻断时停止该路径并记录 `blocked`，不要请求或捕获用户凭据。用 Task 1 规范化器比较源/重导出 DSL；只有结构哈希相等、diff 为空且重建应用复跑返回真实 run ID 与有效 diagnosis 时记录 C06 pass。对每项运行 `validate-candidate`，只检查内容、路径、文件哈希和秘密，不要求这些尚未提交的文件已 Git tracked；通过后才从 staging 选择性复制到列出的 `evidence/dify-live/2026-08-09/` 路径。对于 non-pass，只版本化不含敏感数据的能力记录，不创建伪造输出/DSL。更新 live evidence README，然后完成 Task 2 原子提交，确保全部候选 evidence 在 Task 3 开始前已进入 Git。不要删除 console 应用（删除超出授权），也不要截图或触碰课程材料。</action>
  <verify>
    <automated>$ErrorActionPreference='Stop'; $python=(Resolve-Path -LiteralPath '.venv\Scripts\python.exe').Path; $env:PYTHONPATH=(Resolve-Path -LiteralPath 'src').Path; & $python -m debugmate.dify_live_evidence validate-candidate --repository-root . --evidence-root evidence\dify-live\2026-08-09; if($LASTEXITCODE){ throw 'C03/C04/C06 candidate content/hash/secret validation failed' }; & $python -m pytest -q tests\platform\test_dify_live_evidence.py tests\platform\test_dify_dsl.py -k 'not published_tracking'; if($LASTEXITCODE){ throw 'Candidate evidence tests failed' }; rg -n -i '(Bearer\s+[A-Za-z0-9._-]+|authorization\s*[:=]|api[_ -]?key\s*[:=]\s*["''][^"'']+|csrf|session[_ -]?token|cookie\s*[:=]|[A-Z]:\\Users\\)' evidence\dify-live\2026-08-09\c03-c04 evidence\dify-live\2026-08-09\c06; if($LASTEXITCODE -eq 0){ throw 'Live evidence contains secret/session/personal data' } elseif($LASTEXITCODE -ne 1){ throw 'Secret scan did not run' }</automated>
  </verify>
  <done>每个可证明能力都有独立、真实 run/import evidence 和精确 artifact 哈希；C03 的请求 manifest 证明非图像输入无目标/预置事实，C04 由 direct retriever resource/log 支撑；无法证明项有准确 non-pass 记录。全部 evidence 已通过 candidate 校验并由 Task 2 原子提交，供 Task 3 执行 Git tracking 门禁。</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: 按证据更新矩阵、README 与 STATE 并冻结课程材料</name>
  <files>tests/platform/test_dify_live_evidence.py, tests/platform/test_dify_dsl.py, platform/dify/capability-matrix.json, platform/dify/README.md, README.md, evidence/dify-live/README.md, .planning/STATE.md</files>
  <behavior>
    - "C01/C02/C05/C07 的状态、路径和哈希与 quick 260809-fob 基线逐字一致。"
    - "C03/C04/C06 仅在各自严格证据记录为 pass 时指向该 Git tracked JSON 并填其实算 SHA-256；否则矩阵保持准确 non-pass 且不伪造 pass 引用。"
    - "根 README、Dify README、live evidence README 与 STATE 的七项状态、证据边界和阻塞说明与 capability matrix 一致。"
    - "PPTX、MP4、SRT、视频、字幕、最终截图、产品 UI、PROJECT、REQUIREMENTS、ROADMAP 和既有 pass evidence 均未修改。"
  </behavior>
  <action>Task 3 开始时先运行 `validate-published`，确认 Task 2 原子提交已使全部候选 evidence 成为 Git tracked、not ignored 文件且哈希仍匹配；未跟踪则停止 promotion，不得先改矩阵。再增强矩阵回归测试：锁定 C01/C02/C05/C07 的既有三条路径/四项状态与现有 SHA-256；对 C03/C04/C06 逐项读取对应 live record，只有 record 通过严格 published 验证且为 pass 时允许矩阵 pass。C03 还必须验证版本化 request manifest 与 request SHA、全部非图像输入 target-free/no-prebuilt-facts；C04 必须验证 `retriever-resource.json` 来自 direct node resource/log，明确拒绝 diagnosis.evidence-only；C06 保持 roundtrip/re-run 门禁。每个 pass 的 evidence_path 必须是仓库内普通文件、未 ignored、已 Git tracked、SHA-256 匹配；non-pass 不得被 DSL 节点、共享 C05 diagnosis 或文字说明替代。再以实际证据结果更新 `capability-matrix.json`，不强求三项全 pass。同步 `platform/dify/README.md`、根 `README.md`、`evidence/dify-live/README.md` 和 `.planning/STATE.md`，准确写实际状态与阻塞原因。STATE 继续明确课程材料冻结。本任务不编辑真实 DSL 本体；`reexport.dsl.yml` 只是取证产物。</action>
  <verify>
    <automated>$ErrorActionPreference='Stop'; $python=(Resolve-Path -LiteralPath '.venv\Scripts\python.exe').Path; $env:PYTHONPATH=(Resolve-Path -LiteralPath 'src').Path; & $python -m debugmate.dify_live_evidence validate-published --repository-root . --evidence-root evidence\dify-live\2026-08-09; if($LASTEXITCODE){ throw 'Task 2 evidence is not committed/tracked or failed publication validation' }; & $python -m pytest -q tests\test_probe_cli.py tests\platform\test_dify_live_evidence.py tests\platform\test_dify_dsl.py; if($LASTEXITCODE){ throw 'Capability matrix/evidence/docs tests failed' }; & $python -m ruff check src\debugmate\dify_live_evidence.py tests\test_probe_cli.py tests\platform\test_dify_live_evidence.py tests\platform\test_dify_dsl.py; if($LASTEXITCODE){ throw 'Ruff failed' }; git diff --check -- src/debugmate/dify_live_evidence.py scripts/capture_dify_c03_c04_c06.ps1 tests/platform platform/dify/capability-matrix.json platform/dify/README.md README.md evidence/dify-live .planning/STATE.md .planning/quick/260809-ghz-dify-c03-c04-c06-dsl-readme-state-pptx; if($LASTEXITCODE){ throw 'Scoped diff check failed' }; $changed=@(git status --short | ForEach-Object { if($_.Length -ge 4){ $_.Substring(3).Replace('\','/') } }); if($changed | Where-Object { $_ -match '\.(pptx|mp4|srt)$' -or $_ -match '(^|/)(screenshots?|final-screenshots?|deliverables)(/|$)' -or $_ -match '^src/debugmate/ui/' -or $_ -in @('.planning/PROJECT.md','.planning/REQUIREMENTS.md','.planning/ROADMAP.md','platform/dify/app.dsl.yml') }){ throw 'Frozen/out-of-scope file changed' }</automated>
  </verify>
  <done>能力矩阵和四份事实文档准确反映实际 C03/C04/C06 结果，既有四项 pass 未漂移，全部 pass 均受 Git tracked file + exact SHA-256 测试保护，课程媒体与产品范围保持冻结。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Dify Application API → C03/C04 evidence | 云端响应不可信；只提取 allowlist 字段，必须由图像哈希、run ID、VLM exact match 或 retrieval source metadata 共同证明。 |
| Dify console/browser → C06 evidence | 已认证会话含秘密状态；只自动化导入/导出/运行，不保存 cookie、CSRF、header、HAR、密钥或原始会话数据。 |
| exported YAML → structural equivalence | 重导出可含易变 ID/布局；规范化只移除展示性字段，关键模型、vision、retrieval、contract 与 topology 必须保留并相等。 |
| `.artifacts` staging → Git evidence | 临时产物只有通过合同、秘密扫描、路径和哈希验证后才能选择性进入 `evidence/dify-live/`。 |
| live evidence → capability matrix/docs | 配置存在或部分成功不能升级状态；每个 pass 必须独立绑定对应版本化记录。 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-Q-GHZ-01 | Spoofing | C03 image extraction | mitigate | 固定 PNG SHA-256、上传指纹、真实 run ID、`source_kind=vlm` 和目标文本完全匹配；文本/OCR/本地结果不能代替。 |
| T-Q-GHZ-02 | Tampering | C04 retrieval hits | mitigate | 保存安全 retrieval allowlist、artifact SHA-256 和来源 URL/locator；至少一个真实非空命中才能 pass。 |
| T-Q-GHZ-03 | Repudiation | C06 import/reconstruction | mitigate | 记录 UTC、导入通道、源/重导出哈希、规范化哈希/diff、独立应用指纹和重建 run ID。 |
| T-Q-GHZ-04 | Information disclosure | API/browser captures | mitigate | 环境变量/现有会话只在内存使用；不保存 key/header/cookie/CSRF/HAR/原始响应/个人路径，发布前执行秘密扫描。 |
| T-Q-GHZ-05 | Denial of service | 配额、模型、知识库与 console 权限 | accept | 每项限必要尝试，失败后写准确 non-pass 并继续其余能力；不充值、不循环重试。 |
| T-Q-GHZ-06 | Elevation of privilege | console application lifecycle/course files | mitigate | 仅导入新应用和运行验证，不删除应用、不改课程媒体、UI 或规划源文件；范围测试强制冻结。 |
</threat_model>

<verification>
先用 TDD 锁定三项独立 pass 合同和 DSL 规范化语义；再在忽略 staging 中执行真实 API/console-browser capture，仅发布通过秘密与哈希门禁的 allowlist 证据；最后让矩阵测试逐项绑定 Git tracked evidence，并运行 focused pytest、Ruff、秘密扫描、diff check 和冻结路径检查。验证不要求三项都通过，只要求每项状态与真实证据严格一致。
</verification>

<success_criteria>
- C03 若为 pass，版本化证据可复算地证明真实 PNG 上传、真实 Workflow run、VLM 来源和固定目标文本抽取；allowlisted request manifest/request SHA 同时证明所有非图像输入无目标文本且没有预置 facts，负向注入测试会拒绝违例；否则准确记录 non-pass。
- C04 若为 pass，版本化证据包含至少一个来自真实 Dify Knowledge Retrieval 节点 resource/console run log 的 chunk 与来源元数据；仅 diagnosis.evidence 不足；否则准确记录 non-pass。
- C06 若为 pass，版本化证据证明当前 DSL 独立导入、重新导出、确定性结构等价和重建应用复跑；否则准确记录 non-pass。
- C01/C02/C05/C07 原状态、路径和哈希保持不变；所有七项均由自动测试禁止无证据 pass。
- Task 2 先完成内容/哈希/秘密校验并原子提交 evidence；Task 3 只有在 `validate-published` 证明 evidence 已 Git tracked 且未 ignored 后才提升矩阵状态。
- capability matrix、根 README、Dify README、live evidence README 与 STATE 逐项一致且不含秘密、会话数据或个人绝对路径。
- PPTX、视频、字幕、最终截图、产品 UI、真实 DSL、PROJECT、REQUIREMENTS、ROADMAP 与无关文件未修改。
</success_criteria>

<output>
执行完成后创建 `.planning/quick/260809-ghz-dify-c03-c04-c06-dsl-readme-state-pptx/260809-ghz-SUMMARY.md`，逐项列出 C03/C04/C06 的实际状态、run/import/re-export/compare 事实、版本化证据路径与 SHA-256、阻塞或失败原因，以及 C01/C02/C05/C07 保持不变的复核结果。SUMMARY 必须明确本 quick 未触碰 PPTX、视频、字幕、最终截图或产品 UI。
</output>
