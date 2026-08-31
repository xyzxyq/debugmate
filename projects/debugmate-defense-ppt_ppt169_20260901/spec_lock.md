<!-- ppt-master-schema: spec-lock/v1 -->
# Execution Lock

## canvas
- viewBox: 0 0 1280 720
- format: PPT 16:9

## communication
- primary_language: zh-CN
- audience: 《校外实训》课程教师与同学，具备 Python 基础
- objective: 以真实案例解释 DebugMate 的输入、隐私、检索、诊断和多模态产物链路，并使听众能区分 Dify live、本地 fallback 和固定 replay
- core_message: DebugMate 把一次报错转化为有依据、可检查、可复盘的学习过程
- consumption_mode: presentation

## mode
- mode: custom
- mode_behavior: narrative technical briefing; move from a concrete traceback to architecture, proof, honest limits, and a course-ready close

## visual_style
- visual_style: custom
- visual_style_behavior: editorial technical briefing with warm paper background, dark graphite type, teal evidence spine, orange risk marker, real screenshots, and editable diagram primitives

## colors
- bg: '#F7F5EF'
- primary: '#14212B'
- accent: '#0F9D8A'
- text: '#33424D'
- secondary_accent: '#F0784A'

## typography
- font_family: 'Microsoft YaHei, Aptos, Arial'
- title_family: 'Microsoft YaHei, Aptos Display, Arial'
- body_family: 'Microsoft YaHei, Aptos, Arial'
- code_family: 'Consolas, Courier New, monospace'
- body: 22
- title: 34
- subtitle: 18
- annotation: 16
- footnote: 13
- cover_display: 68
- large_display: 48
- compact_display: 24
- metric_display: 40

## icons
- library: native-svg-line
- inventory: geometric marks for flow, privacy, knowledge, report, card, audio, and status

## images
- p01: images/cover-concept.png | source=ai | crop=adaptive
- p11: images/01-completed-overview.png | source=user | crop=no-crop
- p13a: images/02-tts-partial.png | source=user | crop=no-crop
- p13b: images/03-card-partial.png | source=user | crop=no-crop
- p02: images/terminal-module-not-found-redacted.png | source=user | crop=no-crop
- p12: images/card.png | source=user | crop=no-crop

## page_rhythm
- P01: anchor
- P02: breathing
- P03: breathing
- P04: dense
- P05: anchor
- P06: dense
- P07: anchor
- P08: dense
- P09: anchor
- P10: breathing
- P11: anchor
- P12: breathing
- P13: anchor
- P14: dense
- P15: breathing

## pptx_structure
- mode: flat

## forbidden
- `mask`, `<style>`, `class`, external CSS, `<foreignObject>`, `textPath`, `@font-face`, `<animate*>`, `<set>`, `<script>` / event attributes, `<iframe>`
- HTML named entities in text; write typography as raw Unicode and escape XML reserved characters
