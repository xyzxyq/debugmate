import {Audio} from "@remotion/media";
import type {Caption} from "@remotion/captions";
import {
  AbsoluteFill,
  Easing,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useDelayRender,
  useVideoConfig,
} from "remotion";
import {useCallback, useEffect, useMemo, useState} from "react";
import {SCENES, type SceneContent} from "./content";
import {SCENE_TIMINGS, type SceneTiming} from "./timing";

const C = {
  navy: "#0d2137",
  navy2: "#122b46",
  panel: "#163653",
  panel2: "#1b4661",
  cream: "#f1f5f7",
  muted: "#afc3d1",
  orange: "#eb713e",
  teal: "#2ba6b5",
  green: "#59c6a8",
  red: "#ff8c72",
};

const FONT = "Microsoft YaHei, Segoe UI, Arial, sans-serif";
const MONO = "Cascadia Mono, Consolas, monospace";

const ease = Easing.bezier(0.16, 1, 0.3, 1);

const fade = (frame: number, from: number, to: number) =>
  interpolate(frame, [from, to], [0, 1], {
    easing: ease,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const slide = (frame: number, from: number, to: number, distance = 46) =>
  interpolate(frame, [from, to], [distance, 0], {
    easing: ease,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const frameInScene = (timing: SceneTiming, frame: number) => frame - timing.startFrame;

const rounded = (radius = 26): React.CSSProperties => ({borderRadius: radius});

const Label: React.FC<{children: React.ReactNode; color?: string}> = ({children, color = C.teal}) => (
  <div style={{fontFamily: MONO, fontSize: 24, letterSpacing: 4, color, fontWeight: 700}}>{children}</div>
);

const SceneHeader: React.FC<{scene: SceneContent; frame: number}> = ({scene, frame}) => (
  <div style={{position: "absolute", left: 96, top: 74, right: 96, opacity: fade(frame, 0, 18)}}>
    <Label>{scene.eyebrow}</Label>
    <div style={{marginTop: 26, display: "flex", alignItems: "baseline", gap: 18}}>
      <h1 style={{margin: 0, color: C.cream, fontFamily: FONT, fontSize: 72, lineHeight: 1.08, letterSpacing: -2}}>{scene.title}</h1>
      <h1 style={{margin: 0, color: C.orange, fontFamily: FONT, fontSize: 72, lineHeight: 1.08, letterSpacing: -2}}>{scene.accent}</h1>
    </div>
    <div style={{marginTop: 18, color: C.muted, fontFamily: FONT, fontSize: 30, opacity: 0.95}}>{scene.subtitle}</div>
    <div style={{marginTop: 28, width: 150, height: 6, backgroundColor: C.orange, borderRadius: 4}} />
  </div>
);

const Background: React.FC<{frame: number; sceneId: number}> = ({frame, sceneId}) => (
  <AbsoluteFill style={{backgroundColor: C.navy2, overflow: "hidden"}}>
    <div style={{position: "absolute", inset: 0, opacity: 0.33, backgroundImage: "linear-gradient(rgba(119,176,194,.11) 1px, transparent 1px), linear-gradient(90deg, rgba(119,176,194,.11) 1px, transparent 1px)", backgroundSize: "80px 80px", translate: `${(frame * 0.18) % 80}px ${(frame * 0.08) % 80}px`}} />
    <div style={{position: "absolute", width: 760, height: 760, right: -260, top: -380, borderRadius: "50%", background: `radial-gradient(circle, ${sceneId % 2 ? "rgba(43,166,181,.26)" : "rgba(235,113,62,.17)"} 0%, rgba(13,33,55,0) 72%)`, scale: 1 + Math.sin(frame / 90) * 0.03}} />
    <div style={{position: "absolute", width: 420, height: 420, left: -210, bottom: -250, borderRadius: "50%", background: "radial-gradient(circle, rgba(235,113,62,.18) 0%, rgba(13,33,55,0) 70%)"}} />
    <div style={{position: "absolute", left: 52, top: 68, bottom: 68, width: 6, backgroundColor: C.orange, borderRadius: 6, opacity: 0.95}} />
  </AbsoluteFill>
);

const Footer: React.FC<{timing: SceneTiming; frame: number}> = ({timing, frame}) => {
  const {fps} = useVideoConfig();
  const local = frameInScene(timing, frame);
  const progress = interpolate(local, [0, timing.durationInFrames], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  return (
    <div style={{position: "absolute", left: 96, right: 96, bottom: 48, display: "flex", alignItems: "center", gap: 28, opacity: fade(local, 0, 14)}}>
      <div style={{fontFamily: MONO, color: C.muted, fontSize: 20}}>DEBUGMATE · V0.1</div>
      <div style={{height: 1, flex: 1, backgroundColor: "rgba(175,195,209,.25)"}} />
      <div style={{fontFamily: MONO, color: C.teal, fontSize: 20}}>{String(timing.id).padStart(2, "0")} / 08</div>
      <div style={{width: 180, height: 4, backgroundColor: "rgba(175,195,209,.18)", borderRadius: 4}}><div style={{width: `${progress * 100}%`, height: "100%", backgroundColor: C.teal, borderRadius: 4}} /></div>
      <div style={{fontFamily: MONO, color: C.muted, fontSize: 20}}>{Math.round(timing.durationInFrames / fps)}s</div>
    </div>
  );
};

const Arrow: React.FC<{left: number; top: number; active?: boolean}> = ({left, top, active = true}) => (
  <div style={{position: "absolute", left, top, width: 92, height: 2, backgroundColor: active ? C.orange : C.muted, opacity: 0.9}}>
    <div style={{position: "absolute", right: -1, top: -7, width: 14, height: 14, borderTop: `2px solid ${active ? C.orange : C.muted}`, borderRight: `2px solid ${active ? C.orange : C.muted}`, rotate: "45deg"}} />
  </div>
);

const Pill: React.FC<{children: React.ReactNode; color?: string; bg?: string}> = ({children, color = C.cream, bg = "rgba(43,166,181,.16)"}) => (
  <div style={{display: "inline-flex", alignItems: "center", padding: "12px 18px", color, backgroundColor: bg, border: `1px solid ${color}55`, fontFamily: MONO, fontSize: 20, ...rounded(12)}}>{children}</div>
);

const TerminalCard: React.FC<{frame: number; small?: boolean}> = ({frame, small = false}) => {
  const width = small ? 510 : 720;
  const height = small ? 330 : 455;
  return (
    <div style={{width, height, backgroundColor: "#101820", border: `1px solid ${C.teal}88`, boxShadow: "0 24px 70px rgba(0,0,0,.34)", ...rounded(22), overflow: "hidden", opacity: fade(frame, 12, 32), translate: `${slide(frame, 12, 32, 60)}px 0px`}}>
      <div style={{height: 46, display: "flex", alignItems: "center", gap: 8, padding: "0 18px", backgroundColor: "#172735", borderBottom: "1px solid #294354"}}>
        <span style={{width: 10, height: 10, borderRadius: "50%", backgroundColor: C.red}} /><span style={{width: 10, height: 10, borderRadius: "50%", backgroundColor: "#e6b35b"}} /><span style={{width: 10, height: 10, borderRadius: "50%", backgroundColor: C.green}} />
        <span style={{marginLeft: 14, fontFamily: MONO, fontSize: 16, color: C.muted}}>PowerShell · redacted-input.txt</span>
      </div>
      <div style={{padding: 28, fontFamily: MONO, fontSize: small ? 17 : 22, lineHeight: 1.7, color: C.cream}}>
        <div style={{color: C.teal}}>PS C:\&gt; python train.py</div>
        <div style={{color: C.red, marginTop: 12}}>ModuleNotFoundError:</div>
        <div style={{color: C.red}}>&nbsp;&nbsp;No module named</div>
        <div style={{color: C.orange}}>&nbsp;&nbsp;'debugmate_missing_pkg_7f3a'</div>
        <div style={{marginTop: 20, color: C.muted}}>Environment: Windows · Python 3.13.5</div>
        <div style={{color: C.muted}}>Path: &lt;REDACTED&gt;\project\train.py</div>
      </div>
      <div style={{position: "absolute", right: 22, bottom: 18}}><Pill color={C.green}>已脱敏</Pill></div>
    </div>
  );
};

const Waveform: React.FC<{frame: number; width?: number; height?: number; color?: string}> = ({frame, width = 460, height = 86, color = C.teal}) => (
  <div style={{display: "flex", alignItems: "center", justifyContent: "center", gap: 4, width, height}}>
    {Array.from({length: 32}).map((_, i) => {
      const pulse = 0.25 + Math.abs(Math.sin(frame / 18 + i * 0.63)) * 0.75;
      const envelope = 0.35 + Math.sin((i / 31) * Math.PI) * 0.65;
      return <div key={i} style={{width: 7, height: Math.max(8, pulse * envelope * height), backgroundColor: color, opacity: 0.35 + envelope * 0.55, borderRadius: 8}} />;
    })}
  </div>
);

const SceneOne: React.FC<{frame: number}> = ({frame}) => (
  <>
    <SceneHeader scene={SCENES[0]} frame={frame} />
    <div style={{position: "absolute", left: 100, top: 420, width: 720, opacity: fade(frame, 12, 32), translate: `${slide(frame, 12, 32, 54)}px 0px`}}>
      <div style={{fontFamily: FONT, fontSize: 40, color: C.cream, lineHeight: 1.5}}>让报错不再停留在一段红字，</div>
      <div style={{fontFamily: FONT, fontSize: 40, color: C.orange, lineHeight: 1.5}}>而是进入一条可检查的路径。</div>
      <div style={{marginTop: 40, display: "flex", gap: 14, flexWrap: "wrap"}}><Pill>文本</Pill><Pill>截图</Pill><Pill>代码</Pill><Pill>环境</Pill></div>
      <div style={{marginTop: 60, fontFamily: MONO, fontSize: 22, color: C.muted}}>MULTIMODAL INPUT → EVIDENCE → REPLAY</div>
    </div>
    <div style={{position: "absolute", right: 110, top: 390}}><TerminalCard frame={frame} /></div>
    <div style={{position: "absolute", right: 80, bottom: 175, width: 430, height: 2, backgroundColor: C.orange, opacity: fade(frame, 34, 48)}} />
    <div style={{position: "absolute", right: 72, bottom: 190, fontFamily: MONO, fontSize: 18, color: C.orange, opacity: fade(frame, 40, 54)}}>EVIDENCE FIRST</div>
  </>
);

const SceneTwo: React.FC<{frame: number}> = ({frame}) => (
  <>
    <SceneHeader scene={SCENES[1]} frame={frame} />
    <div style={{position: "absolute", left: 100, top: 370, right: 100, display: "flex", gap: 32}}>
      <CompareCard frame={frame} left title="传统问答" color={C.red} items={["复制错误", "得到一条命令", "不知道依据", "环境不匹配"]} />
      <div style={{flex: "0 0 90px", position: "relative"}}><Arrow left={-14} top={220}/><Arrow left={-14} top={308}/></div>
      <CompareCard frame={frame} title="DebugMate" color={C.teal} items={["先脱敏确认", "抽取事实", "检索与引用", "结构化复盘"]} />
    </div>
    <div style={{position: "absolute", left: 100, bottom: 170, display: "flex", gap: 16, alignItems: "center", opacity: fade(frame, 50, 66)}}>
      <span style={{fontFamily: MONO, color: C.muted, fontSize: 21}}>核心转变</span><span style={{fontFamily: FONT, color: C.cream, fontSize: 33}}>从“给答案”到“交付证据”</span>
    </div>
  </>
);

const CompareCard: React.FC<{frame: number; title: string; items: string[]; color: string; left?: boolean}> = ({frame, title, items, color, left = false}) => (
  <div style={{flex: 1, minHeight: 420, padding: 34, backgroundColor: left ? "rgba(235,113,62,.08)" : "rgba(43,166,181,.12)", border: `1px solid ${color}77`, ...rounded(22), opacity: fade(frame, left ? 18 : 30, left ? 36 : 48), translate: `${slide(frame, left ? 18 : 30, left ? 36 : 48, left ? -70 : 70)}px 0px`}}>
    <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}><div style={{fontFamily: FONT, fontSize: 40, color: C.cream, fontWeight: 700}}>{title}</div><Pill color={color} bg={`${color}18`}>{left ? "LOW TRACE" : "TRACEABLE"}</Pill></div>
    <div style={{marginTop: 36, display: "grid", gap: 18}}>{items.map((item, index) => <div key={item} style={{display: "flex", alignItems: "center", gap: 18, padding: "16px 0", borderTop: `1px solid ${C.muted}25`, opacity: fade(frame, 40 + index * 5, 54 + index * 5)}}><span style={{fontFamily: MONO, color, fontSize: 20}}>0{index + 1}</span><span style={{fontFamily: FONT, color: C.cream, fontSize: 28}}>{item}</span></div>)}</div>
  </div>
);

const SceneThree: React.FC<{frame: number}> = ({frame}) => (
  <>
    <SceneHeader scene={SCENES[2]} frame={frame} />
    <div style={{position: "absolute", left: 100, top: 370}}><Img src={staticFile("assets/terminal-module-not-found-redacted.png")} style={{width: 930, height: 470, objectFit: "cover", ...rounded(22), border: `1px solid ${C.teal}88`, opacity: fade(frame, 15, 36), translate: `${slide(frame, 15, 36, -80)}px 0px`, boxShadow: "0 28px 80px rgba(0,0,0,.32)"}} /></div>
    <div style={{position: "absolute", left: 1080, top: 380, width: 680, display: "grid", gap: 18}}>{["绝对路径", "用户名", "Token / 密码", "邮箱与私有标识"].map((label, index) => <PrivacyRow key={label} frame={frame} index={index} label={label} />)}</div>
    <div style={{position: "absolute", left: 1080, bottom: 176, fontFamily: MONO, color: C.green, fontSize: 21, opacity: fade(frame, 50, 64)}}>LOCAL ONLY · USER APPROVAL REQUIRED</div>
  </>
);

const PrivacyRow: React.FC<{frame: number; index: number; label: string}> = ({frame, index, label}) => (
  <div style={{display: "flex", alignItems: "center", gap: 20, padding: "21px 24px", backgroundColor: "rgba(22,54,83,.88)", border: `1px solid ${index % 2 ? C.orange : C.teal}66`, ...rounded(16), opacity: fade(frame, 22 + index * 8, 38 + index * 8), translate: `${slide(frame, 22 + index * 8, 38 + index * 8, 70)}px 0px`}}><div style={{fontFamily: MONO, color: index % 2 ? C.orange : C.teal, fontSize: 20}}>P0{index + 1}</div><div style={{fontFamily: FONT, color: C.cream, fontSize: 29, flex: 1}}>{label}</div><Pill color={C.green} bg="rgba(89,198,168,.12)">REDACTED</Pill></div>
);

const SceneFour: React.FC<{frame: number}> = ({frame}) => {
  const sources = ["Python", "pip / venv", "PyTorch", "CUDA", "NVIDIA", "Hugging Face", "Ultralytics", "Windows", "PowerShell"];
  return <>
    <SceneHeader scene={SCENES[3]} frame={frame} />
    <div style={{position: "absolute", left: 100, top: 365, width: 860}}>
      <div style={{fontFamily: MONO, color: C.muted, fontSize: 20, marginBottom: 18}}>KNOWLEDGE BUILD · GENERAL MODE-ECO 1</div>
      <div style={{display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14}}>{sources.map((source, index) => <div key={source} style={{padding: "18px 16px", backgroundColor: `${index % 3 === 0 ? C.teal : C.panel}22`, border: `1px solid ${index % 3 === 0 ? C.teal : C.muted}55`, ...rounded(14), fontFamily: FONT, color: C.cream, fontSize: 25, opacity: fade(frame, 15 + index * 3, 30 + index * 3), scale: 0.92 + fade(frame, 15 + index * 3, 30 + index * 3) * 0.08}}>{source}<span style={{display: "block", marginTop: 8, fontFamily: MONO, fontSize: 15, color: C.muted}}>source_{String(index + 1).padStart(2, "0")}</span></div>)}</div>
      <div style={{marginTop: 26, display: "flex", gap: 12, alignItems: "center", opacity: fade(frame, 48, 62)}}><Pill color={C.teal}>17 SOURCES</Pill><span style={{fontFamily: FONT, color: C.muted, fontSize: 24}}>标题 · URL · 版本 · 哈希 · 错误类别</span></div>
    </div>
    <RetrievalPanel frame={frame} />
  </>;
};

const RetrievalPanel: React.FC<{frame: number}> = ({frame}) => (
  <div style={{position: "absolute", right: 95, top: 360, width: 700, minHeight: 460, padding: 28, backgroundColor: "rgba(11,25,40,.82)", border: `1px solid ${C.orange}77`, ...rounded(22), opacity: fade(frame, 28, 44), translate: `${slide(frame, 28, 44, 80)}px 0px`}}>
    <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}><Label color={C.orange}>RETRIEVAL TRACE</Label><Pill color={C.green} bg="rgba(89,198,168,.10)">HITS · 04</Pill></div>
    <div style={{marginTop: 28, padding: 22, borderLeft: `4px solid ${C.orange}`, backgroundColor: "rgba(235,113,62,.09)", fontFamily: MONO, color: C.cream, fontSize: 22, lineHeight: 1.6}}>ModuleNotFoundError<br/><span style={{color: C.orange}}>→ python-venv / python-import</span></div>
    <div style={{marginTop: 22, display: "grid", gap: 10}}>{["document_id", "segment_id", "source_url", "relevance_score"].map((key, index) => <div key={key} style={{display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: `1px solid ${C.muted}20`, fontFamily: MONO, fontSize: 18, opacity: fade(frame, 50 + index * 5, 62 + index * 5)}}><span style={{color: C.muted}}>{key}</span><span style={{color: index === 2 ? C.teal : C.cream}}>{index === 2 ? "docs.python.org/3/..." : index === 3 ? "0.4026" : "bound · verified"}</span></div>)}</div>
  </div>
);

const SceneFive: React.FC<{frame: number}> = ({frame}) => (
  <>
    <SceneHeader scene={SCENES[4]} frame={frame} />
    <div style={{position: "absolute", left: 100, top: 360, width: 1020, display: "grid", gap: 12}}>{["observed_facts", "root_cause_candidates", "checks", "verification_steps", "limitations"].map((key, index) => <EvidenceRow key={key} frame={frame} index={index} keyName={key} value={["4 facts · 100% confidence", "1 candidate · evidence bound", "read-only · no side effects", "import check · expected result", "uncertainty is explicit"][index]} />)}</div>
    <div style={{position: "absolute", right: 105, top: 370, width: 600, height: 485, backgroundColor: "#0b1826", border: `1px solid ${C.teal}66`, ...rounded(22), padding: 28, opacity: fade(frame, 30, 46), translate: `${slide(frame, 30, 46, 80)}px 0px`, boxShadow: "0 28px 80px rgba(0,0,0,.28)"}}>
      <div style={{fontFamily: MONO, fontSize: 18, color: C.teal}}>diagnosis.json · schema 1.1.0</div>
      <pre style={{marginTop: 25, fontFamily: MONO, fontSize: 20, lineHeight: 1.7, color: C.cream, whiteSpace: "pre-wrap"}}>{`{\n  "case_id": "case_8f6c...",\n  "category": "dependency_environment",\n  "confidence": 0.95,\n  "evidence": [ ... ],\n  "fixes": [],\n  "limitations": [ ... ]\n}`}</pre>
      <div style={{position: "absolute", right: 24, bottom: 20}}><Pill color={C.green} bg="rgba(89,198,168,.10)">STRICT JSON</Pill></div>
    </div>
  </>
);

const EvidenceRow: React.FC<{frame: number; index: number; keyName: string; value: string}> = ({frame, index, keyName, value}) => (
  <div style={{display: "flex", alignItems: "center", gap: 20, minHeight: 68, padding: "0 22px", backgroundColor: index % 2 ? "rgba(22,54,83,.72)" : "rgba(27,70,97,.5)", borderLeft: `5px solid ${index === 1 ? C.orange : C.teal}`, ...rounded(12), opacity: fade(frame, 16 + index * 8, 32 + index * 8), translate: `${slide(frame, 16 + index * 8, 32 + index * 8, -70)}px 0px`}}><span style={{width: 32, fontFamily: MONO, color: C.teal, fontSize: 18}}>0{index + 1}</span><span style={{width: 340, fontFamily: MONO, color: C.cream, fontSize: 21}}>{keyName}</span><span style={{fontFamily: FONT, color: C.muted, fontSize: 22}}>{value}</span></div>
);

const SceneSix: React.FC<{frame: number}> = ({frame}) => (
  <>
    <SceneHeader scene={SCENES[5]} frame={frame} />
    <div style={{position: "absolute", left: 100, top: 375, display: "flex", gap: 20}}>
      <OutputCard frame={frame} index={0} title="REPORT" subtitle="Markdown / 引用 / 局限" color={C.teal}><div style={{fontFamily: MONO, color: C.cream, fontSize: 17, lineHeight: 1.7}}>## 诊断摘要<br/><span style={{color: C.orange}}>根因候选</span><br/>检查与验证步骤<br/><span style={{color: C.muted}}>evidence_id: ...</span></div></OutputCard>
      <OutputCard frame={frame} index={1} title="PNG CARD" subtitle="Pillow / 确定性" color={C.orange}><Img src={staticFile("assets/card.png")} style={{width: 316, height: 205, objectFit: "cover", ...rounded(10)}} /></OutputCard>
      <OutputCard frame={frame} index={2} title="MP3 RECAP" subtitle="同一 recap_text" color={C.green}><Waveform frame={frame} width={310} height={76} color={C.green}/><div style={{fontFamily: MONO, color: C.muted, fontSize: 17, marginTop: 18}}>00:00 ━━━━━ 01:12</div></OutputCard>
    </div>
    <div style={{position: "absolute", left: 102, bottom: 168, display: "flex", alignItems: "center", gap: 16, opacity: fade(frame, 54, 68)}}><Pill color={C.orange}>SAME CASE_ID</Pill><span style={{fontFamily: MONO, color: C.muted, fontSize: 21}}>→ 同源 → 同次运行 → 可下载 ZIP</span></div>
  </>
);

const OutputCard: React.FC<{frame: number; index: number; title: string; subtitle: string; color: string; children: React.ReactNode}> = ({frame, index, title, subtitle, color, children}) => (
  <div style={{width: 380, height: 390, padding: 24, backgroundColor: "rgba(22,54,83,.86)", border: `1px solid ${color}77`, ...rounded(20), opacity: fade(frame, 18 + index * 8, 36 + index * 8), translate: `${slide(frame, 18 + index * 8, 36 + index * 8, index === 0 ? -70 : 70)}px 0px`}}><div style={{fontFamily: MONO, color, fontSize: 21, letterSpacing: 2}}>{title}</div><div style={{fontFamily: FONT, color: C.muted, fontSize: 20, marginTop: 8}}>{subtitle}</div><div style={{height: 1, backgroundColor: `${color}55`, margin: "24px 0"}}>{children}</div></div>
);

const SceneSeven: React.FC<{frame: number}> = ({frame}) => (
  <>
    <SceneHeader scene={SCENES[6]} frame={frame} />
    <div style={{position: "absolute", left: 100, top: 380, right: 100, display: "grid", gap: 16}}>{[
      ["DIFY LIVE", "云端增强", "实时检索 / 视觉 / LLM", C.teal, "AVAILABLE WHEN PROVIDER IS STABLE"],
      ["LOCAL FALLBACK", "本地交付", "规则 / Pydantic / Pillow / TTS", C.orange, "REAL FAILURE IS PRESERVED"],
      ["FIXED REPLAY", "稳定演示", "版本化证据包 / 可复算", C.green, "TRUTHFUL DEMO BOUNDARY"],
    ].map(([name, desc, detail, color, status], index) => <FallbackRow key={name} frame={frame} index={index} name={name as string} desc={desc as string} detail={detail as string} color={color as string} status={status as string}/>)}</div>
    <div style={{position: "absolute", right: 110, bottom: 150, fontFamily: FONT, color: C.cream, fontSize: 31, opacity: fade(frame, 52, 66)}}>失败节点可见，交付仍可继续。</div>
  </>
);

const FallbackRow: React.FC<{frame: number; index: number; name: string; desc: string; detail: string; color: string; status: string}> = ({frame, index, name, desc, detail, color, status}) => (
  <div style={{display: "flex", alignItems: "center", padding: "23px 28px", backgroundColor: `${color}12`, border: `1px solid ${color}66`, ...rounded(16), opacity: fade(frame, 15 + index * 9, 32 + index * 9), translate: `${slide(frame, 15 + index * 9, 32 + index * 9, 80)}px 0px`}}><div style={{width: 220, fontFamily: MONO, color, fontSize: 23, letterSpacing: 1}}>{name}</div><div style={{width: 190, fontFamily: FONT, color: C.cream, fontSize: 26}}>{desc}</div><div style={{flex: 1, fontFamily: FONT, color: C.muted, fontSize: 22}}>{detail}</div><div style={{fontFamily: MONO, color, fontSize: 16}}>{status}</div></div>
);

const SceneEight: React.FC<{frame: number}> = ({frame}) => (
  <>
    <SceneHeader scene={SCENES[7]} frame={frame} />
    <div style={{position: "absolute", left: 100, top: 370, right: 100, display: "flex", alignItems: "center", justifyContent: "space-between"}}>{[
      ["INPUT", "文本 · 截图", C.orange], ["PRIVACY", "本机脱敏", C.teal], ["REASON", "检索 · 结构化", C.green], ["OUTPUT", "报告 · PNG · MP3", C.orange],
    ].map(([title, detail, color], index) => <div key={title} style={{display: "flex", alignItems: "center"}}><div style={{width: 300, height: 180, padding: 26, backgroundColor: `${color}15`, border: `1px solid ${color}88`, ...rounded(20), opacity: fade(frame, 18 + index * 8, 34 + index * 8), scale: 0.9 + fade(frame, 18 + index * 8, 34 + index * 8) * 0.1}}><div style={{fontFamily: MONO, color: color as string, fontSize: 21}}>{title as string}</div><div style={{marginTop: 28, fontFamily: FONT, color: C.cream, fontSize: 29}}>{detail as string}</div></div>{index < 3 && <Arrow left={0} top={0}/>}</div>)}</div>
    <div style={{position: "absolute", left: 100, bottom: 188, display: "flex", alignItems: "center", gap: 28, opacity: fade(frame, 60, 78)}}><div style={{fontFamily: FONT, color: C.cream, fontSize: 37}}>可运行</div><div style={{width: 1, height: 42, backgroundColor: C.muted}}/><div style={{fontFamily: FONT, color: C.cream, fontSize: 37}}>可复核</div><div style={{width: 1, height: 42, backgroundColor: C.muted}}/><div style={{fontFamily: FONT, color: C.cream, fontSize: 37}}>可追溯</div></div>
    <div style={{position: "absolute", right: 110, bottom: 194, fontFamily: MONO, color: C.teal, fontSize: 21, opacity: fade(frame, 70, 86)}}>THANK YOU · DEBUGMATE V0.1</div>
  </>
);

const CaptionOverlay: React.FC = () => {
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();
  const {delayRender, continueRender, cancelRender} = useDelayRender();
  const [handle] = useState(() => delayRender());
  const [captions, setCaptions] = useState<Caption[] | null>(null);
  const load = useCallback(async () => {
    try {
      const response = await fetch(staticFile("captions.json"));
      if (!response.ok) throw new Error(`caption fetch failed: ${response.status}`);
      setCaptions((await response.json()) as Caption[]);
      continueRender(handle);
    } catch (error) {
      cancelRender(error);
    }
  }, [cancelRender, continueRender, handle]);
  useEffect(() => { void load(); }, [load]);
  const current = useMemo(() => {
    if (!captions) return null;
    const timeMs = (frame / fps) * 1000;
    return captions.find((caption) => timeMs >= caption.startMs && timeMs < caption.endMs) ?? null;
  }, [captions, frame, fps]);
  if (!current) return null;
  return <div style={{position: "absolute", left: 270, right: 270, bottom: 88, padding: "12px 26px", backgroundColor: "rgba(7,18,29,.78)", border: "1px solid rgba(175,195,209,.25)", ...rounded(12), textAlign: "center", color: C.cream, fontFamily: FONT, fontSize: 25, lineHeight: 1.35, opacity: 0.94}}>{current.text}</div>;
};

const Scene: React.FC<{scene: SceneContent; timing: SceneTiming}> = ({scene, timing}) => {
  // A Sequence resets useCurrentFrame() to zero at its own start. Subtracting
  // timing.startFrame here would push every scene after the first one into
  // negative animation time and leave the visual layer blank.
  const localFrame = useCurrentFrame();
  return <AbsoluteFill><Background frame={localFrame} sceneId={scene.id}/>{scene.id === 1 && <SceneOne frame={localFrame}/>} {scene.id === 2 && <SceneTwo frame={localFrame}/>} {scene.id === 3 && <SceneThree frame={localFrame}/>} {scene.id === 4 && <SceneFour frame={localFrame}/>} {scene.id === 5 && <SceneFive frame={localFrame}/>} {scene.id === 6 && <SceneSix frame={localFrame}/>} {scene.id === 7 && <SceneSeven frame={localFrame}/>} {scene.id === 8 && <SceneEight frame={localFrame}/>}<Footer timing={timing} frame={localFrame}/><div style={{position: "absolute", inset: 0, backgroundColor: C.orange, opacity: interpolate(localFrame, [timing.durationInFrames - 18, timing.durationInFrames], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"})}} /></AbsoluteFill>;
};

export const DebugMateVideo: React.FC<{includeAudio: boolean}> = ({includeAudio}) => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{backgroundColor: C.navy2, fontFamily: FONT}}>
    {includeAudio && <Audio src={staticFile("audio/ambient-bed.mp3")} volume={0.07} loop />}
    {SCENES.map((scene, index) => {
      const timing = SCENE_TIMINGS[index];
      return <Sequence key={scene.id} from={timing.startFrame} durationInFrames={timing.durationInFrames}><Scene scene={scene} timing={timing}/>{includeAudio && <Audio src={staticFile(`audio/scene-${String(scene.id).padStart(2, "0")}.mp3`)} volume={1}/>}</Sequence>;
    })}
    <CaptionOverlay />
    <div style={{position: "absolute", top: 0, left: 0, right: 0, height: 8, backgroundColor: C.orange, scale: `${interpolate(frame, [0, 60], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"})} 1`, transformOrigin: "left"}} />
  </AbsoluteFill>;
};

export const DebugMateVisual: React.FC = () => <DebugMateVideo includeAudio={false} />;
