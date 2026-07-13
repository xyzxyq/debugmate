# Phase 04 Research：三模态产物与统一结果页

**Researched:** 2026-07-13  
**Scope:** `MULTI-01..05`、`UX-01..04` 的实现前研究  
**Mode:** ecosystem + implementation  
**Confidence:** HIGH（本地确定性管线与 UI 架构）；MEDIUM（真实 Dify/edge TTS，受账号、网络和上游服务影响）

## Executive Recommendation

Phase 4 应建立一个与 Phase 3 evidence 分离的、只读消费 `DiagnosisRunOutcome` 的结果派生层：先重新验证 outcome 与源 evidence bundle，再构造唯一的 `PresentationModel`，从该模型并行生成 Markdown、Pillow PNG 和确定性中文复盘稿；音频只朗读该复盘稿；最后由本地一致性门禁统一验证身份、隐私、媒体和引用，再原子发布独立 `results/<case_id>/<result_id>/` 与确定性 ZIP。Gradio 只消费严格 `ResultViewState`，不推断业务状态、不直接调用 TTS/evidence/shell，也不接收用户路径。

不要解除现有 `EvidenceBundle` 对音频的 Phase 3 fail-closed 语义。新建 Phase 4 专用 `ResultBundle`/publisher，并复用 hashing、路径 confinement、输出扫描、PNG 清洗和源 bundle verifier 的原语。这样 Phase 3 evidence 继续不可变，Phase 4 的 MP3、ZIP 与 partial 状态拥有独立而更严格的合同。

本机现场事实：Python `3.13.5`、Pydantic `2.13.4`、HTTPX `0.28.1`、Pillow `12.3.0`、pytest `9.1.1`、Ruff `0.15.21` 已安装；FFmpeg/ffprobe `8.1` 可用；Windows SAPI 存在 `Microsoft Huihui Desktop - Chinese (Simplified)`；常用中文字体 `msyh.ttc`、`simhei.ttf`、`simsun.ttc` 可用。Gradio 与 edge-tts 尚未安装，Dify 相关环境变量未设置。计划必须先做依赖安装/导入 smoke，但不得把真实云 TTS 作为默认离线测试前提。

## Requirements Interpretation

| Requirement | 可证明的实现结果 |
|---|---|
| `MULTI-01` | 从严格 outcome 的同一 diagnosis 生成固定章节中文 Markdown，英文错误原文和命令字面值保持不变，事实/推断及 ID 支持关系可审计。 |
| `MULTI-02` | Pillow 使用固定字体资产、字体度量、断行和排序在 1600px 宽画布生成单帧无 metadata PNG；超高显式 `png_layout_failed`。 |
| `MULTI-03` | 同一 presentation model 生成 30–60 秒中文 `recap.txt`，经 TTS fallback 生成真实可解码、单音轨 MP3。 |
| `MULTI-04` | 每个 artifact 带同一 `case_id/run_id/diagnosis_sha256/schema_version/generation_version`；发布前逐一比对并写哈希。 |
| `MULTI-05` | PNG 失败保留文字/音频；TTS 按 Dify → edge → SAPI+FFmpeg 降级；manifest/UI 显示 backend、attempt、reason。 |
| `UX-01` | Gradio Blocks 单页只展示已验证的脱敏输入、六字段、证据、报告、PNG、音频和引用。 |
| `UX-02` | 下载路径只来自重验后的 result manifest；完整或 partial ZIP 均含明确身份、成员清单和校验值。 |
| `UX-03` | 固定 fixture/evidence allowlist 经同一 loader/verifier 后回放；UI、manifest、ZIP 三处标记 replay。 |
| `UX-04` | `ResultViewState` 明确 failed stage、completed/inherited stages、retry scope、安全错误码和仍可用产物。 |

## Standard Stack

### Runtime dependencies

| Dependency | Pin / contract | Boundary |
|---|---|---|
| CPython | `>=3.13,<3.14`；本机 3.13.5 | `zipfile`、`subprocess`、`pathlib`、原子文件操作。 |
| Pydantic | `2.13.4` strict + `extra='forbid'` + frozen | `ArtifactIdentity`、`ResultManifest`、`ResultViewState`、TTS attempts、probe results。 |
| Pillow | `12.3.0` | 唯一 PNG renderer；`ImageFont.truetype`、`getbbox/getlength` 进行确定性度量。 |
| HTTPX | `0.28.1` | Dify TTS 适配器；显式 connect/read/write/pool timeout，禁止记录响应 body/Authorization。 |
| Gradio | `6.20.0`（待安装） | `Blocks/Row/Column/Tabs/Markdown/Image/Audio/Dataframe/DownloadButton/State`；仅 UI/事件适配。 |
| edge-tts | `7.2.8`（待安装） | 网络 fallback；仅适配器内使用，固定中文 voice 与离散 rate 档位。 |
| FFmpeg/ffprobe | 本机 `8.1` | SAPI WAV→MP3；所有后端共同媒体探测。调用参数列表，不经 shell。 |
| Windows SAPI | `SpVoice` + `SpFileStream` | 最后一个本地 TTS fallback；选择明确中文 voice，先输出 WAV。 |

### Official API facts that affect design

- Gradio `Audio` 输出可接收 `str|Path`，`interactive=False` 时只播放；`format='mp3'` 可声明输出格式，`buttons=['download']` 是 6.x 下载入口。不要提供 upload/microphone sources。
- Gradio event 默认 queue；`trigger_mode='once'` 可阻止 pending 期间重复提交，`concurrency_id` 与 `concurrency_limit=1` 可按 case 串行。业务幂等键仍必须在服务层实现，不能只信 UI disabled 状态。
- `DownloadButton` 输出接受 `str|Path`。因此回调必须在返回前从磁盘重验 manifest、路径 confinement 和哈希；不能把浏览器输入原样返回。
- Dify 当前官方索引将“Convert Text to Audio”列为所有 app 类型可用的 Audio API；密钥只应从后端调用。适配器以 `POST /text-to-audio`、Bearer key、JSON `text`/`user` 为兼容目标，但必须以真实账号 smoke 捕获当前 content type、错误码和响应上限，不能由 fixture 推断成功。
- edge-tts 是第三方项目，使用 Edge 在线语音服务且不需要 API key；支持 voice、rate、volume、pitch，当前 release 为 7.2.8。它不是离线或 Microsoft 官方稳定 SDK，任何网络/协议错误必须进入安全 fallback。
- `ffprobe` 可用 `-show_entries` 精确输出字段。推荐 JSON 命令：`ffprobe -v error -show_entries format=duration:stream=index,codec_type,codec_name,channels -of json <file>`；只接受恰好一个 `codec_type=audio` stream、可解析正 duration、30–60 秒。
- Python `zipfile.ZipInfo` 可固定 `date_time`；`writestr(ZipInfo, bytes)` 避免继承磁盘 mtime。成员名必须 POSIX 相对路径，固定排序、固定 `create_system/external_attr/compress_type/compress_level`，清空 `extra/comment`，才能跨重复运行保持字节稳定。
- Pillow PNG metadata 只有显式 `pnginfo`/ICC/EXIF 等才应写入；仍需保存后重新打开，要求 PNG、单帧、正确尺寸且 `image.info == {}`。字体文件 hash 必须进入 renderer identity，因为不同字体版本会改变断行和像素。

## Architecture Patterns

### 1. 单向、分层的结果派生

```text
verified DiagnosisRunOutcome + verified source evidence
                 |
             OutcomeLoader
                 |
        immutable PresentationModel
          /          |           \
  ReportRenderer  CardRenderer  RecapComposer
                                  |
                          TtsFallbackChain
          \          |           /
          ResultConsistencyGate
                 |
      atomic ResultBundlePublisher
                 |
         ResultApplicationService
                 |
          pure ResultViewState
                 |
             Gradio Blocks
```

依赖方向只向下。renderer 不读取文件系统 manifest；TTS 不读取 diagnosis；publisher 不重写内容；UI 不导入 adapter。所有内容先成为不可变候选，再统一发布。

### 2. 严格输入与身份

`OutcomeLoader` 只接收 `DiagnosisRunOutcome` 或受控 `(case_id, run_id)`，执行：

1. Pydantic strict round-trip；
2. `status == completed` 且 diagnosis 非空；
3. `validate_diagnosis_outcome()`；
4. 定位 `evidence/<case_id>/<run_id>`，执行 `verify_bundle()`；
5. 对 manifest 的 case/run/schema/facts/knowledge/stage 与 outcome 做恒时或严格比对；
6. 对 `diagnosis.json` 重新校验并计算 canonical `diagnosis_sha256`；
7. 禁止从任意裸 JSON、用户路径或 UI label 绕过。

`ArtifactIdentity` 至少含：`case_id`、`source_run_id`、`diagnosis_sha256`、`schema_version='1.1.0'`、`generation_version`。每个 renderer 返回 `{identity, bytes/text, renderer metadata}`；一致性 gate 不从文件名猜 identity。

`result_id` 应由 canonical JSON（source identity + generation version + selected final backends + artifact hashes + replay semantics）派生为稳定标识。目录用 exclusive create；同路径已存在时只允许“验证后复用”，绝不覆盖。

### 3. PresentationModel 是唯一展示事实源

建立一个严格、冻结的 `PresentationModel`，只包含已验证 diagnosis 的确定性投影：身份、六字段、category/confidence、observed facts、root causes、support links、retrieval citations、commands、missing info、limitations、recap units。所有列表使用稳定 ID 排序，不依赖 provider 顺序或 dict insertion 偶然性。

报告、卡片和讲稿不得再次调用 LLM。允许的转化仅为固定中文标签、排序、长度有界的裁剪、格式和断行。裁剪必须记录（例如 `card_omitted_count`），不能静默改变诊断含义。

### 4. 报告 renderer

固定章节：身份摘要 → 已观察事实 → 根因候选与证据 → 检查 → 修复 → 验证 → 缺失信息 → 置信度/局限 → 引用。根因前缀固定为“有依据/推断”；事实、候选、证据 ID 保持可复制。命令 fenced code block 保持原文，同时展示平台、影响、预期与回退。

对用户/provider 字符串做 Markdown-safe escaping；命令 fence 需选择不与内容冲突的 fence 长度。禁止 `gr.HTML` 和原始 HTML。渲染后用 `assert_export_safe()` 复扫，并测试英文 traceback/error/package/command 未被翻译或改写。

### 5. Pillow card renderer

- 固定 1600px 宽、固定 margins/paddings/colors/line widths；高度由布局树计算，先 measure 后 paint。
- 字体 resolver 顺序：项目内已批准字体 → Windows allowlist；返回 resolved path + SHA-256。无中文字体时显式失败，不使用不可预测默认 bitmap font。
- 统一 token-aware wrap：英文路径/命令/ID 允许按安全边界断行；中文按字符/标点规则；每行用 `getlength/getbbox` 验证不越界。
- 内容固定顺序：现象 → 根因 → 检查 → 修复 → 验证；每块保留 ID/证据编号与置信度。
- 设明确 `MAX_PNG_HEIGHT` 和每 section 上限；超过返回 `png_layout_failed`，不裁切、不缩成不可读字号、不生成伪占位。
- 以 `RGB` 单帧保存，不传 pnginfo/exif/icc/dpi；重新打开校验 `format='PNG'`、`n_frames=1`、宽高、`info == {}`，再经过已有 PNG sanitizer/scan。
- 像素 golden 只在固定提交字体资产时可靠；Windows fallback 情况验证布局不溢出、身份与 metadata，比对 perceptual/结构属性而非固定全图 hash。

### 6. Recap 与 TTS fallback

`RecapComposer` 从同一 presentation model 构造六段：现象、首要根因、一个检查动作、一个修复动作、一个验证动作、局限。它应先按内容预算选择，再用固定标点输出；`DiagnosisRecord.recap_text` 可作为素材但不是绕过结构/隐私/时长门禁的自由稿。

不要用字符数直接声称时长。第一次生成后必须真实 probe；时长不合规时，同一 backend 只允许一个离散 rate retry。推荐固定 rate 表（例如 default、`+15%` 或 SAPI 相邻整数档），禁止无限二分或动态改写文本。每次 `AudioAttempt` 记录 backend、rate profile、started/completed、safe error code、duration、hash；不记录密钥、原始 HTTP body、绝对路径。

统一 port：`synthesize(text: SafeRecapText, *, rate_profile) -> AudioCandidate`。候选只能写临时目录，经过 MP3 signature、ffprobe、单音轨、duration、输出隐私二进制扫描后才能进入 publisher。

- `DifyTtsAdapter`：HTTPX 同步适配即可；API key 环境变量；限制最大 response bytes；只接受预期 audio content type，异常 body 不落盘。
- `EdgeTtsAdapter`：直接 Python API，固定批准的简体中文 voice；async 边界封装在 adapter 内；网络超时/NoAudioReceived 等映射为固定错误码。
- `SapiTtsAdapter`：用受控 PowerShell/COM 或独立 Python Windows adapter 生成 PCM WAV，再以参数数组调用 FFmpeg `-nostdin -y -i input.wav -map 0:a:0 -ac 1 -codec:a libmp3lame ... output.mp3`。临时路径由应用创建；不得把文本或路径拼进 shell 字符串。voice identity 与 rate 进入 manifest。

三个后端都失败时发布 `partial`（有 report/card/recap.txt，无 recap.mp3）；绝不写空 MP3。PNG 失败与 TTS 失败正交，可分别形成 partial。若报告/身份/来源/隐私门禁失败则 fail closed，不发布可交付结果。

### 7. Result bundle 与确定性 ZIP

新建 result publisher，而不是向 Phase 3 evidence bundle 追加。推荐成员：

```text
diagnosis.json
report.md
card.png                 # available 时
recap.txt
recap.mp3                # available 时
citations.json
source-manifest.json     # allowlisted summary/copy
result-manifest.json
checksums.sha256
debugmate-result[-partial].zip
```

发布顺序：创建 `.tmp-<result_id>` → 写候选 → 逐文件复扫/重验 → 写 manifest → 写 checksums → 从磁盘重新读取成员生成 ZIP → 验证 ZIP CRC/成员/manifest/hash → 原子 rename。ZIP 不包含自身 checksum；result manifest 可记录 ZIP hash，但必须避免 manifest↔ZIP 自引用循环：建议外层目录 manifest 记录 ZIP hash，ZIP 内嵌的 manifest 明确是 archive manifest 且不记录 archive 自身 hash，或把 package hash 放在独立外层 publication record。计划必须冻结其中一种无环合同。

使用 `ZipInfo` 逐成员 `writestr`：排序、POSIX allowlist name、固定 `(1980,1,1,0,0,0)`、固定 deflate level、`create_system=3`、固定只读 file mode、空 extra/comment。重复构建测试要求 ZIP SHA-256 相同。

partial 包必须在 status、文件名、缺失产物、失败节点和 retry scope 中一致标注。下载前再次 `verify_result_bundle()`；UI 只获得 verifier 返回的 resolved allowlisted path。

### 8. Application service 与 Gradio

`ResultApplicationService` 是唯一 UI facade：compose、load replay、rerun correction、retry stage、restore by verified manifest、resolve download。它返回严格 `ResultViewState`，不抛 raw exception 给组件。

Gradio 回调只做 strict input parsing → application service → pure `render_state(state)`。状态/可见性/interactive/labels/values 由纯函数一次映射，不能用“文件是否存在”推断 completed。长操作使用 queue + 固定阶段事件；无虚构百分比。相同 case 使用 concurrency group + 服务层 idempotency lock，刷新后从已验证 manifest 恢复。

原生组件边界：Markdown（报告）、Image（只读 filepath，禁止 share/download toolbar）、Audio（只读 MP3）、Dataframe（引用）、DownloadButton（ZIP）、File（可选单文件）。所有事件 endpoint 设为 private/undocumented（若无需外部 API），launch 默认 `share=False`、绑定 loopback；课程演示若开放 LAN 必须单独确认。

## Codebase Integration Map

| Existing asset | Phase 4 use | Rule |
|---|---|---|
| `contracts.py::DiagnosisRecord` | presentation source | strict revalidate; canonical hash from `model_dump(mode='json')`. |
| `diagnosis/workflow.py::DiagnosisRunOutcome` | loader input/status lineage | call public `validate_diagnosis_outcome`; accept completed only for normal generation. |
| `evidence.py::verify_bundle` | source evidence gate | verify source before every compose/replay/restore; do not weaken audio rejection in Phase 3 bundle. |
| `hashing.py` | canonical identity, file hashes, confinement | reuse; never duplicate loose path logic. |
| `privacy/output_scan.py::assert_export_safe` | report/recap/manifest/citations scan | scan model values and rendered text; errors remain value-free. |
| `gateway.py::rerun_diagnosis_json` | correction path | UI delegates strict overlay/rerun; creates new run/result. |
| Phase 3 fixtures | offline outcome/evidence source | add committed verified replay index; do not label fixture as live. |

Recommended new packages/modules (names discretionary, boundaries not):

```text
src/debugmate/results/contracts.py
src/debugmate/results/loader.py
src/debugmate/results/presentation.py
src/debugmate/results/report.py
src/debugmate/results/card.py
src/debugmate/results/audio.py
src/debugmate/results/tts/{base,dify,edge,sapi}.py
src/debugmate/results/media.py
src/debugmate/results/publisher.py
src/debugmate/results/service.py
src/debugmate/ui/app.py
src/debugmate/ui/presentation.py
```

## Don't Hand-Roll

- 不手写 MP3 parser/duration estimator；signature 只做首筛，权威媒体结构交给 ffprobe。
- 不用 LLM、图像生成、Mermaid/浏览器截图生成诊断卡；使用 Pillow。
- 不写自定义前端 framework/audio player/file server；使用 Gradio 原生组件。
- 不把 Windows COM 细节泄漏到领域层；封装 SAPI adapter。
- 不从文本猜 package/version/error category；消费 Phase 3 facts/diagnosis。
- 不用 `shutil.make_archive` 或 `ZipFile.write` 直接继承 mtime；显式 ZipInfo。
- 不复制 Phase 3 validator；调用其公共入口并额外验证 source bundle。
- 不在 UI callback 拼 shell、执行诊断命令或接收任意路径。

## Common Pitfalls

1. **身份循环或漂移。** `result_id`、manifest 和 ZIP hash 若互相包含会形成不可解循环。先冻结无环 publication contract。
2. **把 TTS 音频当确定性。** 报告/布局可 deterministic；在线 TTS bytes 可能漂移。记录实际 backend/version/voice/rate/hash，不做跨时间音频 hash 承诺。
3. **只靠字符数判断 30–60 秒。** 必须 synthesize 后 ffprobe；最多一次固定 rate retry。
4. **Pillow 默认字体或系统字体漂移。** 记录实际 font hash；最好把许可允许的中文字体资产纳入 repo，否则 golden 限于结构/layout。
5. **PNG metadata 清理不完全。** copy/save 后 reopen，拒绝 `info`、APNG、多帧、错误尺寸。
6. **Gradio 把返回路径复制到 cache。** 路径即使来自 server 也须在返回前即时重验；临时路径不得显示给用户。
7. **UI 从缺文件推断状态。** partial/failed 必须来自 manifest/status machine，缺文件可能是篡改。
8. **Markdown 注入/HTML。** 内容 escaping + 不使用 unsanitized HTML；URL 只来自 verified citations。
9. **fake MP3 只满足 header。** 默认测试 fixture 必须是可解码真实短媒体；duration 边界可通过生成 WAV→MP3 fixture 覆盖。
10. **在线 smoke 污染默认 suite。** Dify/edge/浏览器 visual tests 用显式 marker，缺凭据 clean skip 并留外部门禁记录。
11. **并发覆盖。** disabled button 不足；exclusive directory、idempotency key 和 per-case lock 都要有。
12. **partial 冒充完整。** UI、ZIP filename、manifest 三处必须一致，且 Phase 5 delivery gate 只能接受 completed。

## Security Threat Model Inputs

| ID | Threat | Required mitigation / test |
|---|---|---|
| T4-01 | 伪造/篡改 outcome 绕过 Phase 3 | strict round-trip + public validator + source evidence verifier + diagnosis hash cross-check. |
| T4-02 | result path traversal/symlink swap | ID-derived paths、resolve confinement、拒绝 symlink/reparse、返回下载前再校验。 |
| T4-03 | ZIP slip/危险成员 | 只从固定 allowlist 生成；POSIX 相对路径；拒绝 absolute/drive/`..`/NUL/反斜杠。 |
| T4-04 | report/Markdown/URL 注入 | output scan、escape、无 raw HTML；URL 仅 verified official metadata。 |
| T4-05 | PNG 隐写 metadata/多帧/超大图 DoS | pixels-only re-encode、单帧/info empty、width/height/pixel caps、文本长度 caps。 |
| T4-06 | TTS 外传秘密 | adapter 参数只接受 `SafeRecapText`；调用前输出复扫；日志 value-free。 |
| T4-07 | 恶意/超大音频响应 | HTTP byte cap、临时文件、signature+ffprobe timeout、stream/duration/channel caps。 |
| T4-08 | 命令注入到 FFmpeg/PowerShell | `shell=False` 参数数组；固定 executable；用户文本不作为命令参数脚本片段。 |
| T4-09 | 任意文件下载 | UI 无 path input；service 根据 verified manifest member ID 解析。 |
| T4-10 | 重放误标为实时 | replay allowlist、fixture/source identity cross-check；UI/manifest/ZIP 强制三处标记。 |
| T4-11 | 并发重复发布/TOCTOU | exclusive temp/final dirs、per-case lock、publish/read-before-return verification。 |
| T4-12 | 原始 provider body/异常泄漏 | 固定错误码和安全摘要；raw body/traceback/absolute temp path 不进 state/manifest/UI。 |
| T4-13 | ZIP bomb/不受控资源 | 文件数、每成员与总 uncompressed bytes 上限；验证 compression ratio 和 CRC。 |
| T4-14 | 旧/不完整 result 恢复 | generation/schema/source identity exact match；unknown version fail closed。 |

## Recommended Implementation Decomposition

计划应保持顺序依赖，建议 7 个 plan/wave：

1. **04-01 Result contracts + loader**：严格 identity/manifest/status，source bundle 重验，canonical diagnosis hash，失败合同。
2. **04-02 Presentation + Markdown**：唯一 presentation model、报告、citations、隐私复扫；覆盖 `MULTI-01`。
3. **04-03 Pillow card**：font resolver、layout、render/reopen gate、layout partial；覆盖 `MULTI-02` 与 PNG 部分降级。
4. **04-04 Recap + media/TTS ports**：deterministic recap、ffprobe、fake adapter、Dify/edge/SAPI adapters、fallback；覆盖 `MULTI-03/05`。
5. **04-05 Consistency + atomic result publisher**：artifact identity、result manifest、partial/full、确定性 ZIP、tamper verification；覆盖 `MULTI-04`、`UX-02`。
6. **04-06 Service + replay + Gradio UI**：pure view-state mapping、queue/idempotency、correction/retry、allowlisted downloads、UI spec；覆盖 `UX-01/03/04`。
7. **04-07 Integrated gates**：offline E2E、security abuse、真实 SAPI smoke、可选 Dify/edge smoke、Gradio browser visual/a11y QA、全 suite 和 secret scan。

04-02 与 04-03 可在 04-01 后并行；04-04 也可并行，但 04-05 必须等待三类候选合同稳定。04-06 必须等待 publisher/service contract；04-07 最后执行。

## Validation Architecture

### Test layers

| Layer | Scope | Default gate |
|---|---|---|
| L0 contract/static | strict models、schema、Ruff、import、dependency pins | 每个 task；阻断 |
| L1 unit/property | canonical identity、ordering、escaping、wrap、duration parser、ZIP metadata | 每个 task；阻断 |
| L2 artifact integration | report/PNG/MP3/result bundle/ZIP 的真实文件验证 | 每个 plan；阻断 |
| L3 service E2E | fixed completed/partial/failed/replay/correction outcomes | 04-05/06；阻断、完全离线 |
| L4 UI structural | app build、component registry、pure visibility matrix、private events | 04-06；阻断、离线 |
| L5 local media smoke | 真 SAPI→WAV→FFmpeg→ffprobe、中文字体 render | 04-04/07；本机阻断，其他环境显式 skip |
| L6 external smoke | Dify TTS、edge-tts | 显式 marker；无凭据/网络 clean skip，但课程演示前必须现场关闭门禁 |
| L7 browser visual/a11y | 1366/1024/768、15 个 UI-SPEC 场景、键盘/zoom/overflow | 04-07；真实浏览器证据 |

### Nyquist sampling rules

- 每个 production behavior 在同一 plan 中至少有一个 automated verification；不能把所有验证推迟到 04-07。
- 每个 renderer 至少覆盖 success、boundary、malicious/oversize、identity mismatch、privacy failure。
- 每个 fallback edge（Dify→edge、edge→SAPI、all failed、duration retry）都有离线 fake adapter 测试；真实网络只验证 adapter contract，不承担分支覆盖。
- 每个 result status（completed/partial PNG/partial TTS/failed/replay）同时覆盖 manifest、ZIP allowlist 和 UI visibility。
- 每个文件型验证必须从落盘文件重新读取，不以 renderer 返回对象证明发布成功。

### Required fixtures

1. 已验证 `ModuleNotFoundError` completed source evidence（默认 replay）；
2. 含长英文命令/Windows 路径占位符/中文长段落的安全 diagnosis；
3. 最大安全长度与超高 PNG layout case；
4. 可解码 mono MP3 fixtures：29.9s、30s、45s、60s、60.1s（可测试时生成或保存小型压缩资产）；
5. multi-audio-stream、corrupt header、non-MP3、metadata/tag payload；
6. tampered source/result manifest、hash、extra member、symlink/path traversal；
7. Dify/edge fake responses（success、timeout、wrong content type、oversize、HTTP errors）；
8. completed/partial/failed/replay `ResultViewState` matrix。

### Core automated assertions

**Identity/contracts**
- strict models reject dict coercion、extra fields、unknown versions；
- canonical diagnosis hash stable under serialization round-trip；
- artifact identity mismatch blocks any final directory；
- result ID stable for identical inputs and changes for generation/backend/artifact changes。

**Report/citations**
- exact section order and stable IDs；fact/inference labels；
- English technical spans and commands byte-for-byte present；
- every displayed citation maps to diagnosis evidence；unsupported URL rejected；
- secret/injection patterns fail without echoing matched value。

**PNG**
- fixed 1600 width、single frame、RGB/RGBA approved mode、metadata empty；
- all measured text boxes within canvas；long token wrapping；
- max-height returns typed `png_layout_failed` with no card file；
- font path confinement/hash/version recorded；repeat render under same font yields same bytes。

**Audio**
- adapter only accepts scanned recap contract；
- subprocess is `shell=False` with fixed args；
- exactly one audio stream、MP3 codec/container policy、30.000–60.000 seconds inclusive；
- duration invalid causes at most one same-backend rate retry；then next backend；
- all failed produces no MP3 and explicit partial state；
- logs/attempts contain no text、key、body、absolute path。

**Publisher/ZIP**
- interrupted/failed publish removes temp and creates no success-looking final dir；
- duplicate never overwrites；tamper/extra/missing member rejected；
- full/partial member allowlists exact；source raw screenshot/provider/log absent；
- `ZipInfo` order/timestamps/attrs/extra/comment fixed；two builds have identical SHA-256；
- unzip then full manifest/checksum/CRC verification passes；traversal member impossible。

**Service/UI**
- pure mapping matrix covers idle/running/completed/partial/failed + replay/fallback orthogonal flags；
- callbacks never return paths outside verified bundle；download revalidation catches post-render tamper；
- duplicate case submit is rejected/idempotently joined；
- correction requires explicit confirmation and creates new run/result；
- replay invalid source yields `replay_bundle_invalid` and no output；
- app builds without network and declares expected native components/events；
- no shell/terminal/auto-install callback and no raw `gr.HTML` content path。

### Suggested markers and commands

Add markers: `tts`（real local SAPI/ffmpeg）、`cloud`（Dify）、`network`（edge）、`browser`（visual）。默认 `pytest` 继续排除外部 marker，但不应排除 deterministic audio/media unit tests。

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m pytest -m tts
.\.venv\Scripts\python.exe -m pytest -m "cloud and tts"
.\.venv\Scripts\python.exe -m pytest -m "network and tts"
```

最终 Phase verifier 还应运行：Pydantic schema round-trip、`git diff --check`、secret scan、result bundle verifier、ZIP repeatability、真实 ffprobe、Gradio app smoke，以及 UI-SPEC VQ-01..VQ-15 的浏览器截图/检查清单。真实 Dify/edge 未运行时必须记录为 external gate open，不能写“通过”。SAPI 本机路径已具备先决条件，应在实现后真实运行，不应只 clean skip。

## Confidence and Open Checks

| Decision | Confidence | Remaining live check |
|---|---|---|
| Result bundle 与 Phase 3 evidence 分离 | HIGH | 实现时验证 source/result manifest 无循环引用。 |
| Deterministic report/PNG/ZIP | HIGH | 若不提交字体资产，PNG byte-golden 仅限当前 font hash。 |
| Gradio 6 native workbench | HIGH | 安装 6.20.0 后做 import/app-config/browser smoke；当前环境缺包。 |
| ffprobe + SAPI/FFmpeg fallback | HIGH on this machine | 生成 30–60 秒中文真实 MP3 并验证 voice/rate/mono。 |
| edge-tts fallback | MEDIUM | 安装 7.2.8 后真实中文 voice/network smoke；服务非官方稳定 API。 |
| Dify TTS primary | MEDIUM | 当前无凭据；需真实确认 endpoint、provider、content type、额度和时长。 |
| UI browser accessibility | MEDIUM-HIGH | 必须在实现后的真实 DOM/浏览器验证，静态 spec 不足以证明。 |

## Sources

Primary/official sources checked 2026-07-13:

- Gradio: [Blocks/queue](https://www.gradio.app/main/docs/gradio/blocks), [Audio](https://www.gradio.app/docs/gradio/audio), [Image](https://www.gradio.app/docs/gradio/image), [DownloadButton](https://www.gradio.app/docs/gradio/downloadbutton), [Progress](https://www.gradio.app/docs/gradio/progress/).
- Dify: [API documentation index](https://docs.dify.ai/llms.txt), [API get started and backend-only key guidance](https://docs.dify.ai/en/api-reference/guides/get-started).
- Pillow 12.3: [PNG save/metadata options](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#png), [ImageFont metrics](https://pillow.readthedocs.io/en/stable/reference/ImageFont.html).
- Python 3.13: [`zipfile` and `ZipInfo`](https://docs.python.org/3.13/library/zipfile.html).
- FFmpeg: [`ffprobe` documentation](https://ffmpeg.org/ffprobe.html).
- Microsoft: [SAPI 5.3 `SpVoice`](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms723602(v=vs.85)).
- edge-tts upstream: [repository/readme and 7.2.8 release](https://github.com/rany2/edge-tts).
- Live local evidence: `.venv` package metadata, `ffprobe -version`, Windows Fonts directory, SAPI `GetVoices()`, and environment-variable name presence checks performed 2026-07-13; no product files were mutated by those checks.

---

*Research output for downstream `/gsd-plan-phase`; no implementation or plan files were created.*
