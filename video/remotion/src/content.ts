export type SceneContent = {
  id: number;
  eyebrow: string;
  title: string;
  accent: string;
  subtitle: string;
};

export const SCENES: SceneContent[] = [
  {
    id: 1,
    eyebrow: "DEBUGMATE / V0.1 / PROJECT FILM",
    title: "把一次报错",
    accent: "变成一条证据链",
    subtitle: "面向 AI 专业学习场景的多模态报错诊断与复盘智能体",
  },
  {
    id: 2,
    eyebrow: "01 / WHY",
    title: "答案不等于诊断",
    accent: "依据才是起点",
    subtitle: "从“给一个命令”转向“解释事实、证据和边界”",
  },
  {
    id: 3,
    eyebrow: "02 / PRIVACY GATE",
    title: "先在本机",
    accent: "把隐私挡住",
    subtitle: "脱敏预览 → 用户确认 → 才允许进入后续诊断",
  },
  {
    id: 4,
    eyebrow: "03 / KNOWLEDGE",
    title: "17 个官方来源",
    accent: "让检索可追溯",
    subtitle: "Python、pip、PyTorch、CUDA、Hugging Face、Windows 与更多来源",
  },
  {
    id: 5,
    eyebrow: "04 / DIAGNOSIS RECORD",
    title: "把推理拆成",
    accent: "可校验的结构",
    subtitle: "事实、推断、引用、检查、修复、验证和局限全部进入同一份记录",
  },
  {
    id: 6,
    eyebrow: "05 / MULTIMODAL OUTPUT",
    title: "同一个诊断对象",
    accent: "派生三种结果",
    subtitle: "文字报告 · 确定性 PNG · 同源语音复盘",
  },
  {
    id: 7,
    eyebrow: "06 / HONEST FALLBACK",
    title: "失败不被抹平",
    accent: "能力边界被保留",
    subtitle: "Dify live、local fallback、fixed replay 清晰分层",
  },
  {
    id: 8,
    eyebrow: "07 / TAKEAWAY",
    title: "从修好一次",
    accent: "到理解并复盘一次",
    subtitle: "课程交付闭环：可运行、可复核、可追溯",
  },
];
