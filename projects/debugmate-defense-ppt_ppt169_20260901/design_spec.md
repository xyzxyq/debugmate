<!-- ppt-master-schema: design-spec/v1 -->
# debugmate-defense-ppt - Design Spec

## I. Project Information

| Item | Value |
| --- | --- |
| Project Name | debugmate-defense-ppt |
| Canvas Format | PPT 16:9 (1280×720) |
| Page Count | 15 |
| Target Audience | 《校外实训》课程教师与同学；具备 Python 基础，需要快速理解项目价值、技术路线和真实证据边界 |
| Communication Intent | 以一个真实可复现的 Python 报错贯穿答辩，解释 DebugMate 如何通过隐私闸门、官方知识检索、结构化诊断和同源多模态产物完成课程闭环，同时如实报告 Dify 云端限制 |
| Desired Audience Outcome | 听众能够复述系统的输入—诊断—产物链路，理解其可追溯性与安全边界，并能区分 Dify live、本地 fallback 和固定 replay |
| Core Message / Ask / Action | DebugMate 把“修好一次报错”转化为“有依据、可检查、可复盘”的学习过程；请以真实证据而不是云端宣传判断项目完成度 |
| Delivery Context | 主讲人现场投影答辩；文件同时作为课程复核和项目交接材料；预计 8–10 分钟 |
| Artifact Afterlife | 课程答辩、课后复核、演示视频配套和项目交接 |
| Reading Mode | presentation |
| Content Strategy | 叙事模式：真实案例开场，随后解释问题、边界、架构、证据和结果，最后以限制与演示顺序收束；页面承载核心句，讲解承载细节 |
| Design Style | editorial technical briefing：浅色纸面、深石墨文字、青绿系统色、橙色风险/重点色；真实截图作为证据面板，技术图用原生 SVG/PPT 元素绘制 |
| AI Image Acquisition Path | 使用内置 imagegen 生成 1 张无文字封面概念图，仅作视觉引导；真实 UI 与运行证据全部来自仓库 |
| Generation Mode | default generate PPTX；free design；flat slide-local SVG，使用 ppt-master 导出 |
| Spec Refinement | disabled；大纲已由用户确认 |
| Speaker Notes | disabled；本次交付为答辩视觉稿，讲解内容由 `docs/course/video-script.md` 维护 |
| Custom Animations | disabled；保持静态、可打印、可复核 |
| Narration Audio | disabled；不在 PPTX 中嵌入音频 |
| Created Date | 2026-09-01 |

## II. Canvas Specification

| Property | Value |
| --- | --- |
| Format | PPT 16:9 |
| Dimensions | 1280×720 |
| viewBox | `0 0 1280 720` |
| Margins | 56 px left/right, 38 px top, 32 px bottom |
| Content Area | x=56..1224, y=38..688 |

## III. Visual Theme

### Theme Style

- **Mode**: custom narrative technical briefing: case → problem → system → proof → boundary → close
- **Visual style**: custom editorial technical briefing with evidence panels and diagrams
- **Theme**: “evidence spine” — a recurring vertical teal rule and orange section marker connect every page
- **Tone**: precise, calm, credible, student-friendly, candid about uncertainty

### AI Image Strategy

- Generate one text-free cover concept image with the built-in image generation tool; use it only as visual framing.
- Use repository screenshots and deterministic Pillow outputs for all runtime evidence; never use generated imagery as proof of execution.

### Color Scheme

| Role | HEX | Purpose |
| --- | --- | --- |
| Background | #F7F5EF | warm paper background |
| Primary | #14212B | titles, architecture, high-contrast anchors |
| Accent | #0F9D8A | system flow, evidence, positive status |
| Body text | #33424D | readable body copy |
| Secondary accent | #F0784A | risk, boundary, callouts |
| Muted panel | #E7ECE9 | cards, code panels, secondary zones |

## IV. Typography System

### Font Plan

| Role | Character (Reference) | Primary | English if non-English | Fallback tail |
| --- | --- | --- | --- | --- |
| Title | Microsoft YaHei | Microsoft YaHei | Aptos Display | Arial |
| Body | Microsoft YaHei | Microsoft YaHei | Aptos | Arial |
| Code | Cascadia Mono | Cascadia Mono | Consolas | Courier New |

- **Typography upgrade (Reference)**: none; use the locked Microsoft YaHei/Aptos fallback stacks
- **Title stack**: Microsoft YaHei, Aptos Display, Arial
- **Body stack**: Microsoft YaHei, Aptos, Arial

### Font Size Hierarchy

| Purpose | Size |
| --- | --- |
| Body | 22 |
| Page title | 34 |
| Subtitle | 18 |
| Annotation | 16 |
| Footnote | 13 |

## V. Layout Principles

### Deck-wide Direction

- **Hierarchy direction**: one claim per page, title first, visual second, evidence label third
- **Composition tendency**: alternating large evidence image, diagrams, comparison, and breathing close pages
- **Cross-page continuity**: fixed top title rail, small section index, teal evidence spine, orange page number marker
- **Spacing posture**: generous outer margins; compact inside diagrams; no dense card wall

## VI. Icon Usage Specification

| Icon Path | Suitable Scenarios |
| --- | --- |
| Native SVG line icons and simple geometric marks | pipeline nodes, privacy shield, knowledge book, report/card/audio outputs; no external icon dependency |

## VIII. Image Resource List

| Filename | Dimensions | Ratio | Purpose | Type | Layout pattern | Crop Policy | Acquire Via | Status | Reference | text_policy | page_role |
| cover-concept.png | 1536×1024 | 3:2 | cover visual: traceback flowing into evidence nodes and three outputs | bitmap | right-side hero with left negative space | adaptive | ai | Generated | generated in current run; no text or watermark | no critical text | P01 |
| 01-completed-overview.png | repository source | wide UI screenshot | real completed workbench evidence | bitmap | framed dominant screenshot | no-crop | user | Existing | `evidence/course-v0.1/screenshots/01-completed-overview.png` | preserve all visible text | P11 |
| 02-tts-partial.png | repository source | wide UI screenshot | real TTS partial failure evidence | bitmap | framed evidence panel | no-crop | user | Existing | `evidence/course-v0.1/screenshots/02-tts-partial.png` | preserve all visible text | P13 |
| 03-card-partial.png | repository source | wide UI screenshot | real PNG partial failure evidence | bitmap | framed evidence panel | no-crop | user | Existing | `evidence/course-v0.1/screenshots/03-card-partial.png` | preserve all visible text | P13 |
| terminal-module-not-found-redacted.png | repository source | terminal screenshot | redacted case input | bitmap | left-side code specimen | no-crop | user | Existing | `tests/fixtures/phase8/terminal-module-not-found-redacted.png` | preserve redaction | P02/P09 |
| card.png | repository source | diagnosis card | actual deterministic visual output | bitmap | output artifact frame | no-crop | user | Existing | `evidence/dify-live/phase8/card.png` | preserve all visible text | P12 |

## IX. Content Outline

### Part 1: Problem and promise

#### Slide 01 - 从报错到复盘：DebugMate

- **Audience move**: 建立项目身份与核心价值，先让听众知道这不是普通聊天机器人
- **Layout**: 大标题左置，AI 概念图右置，底部放三项课程交付标签
- **Title**: DebugMate
- **Core message**: 把一次报错转化为可追溯、可检查、可复盘的学习过程
- **Content**: 面向 AI 专业学习场景的多模态报错诊断与复盘智能体；《校外实训》课程项目；V0.1 本地演示版；有依据 / 可执行 / 说明不确定性
- **Relationships**: cover hook introduces the case-to-learning transformation; none

#### Slide 02 - 从一个真实报错开始
- **Audience move**: 让听众代入学生面对 ModuleNotFoundError 的瞬间
- **Layout**: 左侧真实脱敏终端截图，右侧三条问题注释与一条结论
- **Title**: 从一个真实报错开始
- **Core message**: 错误本身只是一行文字，真正困难是判断下一步该相信什么
- **Content**: ModuleNotFoundError、Python 3.13.5、Windows、导入代码；问题信息分散且环境不确定
- **Relationships**: screenshot evidence supports the three problem annotations; order: symptom → uncertainty → need

#### Slide 03 - 普通问答为什么不够
- **Audience move**: 将项目必要性从“想做 AI”转为三个可观察痛点
- **Layout**: 三个垂直痛点区块，底部用一句设计目标收束
- **Title**: 普通问答为什么不够
- **Core message**: DebugMate 的价值不是回答更多，而是让回答可追溯、可检查、可复盘
- **Content**: 证据缺失、环境不确定、结果难沉淀；设计目标是把一次排错变成学习闭环
- **Relationships**: three parallel pain points converge on one design goal

#### Slide 04 - V0.1 做什么，也不做什么
- **Audience move**: 让听众理解课程版本的完成边界
- **Layout**: 左侧完成项，右侧明确延后项，中间用边界线分隔
- **Title**: V0.1 做什么，也不做什么
- **Core message**: 这是一个可提交、可演示、可复核的课程版本，不伪装成生产服务
- **Content**: 本地浏览器、17 源知识库、隐私确认、三模态产物、代表性案例；延后公网部署、SLA、稳定云端浏览器链路和自动修复
- **Relationships**: equal comparison between committed scope and deferred scope

### Part 2: System and evidence

#### Slide 05 - 一次诊断的完整路径
- **Audience move**: 让听众形成系统全貌
- **Layout**: 横向 6 节点 pipeline，节点下方配输入/输出小标签
- **Title**: 一次诊断的完整路径
- **Core message**: 所有结果都从一次经过确认的诊断对象派生
- **Content**: Input → Privacy Gate → Extraction → Retrieval → DiagnosisRecord → Media/UI
- **Relationships**: ordered pipeline; each stage feeds the next

#### Slide 06 - 技术路线：云端增强，本地闭环
- **Audience move**: 解释为什么 Dify 和本地 Python 不是互相替代
- **Layout**: 两条泳道；上方 Dify Cloud，下方 Local Python；右侧 Git 作为事实源
- **Title**: 技术路线：云端增强，本地闭环
- **Core message**: 云端负责模型编排，本地负责安全、验证和可交付产物
- **Content**: Dify 视觉 / RAG / LLM；Python 脱敏 / Pydantic / Pillow / TTS fallback / Gradio；Git 保存 DSL、知识源、提示词和证据
- **Relationships**: two execution lanes converge on Git-backed evidence; cloud enhances local closure

#### Slide 07 - 系统架构：DiagnosisRecord 是单一事实源
- **Audience move**: 解释模块边界与一致性来源
- **Layout**: 中央 DiagnosisRecord 1.1，左侧输入与证据，右侧报告 / PNG / MP3 / ZIP
- **Title**: 系统架构：DiagnosisRecord 是单一事实源
- **Core message**: 文字、图片、语音不是三个独立答案，而是同一个结构化对象的不同投影
- **Content**: case_id、schema_version、observed_facts、evidence、root_cause_candidates、checks、verification_steps、limitations
- **Relationships**: input and evidence feed the central contract; the contract fans out to four derived outputs

#### Slide 08 - 专属知识库：17 个官方来源
- **Audience move**: 说明“有知识库”具体意味着什么
- **Layout**: 7 类主题的矩阵 + 右下角版本绑定卡片
- **Title**: 专属知识库：17 个官方来源
- **Core message**: 检索不是装饰，来源、版本范围、内容哈希和 knowledge_build_id 都进入证据链
- **Content**: Python、pip/venv、PyTorch、CUDA、Hugging Face、Ultralytics、Windows/PowerShell；无命中时明确记录证据不足
- **Relationships**: seven topic groups belong to one knowledge base; metadata binds every hit to a build

#### Slide 09 - 隐私闸门：先确认，再上传
- **Audience move**: 让听众看到云调用之前发生了什么
- **Layout**: 4 步流程 + 中间展示脱敏前后对照的局部代码块
- **Title**: 隐私闸门：先确认，再上传
- **Core message**: 脱敏不是后台黑盒动作，而是用户可见、可确认的交互门禁
- **Content**: 本机校验 → OCR/正则发现 → 生成脱敏预览 → 用户确认；Token、邮箱、用户名、绝对路径、图片敏感像素和导出物均覆盖
- **Relationships**: ordered privacy gate; confirmation is the prerequisite for cloud submission

### Part 3: Prompt, proof, and honesty

#### Slide 10 - V1–V4：从能回答到可派生
- **Audience move**: 展示工程迭代，而不是只展示最终效果
- **Layout**: 4 段横向演进时间线，每段一个关键词和一个约束
- **Title**: V1–V4：从能回答到可派生
- **Core message**: 提示词优化的终点不是更长，而是让证据、结构和多模态输出保持一致
- **Content**: V1 基础诊断；V2 引用约束；V3 结构可靠；V4 课程定稿；V1 有固定案例 manifest，V2–V4 保留设计迭代边界
- **Relationships**: temporal progression from answer quality to evidence and derivation quality

#### Slide 11 - 一次完整诊断的真实结果
- **Audience move**: 将架构落回可以操作的产品界面
- **Layout**: 大面积真实 Edge 截图，三条 callout 指向输入、证据、结果区
- **Title**: 一次完整诊断的真实结果
- **Core message**: 结果页把脱敏输入、证据、诊断和下载产物放在同一次运行中
- **Content**: 真实工作台截图；标注 local fallback / replay 或 Dify live 的实际状态，不混用
- **Relationships**: dominant screenshot is annotated by three callouts; evidence → interface → deliverables

#### Slide 12 - 三种输出，共享一个身份
- **Audience move**: 证明多模态不是装饰，而是同源派生
- **Layout**: 中心身份链，三侧展示 report / card / audio，底部展示 ZIP
- **Title**: 三种输出，共享一个身份
- **Core message**: `case_id + source_run_id + diagnosis_hash + schema_version` 贯穿文字、图片、语音和 ZIP
- **Content**: 报告包含事实和局限；PNG 用 Pillow 确定性绘制；MP3 使用同一 recap_text；manifest 记录哈希
- **Relationships**: one-to-many derivation from the central diagnosis object; all outputs share identity fields

#### Slide 13 - 失败也要诚实
- **Audience move**: 建立可信度，展示部分完成和最小重试
- **Layout**: 左右两张真实失败截图，中间是最小重试决策树
- **Title**: 失败也要诚实
- **Core message**: 外部节点失败时保留真实失败记录，并只重试失败的产物
- **Content**: TTS 失败保留报告和诊断卡；PNG 失败保留报告和语音；Dify 浏览器 timeout/旧契约明确标记，local fallback 不冒充 cloud success
- **Relationships**: two symmetric failure branches converge on honest partial completion; no false cloud-success edge

### Part 4: Evaluation and close

#### Slide 14 - 评测与自动验证
- **Audience move**: 用数字和案例说明“完成”如何被检查
- **Layout**: 左侧 4 案例矩阵，右侧大号测试数字，底部放质量闸门
- **Title**: 评测与自动验证
- **Core message**: 课程版本以可复算证据为完成标准，而不是以虚构成功率为完成标准
- **Content**: 4 个代表性案例；V1–V4 同输入；1177 passed / 60 deselected；隐私 113 passed；云端合同 1 passed；Phase 9 账本保留明确 blockers
- **Relationships**: case matrix and automated gates jointly support the completion claim; blockers remain attached to cases

#### Slide 15 - 总结：把修好一次变成理解一次
- **Audience move**: 收束项目价值，并给出现场演示路线
- **Layout**: 纵向四段闭环箭头，右下角放演示顺序与限制提醒
- **Title**: 总结：把“修好一次”变成“理解一次”
- **Core message**: DebugMate 已形成课程可提交的多模态诊断闭环，并以真实证据说明云端边界
- **Content**: 报错 → 隐私确认 → 官方知识 → 结构化诊断 → 报告/PNG/MP3/ZIP；演示顺序：预览、确认、诊断、引用、三模态、降级
- **Relationships**: closed-loop sequence returns from diagnosis to learning artifacts; demo order mirrors the system path

## X. Speaker Notes Requirements

- **Generation**: disabled; this deck is a visual defense deck and uses the existing `docs/course/video-script.md` as the speaking aid
- **Filename**: not applicable
- **Content**: no embedded notes; all claims remain visible on slide or traceable to repository evidence
