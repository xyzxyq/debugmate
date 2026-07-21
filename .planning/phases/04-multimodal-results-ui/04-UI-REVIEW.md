# Phase 04 — UI Review

**Audited:** 2026-07-21

**Baseline:** `04-UI-SPEC.md`、最新实现、用户明确反馈“当前前端页面太丑、一点都不友好”

**Screenshots:** inspected current real Edge captures at 1366×768 and 375×812; no fresh capture because no server was available on 3000/5173/8080/7860
**Verdict:** 功能和安全合同扎实，但当前界面仍是“把所有工程能力同时摆出来”的 Gradio 工作台，不是一个新手能轻松完成诊断、理解结论并继续学习的成熟工具。

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 2/4 | 主路径文案已编号，但首屏没有一句价值说明，后端、ID、哈希和工程术语仍比学习结论更抢眼。 |
| 2. Visuals | 1/4 | 1366 px 三列满足最小宽度却同时压窄输入、状态与报告；嵌套卡片、Tabs、Accordion 形成明显 Gradio 原型感。 |
| 3. Color | 2/4 | 浅色基础可读，但顶部状态胶囊无论状态都使用成功绿，固定蓝色强调也没有建立清晰的学习层级。 |
| 4. Typography | 2/4 | 基础字号可读，但标题层级、长 ID/hash、Markdown 大标题和移动端代码行共同制造高噪声阅读。 |
| 5. Spacing | 2/4 | 间距基本整齐，却被三列约束和容器套容器消耗；14 px 非标间距、空头部和长纵向堆叠降低效率。 |
| 6. Experience Design | 2/4 | 状态真实性、隐私、重试和可访问性很强，但新手仍要理解预览、后端、回放、纠错、Tabs 与技术详情，认知负担过高。 |

**Overall: 11/24**

---

## Top 3 Priority Fixes

1. **P0 — 放弃 1366 px 三列常驻，改成“输入侧栏 + 主结果区”的两区布局** — 当前约 280 / 373 / 467 px 的三列让输入、结论和报告都像窄长信息筒；完成态也没有一个足够宽的主阅读面 — 桌面端用 320–360 px 输入侧栏 + `minmax(0, 1fr)` 主区，状态概览放入主区顶部，诊断完成后让“结论 → 下一步 → 报告”占据主要宽度；证据和恢复信息继续折叠。
2. **P0 — 默认只呈现学生可读结论，不直接展开完整工程报告** — 当前完成截图中案例 ID、run ID、诊断哈希、Schema、生成版本、事实/证据 ID 和英文枚举占据视觉主体 — 首屏结果固定为“发生了什么 / 最可能原因 / 先做什么 / 如何验证”四段；完整 Markdown artifact 原样保留在“完整技术报告”披露区和证据包下载中，不能删除、改写或伪造。
3. **P0 — 把一次诊断收敛成单一向导并给出明确完成反馈** — 新手当前同时看到两个按钮、后端、示例、三个区域和四个结果 Tab；完成后仍需自己判断下一步 — 空闲态只强调“粘贴/确认脱敏内容 → 开始诊断”，完成后自动聚焦结论并显示唯一主行动；回放、纠错、重试、引用和技术身份按状态渐进出现。

---

## Priority Implementation Backlog

### P0 — 下一轮必须完成

1. **重构信息架构，不再把“三列可见”当作产品目标。**
   - `>= 1100px`：输入侧栏 320–360 px，主结果区占剩余宽度。
   - 完成态主区顺序：状态与结论 → 第一步行动 → 报告摘要 → 三模态切换 → 技术披露。
   - 900–1099 px 与移动端都按同一阅读顺序堆叠，不让用户先走完整个输入/技术区才看到结果。
2. **建立“学生摘要”和“证据原文”双层展示。**
   - 默认摘要禁止出现 case/run/result ID、SHA-256、Schema、generation version、fixture 空值、fact/evidence ID 和原始枚举。
   - 这些字段只进入 `技术详情与恢复信息`，保持可复制、可验证、不可伪造。
   - 原始 `report.md` 继续使用 native Markdown，但放入“完整技术报告”折叠区或次级 Tab。
3. **修复移动端命令可读性。**
   - 375 px 截图中第一步命令已在窄卡片内被截断；代码容器必须局部横向滚动或安全换行，并显示“复制命令”。
   - 移动端结果摘要应在输入完成后紧接状态出现；技术详情、复盘稿和引用后置。
4. **给首屏补一行价值说明。**
   - 保留标题 `DebugMate 学习诊断助手`。
   - 标题下增加不超过 24 个汉字的说明，例如：`粘贴报错，获得有依据的原因、检查步骤和复盘材料。`
   - 缩短顶部容器高度，不用大块空白承载标题和一个状态胶囊。

### P1 — 结构完成后跟进

1. **减层级：** 每个区域最多一层主表面；删除 `region → summary card → next-step card → inner card` 的连续边框嵌套。Tabs 只承载真正互斥的三模态，不再承担技术详情分组。
2. **统一视觉尺度：** 页标题 18 px、区标题 16 px、正文 14–16 px、元数据 12–13 px；半径统一 8 px；间距只用 8/12/16/24/32 px。
3. **修复状态色：** 顶部状态必须随 neutral/blue/green/amber/red 切换；当前 `.status-indicator p:first-child` 固定成功绿，等待、运行和失败都会产生错误暗示。
4. **降低 Gradio 默认控件感：** 保留 native 语义和禁用行为，但统一标签位置、边框、选中态和按钮权重；主按钮每个状态只保留一个，次要动作改为文本按钮或披露入口。
5. **让报告真正可扫读：** 限制正文阅读宽度约 70–80 个中文字符；H2/H3 不超过页面标题；长 ID 用短前缀显示 + 复制完整值，不在正文中连续换行。

### P2 — 打磨与课程演示

1. 为完成态增加轻量的“诊断已完成，建议先做以下检查”反馈，而不是只改变状态徽标。
2. 为三模态结果显示可用性摘要，例如 `文字 ✓ / 诊断卡 ✓ / 语音 ✓`，部分失败时直接说明缺少哪一项。
3. 为首个真实案例录制一次 30 秒可用性走查：从空闲态到理解结论，记录点击数、首次看到原因的时间和犹豫点。
4. 重新生成桌面空闲、桌面完成和移动完成截图，人工检查视觉焦点、阅读顺序和代码完整性；不能只依赖“无 overflow”断言。

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

做得好的部分：主路径已经改为 `1. 生成脱敏预览` → `2. 确认并开始诊断`，第二步在预览前禁用；空闲态也明确说明“两步开始诊断” ([app.py](../../../src/debugmate/ui/app.py#L1296), [presentation.py](../../../src/debugmate/ui/presentation.py#L276))。

主要问题：

- 首屏虽然有 `DebugMate 学习诊断助手`，却没有解释“它能帮我得到什么”。用户只能从三个区域标题推断产品价值；这对第一次打开页面的学生不友好 ([app.py](../../../src/debugmate/ui/app.py#L1266))。
- `后端：local-rule-v1（本地规则，无云端调用）` 在主要输入流中永久出现。它是重要真实性信息，但不是开始诊断前的决策信息，应进入“运行与隐私说明”或完成态技术详情 ([app.py](../../../src/debugmate/ui/app.py#L1307))。
- 真实运行元数据仍输出 `fixture_id=null；fixture_name=null`，这是实现验证语言，不是用户语言 ([presentation.py](../../../src/debugmate/ui/presentation.py#L172))。
- 完成截图中的完整报告直接展示案例 ID、来源运行 ID、诊断哈希、Schema、生成版本和事实 ID。信息都是真实的，但默认层级错误；学生先看到的是系统内部身份，而不是“为什么报错、先做什么”。
- `开始` kicker 与 `开始诊断` 标题重复，底部安全说明也在技术详情和页面底部重复。应减少重复标签，把文字预算留给价值说明和下一步反馈 ([app.py](../../../src/debugmate/ui/app.py#L1283), [app.py](../../../src/debugmate/ui/app.py#L1455))。

### Pillar 2: Visuals (1/4)

最新空闲桌面截图清楚显示三列都“存在”，但没有形成主次：左列是表单，中列是说明，右列是空结果；三块等高白卡并排，用户不知道视线应该先落在哪里。完成截图更严重：右列长报告成为窄列文档，中列结论和下一步被压成多个小卡，左列仍长期占据近四分之一屏幕。

源码把桌面固定为 `minmax(280px, .8fr) / minmax(360px, 1fr) / minmax(460px, 1.3fr)` ([app.py](../../../src/debugmate/ui/app.py#L126))。测试只要求三列分别不小于 280/360/440 px 且无 body overflow ([test_browser.py](../../../tests/ui/test_browser.py#L2404))；这证明布局没有坏，却不能证明输入、结论和报告都足够舒适。

视觉层级过多：

- 顶部是一张带阴影的卡片；主体再分三张区域卡；中列又有结论卡和下一步卡；右列又有 Tabs、结论速览卡和 Markdown 报告 ([app.py](../../../src/debugmate/ui/app.py#L86), [app.py](../../../src/debugmate/ui/app.py#L207), [app.py](../../../src/debugmate/ui/app.py#L231), [app.py](../../../src/debugmate/ui/app.py#L1393))。
- 输入区还叠加示例 Accordion、纠错 Accordion 和二次确认 Accordion。结构合理但视觉上像把所有 Gradio 组件能力逐项陈列。
- 顶部标题和状态之间留有大量空白，却没有副标题、关键动作或结果摘要；空间使用与信息价值不匹配。

这不是“配色再调一点”能解决的问题，必须重构主次和页面区域。

### Pillar 3: Color (2/4)

优点是浅色画布、白色表面、深色正文和蓝色主操作具有基本可读性；overview 已经能按 neutral/blue/green/amber/red 使用不同左边框和背景 ([app.py](../../../src/debugmate/ui/app.py#L207))。

但顶级状态语义仍有明显错误：`.status-indicator p:first-child` 固定使用 `--success` 和 `--success-surface`，因此空闲截图中的“等待诊断”也是绿色，运行或失败状态也会继承绿色胶囊 ([app.py](../../../src/debugmate/ui/app.py#L100))。状态文字虽然真实，颜色却在说“成功”。

此外，固定蓝色结果区顶边、蓝色 Tab、蓝色按钮和链接都在竞争注意力 ([app.py](../../../src/debugmate/ui/app.py#L145), [app.py](../../../src/debugmate/ui/app.py#L247))。建议把蓝色只留给当前主行动、选中 Tab 和链接；结构边框使用中性色。

### Pillar 4: Typography (2/4)

- 实现把页标题设为 20 px、区域标题设为 18 px，而 UI-SPEC 分别规定 18 px 和 16 px ([app.py](../../../src/debugmate/ui/app.py#L91), [app.py](../../../src/debugmate/ui/app.py#L154))。偏差本身不大，但三个 18 px 区标题同时出现，进一步强化“三区同权”。
- 表格和元数据大量使用 12 px；单独看满足合同，但完成态中 12 px 的 ID/hash 占比太高，用户会把页面感知为日志查看器 ([app.py](../../../src/debugmate/ui/app.py#L163), [app.py](../../../src/debugmate/ui/app.py#L276))。
- 完整 Markdown 报告的标题、列表、代码和行内 ID 在约 460 px 列中频繁换行，破坏段落节奏。报告虽设置 560 px 内滚动，但只是把长文塞进更小视口 ([app.py](../../../src/debugmate/ui/app.py#L261))。
- 375×812 截图中命令在下一步卡片内横向截断；这属于核心行动不可完整阅读，不应只用“页面无横向 overflow”判为通过。

### Pillar 5: Spacing (2/4)

实现多数使用 8/12/16 px，基础秩序尚可；但仍存在 14 px 页内间距和 next-step padding，不符合已声明的 4 px 倍数尺度 ([app.py](../../../src/debugmate/ui/app.py#L56), [app.py](../../../src/debugmate/ui/app.py#L231))。

更大的问题是空间被错误结构消耗：

- 16 px 三列间隙 + 三列各自 16 px padding，在 1366 px 下从本就有限的阅读宽度继续扣除。
- 多层卡片各自拥有边框、内边距和标题间距，同一屏大量空间用于“容器说明”，不是用于内容。
- 移动端只把三块区域顺序堆叠，没有消除桌面结构；因此用户要滚过完整输入区和概览区才能到结果区 ([app.py](../../../src/debugmate/ui/app.py#L322))。
- 空闲顶部卡高度明显大于实际标题与状态所需，形成无意义留白；完成态则在窄列中变得过密，整体松紧失衡。

### Pillar 6: Experience Design (2/4)

必须肯定的工程基础：状态从严格 `ResultViewState` 映射；idle/running/completed/partial/failed、回放、fallback、七阶段进度、失败七字段、局部重试和 Tab 启用条件都有明确实现 ([presentation.py](../../../src/debugmate/ui/presentation.py#L253), [presentation.py](../../../src/debugmate/ui/presentation.py#L272))。预览 token、下载能力、证据包、技术身份和安全命令边界也不应被 UI 重构削弱。

但新手体验仍不合格：

- 第一次进入就要理解脱敏预览、确认诊断、本地后端、回放案例、问题概览和四个禁用 Tabs。即使控件被禁用，它们仍占据认知空间。
- 诊断完成后没有把用户带到“结论 + 第一步行动”；输入侧栏仍常驻，完整报告立即展开，用户需要自己在三列间寻找变化。
- 当前浏览器测试详细验证了可见、可禁用、键盘可达、无溢出、可下载和身份一致性，但没有验证“学生几秒内能否说出原因和下一步” ([test_browser.py](../../../tests/ui/test_browser.py#L552), [test_browser.py](../../../tests/ui/test_browser.py#L1555))。
- 移动端顺序技术上是输入 → 概览 → 结果，但完成后仍沿用表单优先；对结果查看任务不合理。

建议新增体验验收：新用户在结果完成后 5 秒内能指出“最可能原因”和“第一步检查”；空闲态在 3 秒内能指出唯一下一步；完成一次诊断不需要理解 fixture、backend、run ID 或 hash。

---

## Safety and Evidence Contracts to Preserve

UI 重构不得牺牲以下合同：

- `ResultViewState` 与严格 `DiagnosisRecord` 分工；不得从 DOM、文件存在或视觉状态猜测结果。
- 本地脱敏预览 token 与显式二次确认；不得把预览和诊断合并成无确认的一键上传。
- live/replay、completed/partial/failed、TTS fallback 的真实文字标识；不得把回放或降级包装成实时云端成功。
- 原始报告、诊断卡、复盘稿、MP3、引用与 ZIP 仍来自同一已验证结果身份；UI 摘要只能确定性选取和格式化，不能重新推理或改写事实。
- case/run/result/fixture、哈希、事实/证据 ID、backend 和恢复字段必须保留在技术详情及证据包中，可复制、可审计，只是不再默认主导页面。
- 命令只读、永不自动执行；下载仍使用服务端验证的 capability URL，不引入用户路径、任意文件或 shell 边界。
- partial 只显示真实可用产物和作用域重试；failed 不显示未验证报告、媒体或结果包。
- native Gradio 的键盘、焦点、禁用、Tabs、Audio 与 DownloadButton 语义继续保留。

---

## Evidence Notes

- Visual evidence: `output/playwright/after-student-idle-desktop.png` (1366×768), `after-student-completed-desktop.png` (1366×768), `after-student-completed-mobile.png` (375×812).
- The idle screenshot proves the current first screen has a title but no value proposition, three equally weighted columns, a large empty header, and disabled result chrome.
- The completed desktop screenshot proves the report artifact still elevates raw IDs/hashes/version fields into primary reading space.
- The mobile screenshot proves one-column stacking avoids body overflow but does not produce a good result-first reading order; the first command is visibly clipped.
- No live server was available on ports 3000, 5173, 8080, or 7860, so no new screenshots were captured.
- Registry audit skipped: `components.json` is absent and `04-UI-SPEC.md` declares no third-party registries.

---

## Files Audited

- `.planning/phases/04-multimodal-results-ui/04-CONTEXT.md`
- `.planning/phases/04-multimodal-results-ui/04-UI-SPEC.md`
- `.planning/phases/04-multimodal-results-ui/04-01-SUMMARY.md` through `04-10-SUMMARY.md`
- `src/debugmate/ui/app.py`
- `src/debugmate/ui/presentation.py`
- `tests/ui/test_browser.py`
- `output/playwright/after-student-idle-desktop.png`
- `output/playwright/after-student-completed-desktop.png`
- `output/playwright/after-student-completed-mobile.png`
