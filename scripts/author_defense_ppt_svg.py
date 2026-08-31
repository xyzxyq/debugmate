# Generated slide authoring intentionally keeps SVG attribute strings together;
# the ppt-master SVG gate is the formatting/geometry authority for this file.
# ruff: noqa: E501, F541, I001

from __future__ import annotations

import html
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "debugmate-defense-ppt_ppt169_20260901"
OUT = PROJECT / "svg_output"
IMG = PROJECT / "images"

W, H = 1280, 720
BG = "#F7F5EF"
INK = "#14212B"
BODY = "#33424D"
TEAL = "#0F9D8A"
CORAL = "#F0784A"
MINT = "#D9EEE8"
PANEL = "#E7ECE9"
LINE = "#C5D2CC"
WHITE = "#FFFFFF"
MUTED = "#708087"
CODE = "#1E2A31"


def esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def svg_open(role: str, num: int, section: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" data-pptx-page-role="{role}" font-family="Microsoft YaHei, Arial">',
        f'<rect id="page-background" data-pptx-role="background" x="0" y="0" width="{W}" height="{H}" fill="{BG}"/>',
        '<g id="page-chrome" data-pptx-bounds="56 20 1168 40">',
        f'<text x="56" y="39" font-family="Microsoft YaHei, Arial" font-size="13" letter-spacing="2" fill="{TEAL}">{esc(section.upper())}</text>',
        f'<text x="1170" y="39" font-family="Consolas, Courier New, monospace" font-size="13" fill="{MUTED}">{num:02d} / 15</text>',
        f'<rect x="56" y="54" width="32" height="4" rx="2" fill="{CORAL}"/>',
        '</g>',
        '<g id="slide-content" data-pptx-bounds="56 60 1168 650">',
    ]


def svg_close(parts: list[str]) -> str:
    parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts)


def title(parts: list[str], main: str, sub: str | None = None) -> None:
    parts.append(f'<text x="56" y="105" font-family="Microsoft YaHei, Arial" font-size="34" font-weight="700" fill="{INK}">{esc(main)}</text>')
    if sub:
        parts.append(f'<text x="58" y="137" font-family="Microsoft YaHei, Arial" font-size="17" fill="{MUTED}">{esc(sub)}</text>')


def text_lines(parts: list[str], x: float, y: float, lines: list[str], size: int = 20, color: str = BODY, weight: str = "400", leading: int = 30, family: str = "Microsoft YaHei, Arial") -> None:
    for i, line in enumerate(lines):
        parts.append(f'<text x="{x}" y="{y + i * leading}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{color}">{esc(line)}</text>')


def rounded(parts: list[str], x: float, y: float, w: float, h: float, fill: str = WHITE, stroke: str = LINE, r: int = 16, opacity: float = 1) -> None:
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" opacity="{opacity}"/>')


def pill(parts: list[str], x: float, y: float, w: float, label: str, fill: str = MINT, color: str = TEAL) -> None:
    rounded(parts, x, y, w, 30, fill, fill, 15)
    parts.append(f'<text x="{x + w / 2}" y="{y + 20}" text-anchor="middle" font-family="Microsoft YaHei, Arial" font-size="14" font-weight="700" fill="{color}">{esc(label)}</text>')


def arrow(parts: list[str], x1: float, y1: float, x2: float, y2: float, color: str = TEAL, width: int = 3) -> None:
    parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2 - 12}" y2="{y2}" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>')
    parts.append(f'<path d="M {x2 - 15} {y2 - 7} L {x2} {y2} L {x2 - 15} {y2 + 7}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')


def image_tag(parts: list[str], name: str, x: float, y: float, w: float, h: float, preserve: str = "xMidYMid slice") -> None:
    parts.append(f'<image href="../images/{esc(name)}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="{preserve}"/>')


def node(parts: list[str], x: float, y: float, label: str, sub: str, accent: str = TEAL, w: float = 160, h: float = 108) -> None:
    rounded(parts, x, y, w, h, WHITE, LINE, 18)
    parts.append(f'<circle cx="{x + 27}" cy="{y + 28}" r="14" fill="{accent}"/>')
    parts.append(f'<text x="{x + 27}" y="{y + 33}" text-anchor="middle" font-family="Arial" font-size="14" font-weight="700" fill="{WHITE}">✓</text>')
    parts.append(f'<text x="{x + 52}" y="{y + 33}" font-family="Microsoft YaHei, Arial" font-size="18" font-weight="700" fill="{INK}">{esc(label)}</text>')
    text_lines(parts, x + 20, y + 65, [sub], 14, MUTED, leading=20)


def footer(parts: list[str], label: str = "DebugMate · V0.1 · 可追溯诊断工作流") -> None:
    parts.append(f'<line x1="56" y1="675" x2="1224" y2="675" stroke="{LINE}" stroke-width="1"/>')
    parts.append(f'<text x="56" y="699" font-family="Microsoft YaHei, Arial" font-size="13" fill="{MUTED}">{esc(label)}</text>')


def p01() -> str:
    p = svg_open("cover", 1, "Defense deck")
    image_tag(p, "cover-concept.png", 530, 0, 750, 720, "xMidYMid slice")
    p.append('<rect x="0" y="0" width="690" height="720" fill="#F7F5EF" opacity="0.96"/>')
    p.append(f'<text x="66" y="150" font-family="Microsoft YaHei, Arial" font-size="68" font-weight="700" fill="{INK}">DebugMate</text>')
    p.append(f'<text x="69" y="204" font-family="Microsoft YaHei, Arial" font-size="24" fill="{TEAL}">从报错到复盘</text>')
    text_lines(p, 69, 275, ["面向 AI 专业学习场景的", "多模态报错诊断与复盘智能体"], 24, BODY, "400", 42)
    p.append(f'<line x1="69" y1="370" x2="355" y2="370" stroke="{CORAL}" stroke-width="5"/>')
    text_lines(p, 69, 422, ["有依据", "可执行", "说明不确定性"], 22, INK, "700", 42)
    pill(p, 69, 575, 144, "《校外实训》")
    pill(p, 225, 575, 102, "V0.1")
    pill(p, 339, 575, 138, "本地演示版", "#FBE5DB", CORAL)
    footer(p, "Defense deck · 2026.09")
    return svg_close(p)


def p02() -> str:
    p = svg_open("content", 2, "01 · Problem")
    title(p, "从一个真实报错开始", "错误只有一行，判断下一步需要一整条证据链")
    rounded(p, 56, 176, 610, 420, CODE, CODE, 18)
    image_tag(p, "terminal-module-not-found-redacted.png", 74, 196, 574, 360, "xMidYMid meet")
    pill(p, 80, 570, 130, "真实脱敏输入", "#283840", "#BCE5DB")
    rounded(p, 724, 176, 500, 420, WHITE, LINE, 18)
    p.append(f'<text x="758" y="224" font-family="Microsoft YaHei, Arial" font-size="19" font-weight="700" fill="{CORAL}">学生真正需要判断的三件事</text>')
    for i, (head, body) in enumerate([("是什么", "ModuleNotFoundError 指向导入失败"), ("发生在哪里", "Windows / Python 3.13.5 / 当前解释器"), ("下一步信什么", "官方资料、检查命令与明确限制")]):
        y = 275 + i * 92
        p.append(f'<circle cx="770" cy="{y - 7}" r="16" fill="{TEAL}"/>')
        p.append(f'<text x="770" y="{y - 1}" text-anchor="middle" font-family="Arial" font-size="14" font-weight="700" fill="{WHITE}">{i + 1}</text>')
        p.append(f'<text x="802" y="{y}" font-family="Microsoft YaHei, Arial" font-size="20" font-weight="700" fill="{INK}">{esc(head)}</text>')
        p.append(f'<text x="802" y="{y + 28}" font-family="Microsoft YaHei, Arial" font-size="16" fill="{BODY}">{esc(body)}</text>')
    p.append(f'<text x="758" y="555" font-family="Microsoft YaHei, Arial" font-size="18" font-weight="700" fill="{TEAL}">DebugMate 的任务：让判断有证据可回看。</text>')
    footer(p)
    return svg_close(p)


def p03() -> str:
    p = svg_open("content", 3, "01 · Problem")
    title(p, "普通问答为什么不够", "价值不在于“回答更多”，而在于让回答可追溯、可检查、可复盘")
    cards = [("01", "证据缺失", "看似合理的安装命令，未必绑定当前环境和官方资料。", CORAL), ("02", "环境不确定", "解释器、版本、路径和截图信息常常分散在不同位置。", TEAL), ("03", "结果难沉淀", "修好一次不等于理解一次，缺少结构化的学习记录。", "#6D7BB8")]
    for i, (num, head, body, color) in enumerate(cards):
        x = 56 + i * 388
        rounded(p, x, 210, 350, 280, WHITE, LINE, 18)
        p.append(f'<text x="{x + 26}" y="{270}" font-family="Consolas, Courier New, monospace" font-size="48" font-weight="700" fill="{color}" opacity="0.35">{num}</text>')
        p.append(f'<text x="{x + 28}" y="{340}" font-family="Microsoft YaHei, Arial" font-size="25" font-weight="700" fill="{INK}">{esc(head)}</text>')
        text_lines(p, x + 28, 382, [body[:16], body[16:]], 17, BODY, leading=28)
        p.append(f'<rect x="{x + 28}" y="{450}" width="80" height="5" rx="2" fill="{color}"/>')
    rounded(p, 56, 540, 1168, 70, INK, INK, 18)
    p.append(f'<text x="640" y="584" text-anchor="middle" font-family="Microsoft YaHei, Arial" font-size="23" font-weight="700" fill="{WHITE}">目标：把一次排错，转化为可追溯、可检查、可复盘的学习过程。</text>')
    footer(p)
    return svg_close(p)


def p04() -> str:
    p = svg_open("content", 4, "01 · Scope")
    title(p, "V0.1 做什么，也不做什么", "课程交付优先：闭环真实可演示，边界明确不夸大")
    rounded(p, 56, 190, 540, 410, "#E1F1EC", "#B9DDD3", 20)
    rounded(p, 644, 190, 580, 410, "#FBEAE3", "#F0C4B4", 20)
    p.append(f'<text x="92" y="240" font-family="Microsoft YaHei, Arial" font-size="24" font-weight="700" fill="{TEAL}">本版本交付</text>')
    p.append(f'<text x="680" y="240" font-family="Microsoft YaHei, Arial" font-size="24" font-weight="700" fill="{CORAL}">明确延后</text>')
    done = ["Windows 本地浏览器真实演示", "17 个官方知识来源与检索证据", "上传前脱敏 + 用户预览确认", "同源报告 / PNG / MP3 / ZIP", "4 个代表性案例与提示词账本"]
    later = ["公网部署、账户、权限与 SLA", "跨平台并发和生产监控", "稳定的 Dify 浏览器端全链路", "自动执行修复命令", "把未验证输出扩写成成功率"]
    for i, line in enumerate(done):
        y = 292 + i * 54
        p.append(f'<circle cx="96" cy="{y - 7}" r="12" fill="{TEAL}"/>')
        p.append(f'<text x="96" y="{y - 2}" text-anchor="middle" font-family="Arial" font-size="13" font-weight="700" fill="{WHITE}">✓</text>')
        p.append(f'<text x="122" y="{y}" font-family="Microsoft YaHei, Arial" font-size="17" fill="{INK}">{esc(line)}</text>')
    for i, line in enumerate(later):
        y = 292 + i * 54
        p.append(f'<circle cx="684" cy="{y - 7}" r="12" fill="{CORAL}"/>')
        p.append(f'<text x="684" y="{y - 2}" text-anchor="middle" font-family="Arial" font-size="13" font-weight="700" fill="{WHITE}">–</text>')
        p.append(f'<text x="710" y="{y}" font-family="Microsoft YaHei, Arial" font-size="17" fill="{INK}">{esc(line)}</text>')
    footer(p)
    return svg_close(p)


def p05() -> str:
    p = svg_open("content", 5, "02 · System")
    title(p, "一次诊断的完整路径", "每一步都有清晰输入与输出，最后所有产物回到同一个诊断对象")
    labels = [("输入", "文本 / 代码 / 截图", TEAL), ("隐私", "脱敏 + 预览确认", CORAL), ("抽取", "事实与纠错", "#6D7BB8"), ("检索", "官方 chunk / URL", TEAL), ("诊断", "DiagnosisRecord 1.1", CORAL), ("产物", "报告 / PNG / MP3", "#6D7BB8")]
    xs = [56, 258, 460, 662, 864, 1066]
    for i, (head, sub, color) in enumerate(labels):
        node(p, xs[i], 260, head, sub, color, 160, 120)
        if i < len(labels) - 1:
            arrow(p, xs[i] + 165, 320, xs[i + 1] - 7, 320)
    rounded(p, 56, 470, 1168, 105, INK, INK, 18)
    p.append(f'<text x="88" y="510" font-family="Cascadia Mono, Consolas, monospace" font-size="16" fill="#BCE5DB">case_id</text>')
    p.append(f'<text x="250" y="510" font-family="Cascadia Mono, Consolas, monospace" font-size="16" fill="{WHITE}">→</text>')
    p.append(f'<text x="288" y="510" font-family="Cascadia Mono, Consolas, monospace" font-size="16" fill="#BCE5DB">knowledge_build_id</text>')
    p.append(f'<text x="600" y="510" font-family="Cascadia Mono, Consolas, monospace" font-size="16" fill="{WHITE}">→</text>')
    p.append(f'<text x="642" y="510" font-family="Cascadia Mono, Consolas, monospace" font-size="16" fill="#BCE5DB">diagnosis_hash</text>')
    p.append(f'<text x="88" y="545" font-family="Microsoft YaHei, Arial" font-size="19" font-weight="700" fill="{WHITE}">从输入到导出的身份线索贯穿同一次运行，便于回看与复核。</text>')
    footer(p)
    return svg_close(p)


def p06() -> str:
    p = svg_open("content", 6, "02 · System")
    title(p, "技术路线：云端增强，本地闭环", "不是二选一，而是把不稳定的外部能力隔离在可验证边界之外")
    rounded(p, 56, 185, 820, 420, WHITE, LINE, 20)
    rounded(p, 900, 185, 324, 420, INK, INK, 20)
    p.append(f'<text x="92" y="232" font-family="Microsoft YaHei, Arial" font-size="22" font-weight="700" fill="{TEAL}">Dify Cloud · 增强层</text>')
    p.append(f'<text x="92" y="265" font-family="Microsoft YaHei, Arial" font-size="15" fill="{MUTED}">视觉模型 / 知识检索 / LLM 工作流</text>')
    p.append(f'<text x="92" y="350" font-family="Microsoft YaHei, Arial" font-size="22" font-weight="700" fill="{CORAL}">Local Python · 交付层</text>')
    p.append(f'<text x="92" y="383" font-family="Microsoft YaHei, Arial" font-size="15" fill="{MUTED}">脱敏 / Pydantic / Pillow / TTS fallback / Gradio</text>')
    for i, label in enumerate(["上传与检索", "结构化 JSON", "本地严格校验", "报告与多媒体"]):
        x = 92 + i * 177
        rounded(p, x, 290 if i < 2 else 425, 150, 48, MINT if i < 2 else "#FBE5DB", "none", 12)
        p.append(f'<text x="{x + 75}" y="{320 if i < 2 else 455}" text-anchor="middle" font-family="Microsoft YaHei, Arial" font-size="14" font-weight="700" fill="{TEAL if i < 2 else CORAL}">{esc(label)}</text>')
    arrow(p, 245, 338, 245, 414, CORAL, 2)
    arrow(p, 600, 338, 600, 414, CORAL, 2)
    p.append(f'<text x="934" y="245" font-family="Microsoft YaHei, Arial" font-size="24" font-weight="700" fill="{WHITE}">Git · 事实源</text>')
    text_lines(p, 934, 295, ["知识源与 manifest", "提示词 V1–V4", "Dify DSL", "运行证据与哈希", "课程材料与脚本"], 18, "#D8E5E1", leading=42)
    p.append(f'<line x1="934" y1="520" x2="1188" y2="520" stroke="#4D666A"/>')
    p.append(f'<text x="934" y="555" font-family="Microsoft YaHei, Arial" font-size="16" fill="#BCE5DB">可重建 · 可复核 · 可交接</text>')
    footer(p)
    return svg_close(p)


def p07() -> str:
    p = svg_open("content", 7, "02 · System")
    title(p, "系统架构：DiagnosisRecord 是单一事实源", "三种媒体不是三个答案，而是一个结构化对象的不同投影")
    rounded(p, 56, 214, 280, 290, WHITE, LINE, 18)
    p.append(f'<text x="86" y="255" font-family="Microsoft YaHei, Arial" font-size="21" font-weight="700" fill="{TEAL}">输入与证据</text>')
    text_lines(p, 86, 305, ["error_text", "code / environment", "observed_facts", "knowledge chunks", "support_links"], 18, BODY, leading=39)
    rounded(p, 400, 170, 480, 380, INK, INK, 24)
    p.append(f'<text x="440" y="232" font-family="Cascadia Mono, Consolas, monospace" font-size="23" font-weight="700" fill="#BCE5DB">DiagnosisRecord</text>')
    p.append(f'<text x="440" y="270" font-family="Microsoft YaHei, Arial" font-size="20" font-weight="700" fill="{WHITE}">schema_version 1.1.0</text>')
    fields = ["case_id", "root_cause_candidates", "checks", "verification_steps", "limitations"]
    for i, field in enumerate(fields):
        y = 324 + i * 38
        p.append(f'<rect x="440" y="{y - 22}" width="370" height="28" rx="8" fill="#263841"/>')
        p.append(f'<text x="458" y="{y - 2}" font-family="Cascadia Mono, Consolas, monospace" font-size="15" fill="#D8E5E1">{esc(field)}</text>')
    rounded(p, 944, 214, 280, 290, WHITE, LINE, 18)
    p.append(f'<text x="974" y="255" font-family="Microsoft YaHei, Arial" font-size="21" font-weight="700" fill="{CORAL}">派生结果</text>')
    text_lines(p, 974, 305, ["Markdown report", "Pillow diagnostic card", "MP3 recap", "ZIP + manifest"], 18, BODY, leading=45)
    arrow(p, 342, 360, 390, 360, TEAL, 3)
    arrow(p, 888, 360, 936, 360, CORAL, 3)
    footer(p)
    return svg_close(p)


def p08() -> str:
    p = svg_open("content", 8, "02 · Evidence")
    title(p, "专属知识库：17 个官方来源", "检索不是装饰：来源、版本范围、内容哈希和构建 ID 都进入证据链")
    topics = [("Python 异常", "导入 / Traceback", TEAL), ("pip / venv", "环境 / 依赖", CORAL), ("PyTorch", "张量 / 序列化", "#6D7BB8"), ("CUDA", "显存 / 设备", TEAL), ("Hugging Face", "模型 / Hub", CORAL), ("Ultralytics", "训练 / 预测", "#6D7BB8"), ("Windows", "PATH / PowerShell", TEAL)]
    for i, (head, sub, color) in enumerate(topics):
        row, col = divmod(i, 2)
        x = 56 + col * 310
        y = 188 + row * 86
        rounded(p, x, y, 280, 64, WHITE, LINE, 14)
        p.append(f'<rect x="{x}" y="{y}" width="7" height="64" rx="3" fill="{color}"/>')
        p.append(f'<text x="{x + 24}" y="{y + 27}" font-family="Microsoft YaHei, Arial" font-size="17" font-weight="700" fill="{INK}">{esc(head)}</text>')
        p.append(f'<text x="{x + 24}" y="{y + 49}" font-family="Microsoft YaHei, Arial" font-size="13" fill="{MUTED}">{esc(sub)}</text>')
    rounded(p, 730, 188, 494, 330, INK, INK, 20)
    p.append(f'<text x="766" y="236" font-family="Microsoft YaHei, Arial" font-size="21" font-weight="700" fill="#BCE5DB">一次命中，至少回答四个问题</text>')
    for i, line in enumerate(["来源 URL 是什么？", "适用的版本范围是什么？", "命中的 chunk / locator 在哪里？", "是否绑定当前 knowledge_build_id？"]):
        y = 286 + i * 48
        p.append(f'<circle cx="774" cy="{y - 7}" r="10" fill="{TEAL}"/>')
        p.append(f'<text x="774" y="{y - 3}" text-anchor="middle" font-family="Arial" font-size="12" fill="{WHITE}">✓</text>')
        p.append(f'<text x="798" y="{y}" font-family="Microsoft YaHei, Arial" font-size="17" fill="{WHITE}">{esc(line)}</text>')
    p.append(f'<text x="766" y="478" font-family="Cascadia Mono, Consolas, monospace" font-size="14" fill="#F6C2AF">knowledge_build_id: e8e065…71ff</text>')
    rounded(p, 56, 492, 590, 74, "#FBE5DB", "#F0C4B4", 16)
    p.append(f'<text x="84" y="524" font-family="Microsoft YaHei, Arial" font-size="16" font-weight="700" fill="{CORAL}">无命中 ≠ 可以猜</text>')
    p.append(f'<text x="84" y="549" font-family="Microsoft YaHei, Arial" font-size="15" fill="{BODY}">证据不足时，诊断必须明确记录缺失信息。</text>')
    footer(p)
    return svg_close(p)


def p09() -> str:
    p = svg_open("content", 9, "02 · Safety")
    title(p, "隐私闸门：先确认，再上传", "脱敏不是后台黑盒动作，而是用户可见、可确认的交互门禁")
    steps = [("01", "本机校验", "检查输入完整性", TEAL), ("02", "发现敏感项", "OCR + 正则", CORAL), ("03", "生成预览", "文字替换 / 像素遮挡", "#6D7BB8"), ("04", "用户确认", "确认后才允许云调用", TEAL)]
    for i, (num, head, sub, color) in enumerate(steps):
        x = 56 + i * 292
        rounded(p, x, 210, 248, 158, WHITE, LINE, 18)
        p.append(f'<text x="{x + 22}" y="{250}" font-family="Consolas, Courier New, monospace" font-size="26" font-weight="700" fill="{color}">{num}</text>')
        p.append(f'<text x="{x + 22}" y="{298}" font-family="Microsoft YaHei, Arial" font-size="21" font-weight="700" fill="{INK}">{esc(head)}</text>')
        p.append(f'<text x="{x + 22}" y="{330}" font-family="Microsoft YaHei, Arial" font-size="15" fill="{BODY}">{esc(sub)}</text>')
        if i < 3:
            arrow(p, x + 254, 289, x + 284, 289, color, 2)
    rounded(p, 56, 420, 1168, 150, CODE, CODE, 18)
    p.append(f'<text x="86" y="458" font-family="Microsoft YaHei, Arial" font-size="16" font-weight="700" fill="#BCE5DB">上传前审计对象</text>')
    text_lines(p, 86, 500, ["Token / 密码    邮箱 / 用户名    Windows / Linux 绝对路径    截图敏感像素    日志与导出物二次泄漏"], 17, WHITE, leading=25)
    p.append(f'<text x="86" y="545" font-family="Microsoft YaHei, Arial" font-size="17" font-weight="700" fill="#F6C2AF">用户能看到脱敏结果，系统才有资格继续。</text>')
    footer(p)
    return svg_close(p)


def p10() -> str:
    p = svg_open("content", 10, "03 · Prompt")
    title(p, "V1–V4：从能回答到可派生", "提示词优化的终点不是更长，而是证据、结构和多模态输出保持一致")
    p.append(f'<line x1="100" y1="360" x2="1180" y2="360" stroke="{LINE}" stroke-width="4"/>')
    versions = [("V1", "基础诊断", "类别 / 原因 / 步骤", "能回答", CORAL), ("V2", "引用约束", "事实 / 推断 / 缺失信息", "有依据", TEAL), ("V3", "结构可靠", "命令影响 / 预期 / 回退", "可校验", "#6D7BB8"), ("V4", "课程定稿", "recap → 报告 / PNG / MP3", "可派生", CORAL)]
    for i, (ver, head, body, tag, color) in enumerate(versions):
        x = 120 + i * 280
        p.append(f'<circle cx="{x}" cy="360" r="24" fill="{color}"/>')
        p.append(f'<text x="{x}" y="368" text-anchor="middle" font-family="Cascadia Mono, Consolas, monospace" font-size="14" font-weight="700" fill="{WHITE}">✓</text>')
        p.append(f'<text x="{x - 10}" y="290" text-anchor="middle" font-family="Cascadia Mono, Consolas, monospace" font-size="24" font-weight="700" fill="{color}">{ver}</text>')
        p.append(f'<text x="{x - 10}" y="426" text-anchor="middle" font-family="Microsoft YaHei, Arial" font-size="20" font-weight="700" fill="{INK}">{esc(head)}</text>')
        p.append(f'<text x="{x - 10}" y="458" text-anchor="middle" font-family="Microsoft YaHei, Arial" font-size="15" fill="{BODY}">{esc(body)}</text>')
        pill(p, x - 59, 500, 118, tag, "#E1F1EC" if color == TEAL else "#FBE5DB", TEAL if color == TEAL else CORAL)
    rounded(p, 56, 570, 1168, 46, WHITE, LINE, 14)
    p.append(f'<text x="640" y="599" text-anchor="middle" font-family="Microsoft YaHei, Arial" font-size="15" fill="{MUTED}">V1 有固定案例 manifest；V2–V4 的采用、限制与未验证范围保留在版本化账本中。</text>')
    footer(p)
    return svg_close(p)


def p11() -> str:
    p = svg_open("content", 11, "03 · Proof")
    title(p, "一次完整诊断的真实结果", "真实 Microsoft Edge 截图：输入、证据、诊断和下载处在同一个工作台")
    rounded(p, 56, 172, 920, 430, WHITE, LINE, 18)
    image_tag(p, "01-completed-overview.png", 70, 186, 892, 402, "xMidYMid meet")
    rounded(p, 1010, 190, 214, 370, INK, INK, 18)
    p.append(f'<text x="1038" y="235" font-family="Microsoft YaHei, Arial" font-size="20" font-weight="700" fill="#BCE5DB">三处关键证据</text>')
    for i, line in enumerate(["脱敏输入", "事实与引用", "报告 / 卡 / 音频 / ZIP"]):
        y = 294 + i * 75
        p.append(f'<circle cx="1042" cy="{y - 7}" r="12" fill="{TEAL if i < 2 else CORAL}"/>')
        p.append(f'<text x="1042" y="{y - 2}" text-anchor="middle" font-family="Arial" font-size="12" fill="{WHITE}">{i + 1}</text>')
        p.append(f'<text x="1066" y="{y}" font-family="Microsoft YaHei, Arial" font-size="16" fill="{WHITE}">{esc(line)}</text>')
    p.append(f'<text x="1038" y="492" font-family="Microsoft YaHei, Arial" font-size="14" fill="#F6C2AF">截图标记：离线回放</text>')
    p.append(f'<text x="1038" y="520" font-family="Microsoft YaHei, Arial" font-size="14" fill="#D8E5E1">不把回放称为实时云端</text>')
    footer(p)
    return svg_close(p)


def p12() -> str:
    p = svg_open("content", 12, "03 · Proof")
    title(p, "三种输出，共享一个身份", "同一份 DiagnosisRecord 派生出文字、图像、语音与证据包")
    rounded(p, 56, 222, 300, 260, WHITE, LINE, 18)
    p.append(f'<text x="88" y="270" font-family="Microsoft YaHei, Arial" font-size="21" font-weight="700" fill="{TEAL}">文字报告</text>')
    text_lines(p, 88, 314, ["事实 / 推断", "缺失信息", "检查与验证", "置信度与局限"], 17, BODY, leading=34)
    rounded(p, 490, 182, 300, 340, INK, INK, 24)
    p.append(f'<text x="640" y="242" text-anchor="middle" font-family="Cascadia Mono, Consolas, monospace" font-size="20" font-weight="700" fill="#BCE5DB">shared identity</text>')
    text_lines(p, 535, 302, ["case_id", "source_run_id", "diagnosis_hash", "schema_version"], 17, WHITE, "400", 46, "Cascadia Mono, Consolas, monospace")
    rounded(p, 924, 222, 300, 260, WHITE, LINE, 18)
    p.append(f'<text x="956" y="270" font-family="Microsoft YaHei, Arial" font-size="21" font-weight="700" fill="{CORAL}">PNG / MP3 / ZIP</text>')
    text_lines(p, 956, 314, ["Pillow 确定性诊断卡", "同一 recap_text 生成语音", "manifest + SHA-256 校验"], 17, BODY, leading=38)
    image_tag(p, "card.png", 956, 424, 230, 76, "xMidYMid meet")
    arrow(p, 365, 350, 474, 350, TEAL, 3)
    arrow(p, 806, 350, 915, 350, CORAL, 3)
    rounded(p, 56, 560, 1168, 48, MINT, MINT, 14)
    p.append(f'<text x="640" y="591" text-anchor="middle" font-family="Microsoft YaHei, Arial" font-size="17" font-weight="700" fill="{TEAL}">同源 ≠ 同格式；同源 = 同一身份、同一事实、同一限制。</text>')
    footer(p)
    return svg_close(p)


def p13() -> str:
    p = svg_open("content", 13, "03 · Honesty")
    title(p, "失败也要诚实", "外部节点失败时保留真实失败记录，只重试失败的产物")
    rounded(p, 56, 180, 440, 410, WHITE, LINE, 18)
    image_tag(p, "02-tts-partial.png", 70, 194, 412, 310, "xMidYMid meet")
    pill(p, 82, 522, 164, "TTS failed → 重试语音", "#FBE5DB", CORAL)
    rounded(p, 840, 180, 384, 410, WHITE, LINE, 18)
    image_tag(p, "03-card-partial.png", 854, 194, 356, 310, "xMidYMid meet")
    pill(p, 866, 522, 188, "PNG failed → 重试诊断卡", "#E1F1EC", TEAL)
    rounded(p, 540, 240, 230, 300, INK, INK, 18)
    p.append(f'<text x="655" y="284" text-anchor="middle" font-family="Microsoft YaHei, Arial" font-size="19" font-weight="700" fill="#BCE5DB">最小重试</text>')
    text_lines(p, 576, 340, ["保留已完成结果", "记录失败节点", "给出可重试范围", "不伪装 cloud success"], 16, WHITE, leading=42)
    arrow(p, 502, 382, 532, 382, CORAL, 2)
    arrow(p, 778, 382, 832, 382, TEAL, 2)
    p.append(f'<text x="56" y="628" font-family="Microsoft YaHei, Arial" font-size="16" fill="{MUTED}">当前边界：Dify 浏览器端曾出现 timeout / 旧契约响应；正式材料保留限制，并明确使用 local fallback 或 replay。</text>')
    footer(p)
    return svg_close(p)


def p14() -> str:
    p = svg_open("content", 14, "04 · Evaluation")
    title(p, "评测与自动验证", "以可复算证据作为完成标准，而不是以虚构成功率作为完成标准")
    rounded(p, 56, 180, 600, 400, WHITE, LINE, 18)
    p.append(f'<text x="86" y="226" font-family="Microsoft YaHei, Arial" font-size="21" font-weight="700" fill="{TEAL}">Phase 9 · 4 个代表性案例</text>')
    cases = [("C01", "依赖缺失", "blocked / real_live", CORAL), ("C02", "信息不足", "insufficient_data", "#6D7BB8"), ("C03", "长文本 replay", "blocked / replay", TEAL), ("C04", "fallback partial", "partial", CORAL)]
    for i, (cid, head, state, color) in enumerate(cases):
        y = 280 + i * 63
        p.append(f'<text x="88" y="{y}" font-family="Cascadia Mono, Consolas, monospace" font-size="16" font-weight="700" fill="{color}">{cid}</text>')
        p.append(f'<text x="150" y="{y}" font-family="Microsoft YaHei, Arial" font-size="17" font-weight="700" fill="{INK}">{esc(head)}</text>')
        p.append(f'<text x="350" y="{y}" font-family="Cascadia Mono, Consolas, monospace" font-size="14" fill="{MUTED}">{esc(state)}</text>')
        p.append(f'<line x1="88" y1="{y + 18}" x2="602" y2="{y + 18}" stroke="{LINE}"/>')
    rounded(p, 704, 180, 520, 400, INK, INK, 18)
    p.append(f'<text x="740" y="226" font-family="Microsoft YaHei, Arial" font-size="21" font-weight="700" fill="#BCE5DB">自动验证结果</text>')
    nums = [("1177", "offline regression passed", "#BCE5DB"), ("113", "privacy tests passed", "#BCE5DB"), ("1", "cloud contract test passed", "#F6C2AF"), ("0", "Phase 10 eligible source", "#F6C2AF")]
    for i, (num, label, color) in enumerate(nums):
        x = 756 + (i % 2) * 220
        y = 300 + (i // 2) * 125
        p.append(f'<text x="{x}" y="{y}" font-family="Consolas, Courier New, monospace" font-size="40" font-weight="700" fill="{color}">{num}</text>')
        text_lines(p, x, y + 30, [label], 14, WHITE, leading=18)
    p.append(f'<text x="740" y="550" font-family="Microsoft YaHei, Arial" font-size="14" fill="#F6C2AF">0 eligible 表示保持诚实，不把阻塞案例扩写进课程证据。</text>')
    footer(p)
    return svg_close(p)


def p15() -> str:
    p = svg_open("ending", 15, "05 · Close")
    title(p, "总结：把“修好一次”变成“理解一次”", "DebugMate V0.1 已形成课程可提交的多模态诊断闭环")
    sequence = [("报错", "真实或可复现", CORAL), ("隐私", "先预览再确认", TEAL), ("知识", "官方来源可追溯", "#6D7BB8"), ("诊断", "结构化且有边界", CORAL), ("复盘", "报告 / PNG / MP3 / ZIP", TEAL)]
    for i, (head, sub, color) in enumerate(sequence):
        x = 92 + i * 222
        p.append(f'<circle cx="{x}" cy="330" r="34" fill="{color}"/>')
        p.append(f'<text x="{x}" y="338" text-anchor="middle" font-family="Microsoft YaHei, Arial" font-size="17" font-weight="700" fill="{WHITE}">{esc(head)}</text>')
        p.append(f'<text x="{x}" y="405" text-anchor="middle" font-family="Microsoft YaHei, Arial" font-size="15" fill="{BODY}">{esc(sub)}</text>')
        if i < 4:
            arrow(p, x + 42, 330, x + 192, 330, TEAL, 3)
    rounded(p, 56, 500, 1168, 88, INK, INK, 18)
    p.append(f'<text x="88" y="538" font-family="Microsoft YaHei, Arial" font-size="17" fill="#D8E5E1">现场演示顺序</text>')
    p.append(f'<text x="88" y="566" font-family="Microsoft YaHei, Arial" font-size="18" font-weight="700" fill="{WHITE}">脱敏预览 → 用户确认 → 诊断与引用 → 三模态产物 → 失败降级说明</text>')
    p.append(f'<text x="56" y="635" font-family="Microsoft YaHei, Arial" font-size="17" fill="{MUTED}">云端 live、本地 fallback、固定 replay：三者都可以演示，但必须被准确命名。</text>')
    footer(p, "DebugMate · 课程答辩收束")
    return svg_close(p)


PAGES = [p01, p02, p03, p04, p05, p06, p07, p08, p09, p10, p11, p12, p13, p14, p15]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    for i, builder in enumerate(PAGES, 1):
        (OUT / f"P{i:02d}.svg").write_text(builder(), encoding="utf-8")
    print(f"authored {len(PAGES)} SVG pages in {OUT}")


if __name__ == "__main__":
    main()
