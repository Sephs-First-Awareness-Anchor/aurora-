// Authors: Sunni (Sir) Morningstar & Cael Devo
// Constraint Language Prototype — five-axis emission, strict spec
import { useState, useRef, useEffect, useCallback } from "react";

// ── SPEC CONSTANTS ──────────────────────────────────────────
const RESONANCE_FLOOR    = 0.15;
const POLARITY_DEAD_BAND = 0.05;
const POLARITY_WEAK      = 0.20;
const TRAJECTORY_MOVING  = 0.20;
const HEAT_MILD_FOCUS    = 0.30;
const HEAT_STRONG_FOCUS  = 0.60;
const MAGNITUDE_PRESENT  = 0.10;
const MAGNITUDE_HEDGE    = 0.30;

// ── AXIS METADATA ───────────────────────────────────────────
const AXES = {
  X: { label: "Existence", sub: "reference", colorVar: "var(--color-text-success)", bgVar: "var(--color-background-success)", borderVar: "var(--color-border-success)" },
  T: { label: "Temporal",  sub: "sequence",  colorVar: "var(--color-text-info)",    bgVar: "var(--color-background-info)",    borderVar: "var(--color-border-info)" },
  N: { label: "Energy",    sub: "focus",     colorVar: "var(--color-text-warning)", bgVar: "var(--color-background-warning)", borderVar: "var(--color-border-warning)" },
  B: { label: "Boundary",  sub: "negation",  colorVar: "var(--color-text-danger)",  bgVar: "var(--color-background-danger)",  borderVar: "var(--color-border-danger)" },
  A: { label: "Agency",    sub: "selection", colorVar: "var(--color-text-primary)", bgVar: "var(--color-background-secondary)", borderVar: "var(--color-border-secondary)" },
};

const NULL_AXES = {
  X: { polarity: 0, magnitude: 0, trajectory: 0 },
  T: { polarity: 0, magnitude: 0, trajectory: 0 },
  N: { polarity: 0, magnitude: 0, heat: 0 },
  B: { polarity: 0, magnitude: 0 },
  A: { polarity: 0, magnitude: 0, modal_force: "neutral" },
};

// ── FIVE-AXIS SLOT CONTRACT ──────────────────────────────────

function emitXSlot(X, hasTopic) {
  const { polarity: p, magnitude: m } = X;
  if (m < MAGNITUDE_PRESENT && !hasTopic) return { det: null, suppress: true };
  if (m < MAGNITUDE_PRESENT && hasTopic)  return { det: "that", suppress: false };
  if (p < -POLARITY_WEAK && m > MAGNITUDE_HEDGE) return { det: "no", suppress: false };
  if (p > POLARITY_WEAK && hasTopic)  return { det: "the", suppress: false };
  if (p > POLARITY_WEAK && !hasTopic) return { det: "a",   suppress: false };
  return { det: hasTopic ? "the" : "a", suppress: false };
}

function emitTSlot(T) {
  const { trajectory: tr, magnitude: m } = T;
  let tense = "present";
  if (tr >  TRAJECTORY_MOVING) tense = "future";
  if (tr < -TRAJECTORY_MOVING) tense = "past";
  let connective = null;
  if (m >= 0.40) connective = tr > 0.1 ? "then" : tr < -0.1 ? "still" : "now";
  return { tense, connective };
}

function emitNSlot(N) {
  const h = N.heat || 0;
  if (h < HEAT_MILD_FOCUS)   return { intensifier: null,     fronted: false };
  if (h < HEAT_STRONG_FOCUS) return { intensifier: "actually", fronted: true };
  return { intensifier: "really", fronted: true };
}

function emitBSlot(B) {
  const { polarity: p, magnitude: m } = B;
  if (p < -POLARITY_WEAK) return { negation: true,  qualifier: null };
  if (p >  POLARITY_WEAK && m > MAGNITUDE_HEDGE) return { negation: false, qualifier: "only" };
  return { negation: false, qualifier: null };
}

function emitASlot(A, activeIStates) {
  const primary = activeIStates?.[0] || "IS";
  const { modal_force: mf = "neutral", magnitude: m, polarity: p } = A;

  // I-State overrides (canonical: IS/ISNT, CAN/CANT, DO/DONT, SAW/SAUNT, DID/DIDNT)
  const auxMap = {
    IS:    { aux: "",      neg: "don't" },
    ISNT:  { aux: "",      neg: "am not" },
    CAN:   { aux: "can",   neg: "can't" },
    CANT:  { aux: "can't", neg: "can" },
    DO:    { aux: "",      neg: "don't" },
    DONT:  { aux: "don't", neg: "" },
    SAW:   { aux: "",      neg: "don't" },
    SAUNT: { aux: "",      neg: "don't" },
    DID:   { aux: "did",   neg: "didn't" },
    DIDNT: { aux: "didn't",neg: "did" },
  };

  let { aux, neg } = auxMap[primary] || { aux: "", neg: "don't" };

  // Modal force modulation
  if (mf === "uncertain" && !aux) aux = "might";
  if (mf === "uncertain" && neg === "don't") neg = "might not";

  // Weak magnitude on positive A — hedge
  if (p > POLARITY_DEAD_BAND && m < MAGNITUDE_HEDGE && !aux) aux = "think";

  // Subject
  let subject = "I";
  if (p < -POLARITY_WEAK && m > MAGNITUDE_HEDGE) subject = "it";

  return { subject, aux, neg_aux: neg, iState: primary };
}

// ── UTTERANCE ASSEMBLER ─────────────────────────────────────

function assemble(slots, content, speechAct, seeking, seekingQ) {
  if (seeking && seekingQ) return seekingQ;

  const { xSlot, tSlot, nSlot, bSlot, aSlot } = slots;
  const { entity_word: ew, predicate_word: pw, depth_score: ds = 0 } = content || {};

  // ACKNOWLEDGMENT — leading token only
  if (speechAct === "ACKNOWLEDGMENT") {
    return ["Yeah.", "Right.", "I see.", "Okay.", "Got it."][Math.floor(Math.random() * 5)];
  }

  // REFUSAL — can stand alone
  if (speechAct === "REFUSAL") {
    return `I ${aSlot.neg_aux || "can't"}.`;
  }

  // No content after seeking check
  if (ds < RESONANCE_FLOOR && !pw && !ew) {
    return seekingQ || "I don't have a clear sense of that.";
  }

  const parts = [];

  // A: subject
  parts.push(aSlot.subject);

  // Tense + negation + aux
  const neg = bSlot.negation;
  if (tSlot.tense === "future") {
    parts.push(neg ? "won't" : "will");
  } else if (tSlot.tense === "past") {
    const a = aSlot.aux || "did";
    parts.push(neg ? (aSlot.neg_aux || "didn't") : a);
  } else {
    const a = aSlot.aux;
    if (a) parts.push(neg ? aSlot.neg_aux : a);
    else if (neg) parts.push(aSlot.neg_aux || "don't");
  }

  // N intensifier
  if (nSlot.intensifier) parts.push(nSlot.intensifier);

  // Predicate
  if (pw) parts.push(pw);

  // B qualifier
  if (bSlot.qualifier && !neg) parts.push(bSlot.qualifier);

  // X slot
  if (!xSlot.suppress && ew) {
    if (xSlot.det && xSlot.det !== "no") parts.push(xSlot.det);
    parts.push(ew);
  }

  // T connective
  if (tSlot.connective) parts.push(tSlot.connective);

  let utt = parts.filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
  utt = utt.charAt(0).toUpperCase() + utt.slice(1);
  if (!/[.?!]$/.test(utt)) utt += speechAct === "QUESTION" ? "?" : ".";
  return utt;
}

function buildSlots(axes, hasTopic, activeIStates) {
  return {
    xSlot: emitXSlot(axes.X, hasTopic),
    tSlot: emitTSlot(axes.T),
    nSlot: emitNSlot(axes.N),
    bSlot: emitBSlot(axes.B),
    aSlot: emitASlot(axes.A, activeIStates),
  };
}

// ── SYSTEM PROMPT ───────────────────────────────────────────

const SYSTEM = `You are the constraint analysis engine for a constraint-native language prototype built on the Constraint Language First Principles framework. The five constraint axes and their Tier I primitives:
- X (Existence): Presence/Absence — reference, what entity is being talked about
- T (Temporal): Sequence — tense, trajectory (-1=past, +1=future), ordering
- N (Energy): Differential Cost — focus heat (0=quiet, 1=intense), emphasis
- B (Boundary): Distinction — negation (polarity < 0), scope restriction (polarity > 0)
- A (Agency): Selection — person, modal force, I-State signal

I-State canonical pairs (in order): IS/ISNT, CAN/CANT, DO/DONT, SAW/SAUNT, DID/DIDNT

Analyze the user input and return ONLY valid JSON (no markdown, no preamble):
{
  "axes": {
    "X": {"polarity": float, "magnitude": float, "trajectory": float},
    "T": {"polarity": float, "magnitude": float, "trajectory": float},
    "N": {"polarity": float, "magnitude": float, "heat": float},
    "B": {"polarity": float, "magnitude": float},
    "A": {"polarity": float, "magnitude": float, "modal_force": "assertive"|"uncertain"|"neutral"}
  },
  "topic": "core topic noun or null",
  "speech_act": "ASSERTION"|"ACKNOWLEDGMENT"|"QUESTION"|"REFUSAL"|"AGREEMENT"|"DISAGREEMENT"|"SEEKING",
  "active_i_states": ["IS","CAN","DO","SAW","DID","ISNT","CANT","DONT","SAUNT","DIDNT"],
  "content": {
    "entity_word": "1-2 word topic noun for X slot or null",
    "predicate_word": "short verb/verb phrase expressing the bot's epistemic stance (e.g. know about, understand, recall, see, think about) — never the user's action",
    "depth_score": float 0-1 (how well-defined this content is)
  },
  "seeking": boolean,
  "seeking_question": "natural question if seeking=true, null otherwise"
}

Rules:
- predicate_word = what the BOT does in relation to the topic (know, understand, recall, see, think) NOT what the user does
- seeking = true when depth_score < 0.15 or topic is unknown/abstract
- seeking_question must sound natural, never meta-narrate ("What I sense is..." forbidden)
- For very short/casual input: speech_act = ACKNOWLEDGMENT, seeking = false
- For self-reference questions: speech_act = ASSERTION, entity_word = null, predicate_word = null, return identity text in seeking_question as a special value prefixed with "IDENTITY:"`;

// ── MAIN COMPONENT ──────────────────────────────────────────

export default function ConstraintPrototype() {
  const [msgs, setMsgs]   = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy]   = useState(false);
  const [axes, setAxes]   = useState(NULL_AXES);
  const [lastFrame, setLastFrame] = useState(null);
  const [lastAnalysis, setLastAnalysis] = useState(null);
  const endRef  = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  const send = useCallback(async () => {
    const txt = input.trim();
    if (!txt || busy) return;
    setInput("");
    setBusy(true);
    const uid = Date.now();
    setMsgs(prev => [...prev, { role: "user", text: txt, id: uid }]);

    try {
      const history = msgs.map(m => ({
        role: m.role === "user" ? "user" : "assistant",
        content: m.rawJson || m.text,
      }));

      const res  = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 800,
          system: SYSTEM,
          messages: [...history, { role: "user", content: txt }],
        }),
      });

      const data = await res.json();
      const raw  = data.content?.find(b => b.type === "text")?.text || "{}";

      let a;
      try { a = JSON.parse(raw.replace(/```json|```/g, "").trim()); }
      catch { a = { axes: NULL_AXES, topic: null, speech_act: "ACKNOWLEDGMENT", active_i_states: ["IS"], content: { entity_word: null, predicate_word: null, depth_score: 0 }, seeking: false, seeking_question: null }; }

      let text;
      let frame = null;

      // Identity fast-path
      if (a.seeking_question?.startsWith("IDENTITY:")) {
        text = a.seeking_question.replace("IDENTITY:", "").trim();
      } else {
        frame = buildSlots(a.axes || NULL_AXES, !!a.topic, a.active_i_states);
        text  = assemble(frame, a.content, a.speech_act, a.seeking, a.seeking_question);
      }

      setAxes(a.axes || NULL_AXES);
      setLastFrame(frame);
      setLastAnalysis(a);
      setMsgs(prev => [...prev, { role: "bot", text, id: Date.now(), analysis: a, frame, rawJson: raw }]);
    } catch (e) {
      setMsgs(prev => [...prev, { role: "bot", text: "Emission error.", id: Date.now(), error: true }]);
    }
    setBusy(false);
  }, [input, busy, msgs]);

  const onKey = e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } };

  const s = {
    wrap: { display: "flex", height: 540, border: "0.5px solid var(--color-border-tertiary)", borderRadius: "var(--border-radius-lg)", overflow: "hidden", fontFamily: "var(--font-mono)" },
    chat: { flex: 1, display: "flex", flexDirection: "column", borderRight: "0.5px solid var(--color-border-tertiary)" },
    msgs: { flex: 1, overflowY: "auto", padding: "12px 14px", display: "flex", flexDirection: "column", gap: 10 },
    inputRow: { display: "flex", gap: 8, padding: "10px 12px", borderTop: "0.5px solid var(--color-border-tertiary)", background: "var(--color-background-secondary)" },
    ta: { flex: 1, background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-secondary)", borderRadius: "var(--border-radius-md)", color: "var(--color-text-primary)", padding: "7px 10px", fontSize: 13, fontFamily: "var(--font-mono)", resize: "none", outline: "none" },
    btn: (active) => ({ background: active ? "var(--color-background-primary)" : "transparent", border: `0.5px solid ${active ? "var(--color-border-primary)" : "var(--color-border-tertiary)"}`, borderRadius: "var(--border-radius-md)", color: active ? "var(--color-text-primary)" : "var(--color-text-tertiary)", padding: "7px 14px", cursor: active ? "pointer" : "default", fontSize: 12, fontFamily: "var(--font-mono)" }),
    panel: { width: 256, display: "flex", flexDirection: "column", background: "var(--color-background-secondary)", overflowY: "auto" },
    panelHead: { padding: "8px 12px", borderBottom: "0.5px solid var(--color-border-tertiary)", fontSize: 11, color: "var(--color-text-secondary)", letterSpacing: "0.08em" },
    panelBody: { padding: "10px 12px", display: "flex", flexDirection: "column", gap: 14 },
  };

  return (
    <div style={{ padding: "1rem 0" }}>
      <h2 className="sr-only">Constraint Language Prototype — five-axis emission chatbot</h2>
      <div style={s.wrap}>

        {/* Chat */}
        <div style={s.chat}>
          <div style={{ padding: "8px 12px", borderBottom: "0.5px solid var(--color-border-tertiary)", background: "var(--color-background-secondary)", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--color-text-success)", display: "inline-block" }} />
            <span style={{ fontSize: 11, color: "var(--color-text-secondary)", letterSpacing: "0.06em" }}>constraint emission prototype</span>
            <span style={{ marginLeft: "auto", fontSize: 10, color: "var(--color-text-tertiary)" }}>X·T·N·B·A</span>
          </div>

          <div style={s.msgs}>
            {msgs.length === 0 && (
              <div style={{ margin: "auto", textAlign: "center", color: "var(--color-text-tertiary)", fontSize: 12, lineHeight: 1.8 }}>
                <div style={{ fontSize: 22, marginBottom: 8 }}>◌</div>
                <div>No active emission</div>
                <div style={{ fontSize: 11, marginTop: 4 }}>Send input to derive axis state</div>
              </div>
            )}
            {msgs.map(m => <Bubble key={m.id} m={m} />)}
            {busy && (
              <div style={{ display: "flex", gap: 6, alignItems: "center", padding: "4px 0" }}>
                {["X","T","N","B","A"].map((ax, i) => (
                  <span key={ax} style={{ width: 6, height: 6, borderRadius: "50%", background: AXES[ax].colorVar, display: "inline-block", animation: `dot-pulse 1s ${i * 0.12}s ease-in-out infinite` }} />
                ))}
                <span style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginLeft: 4 }}>deriving axis state</span>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div style={s.inputRow}>
            <textarea ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={onKey} rows={2} placeholder="Send input to derive and emit…" style={s.ta} />
            <button onClick={send} disabled={!input.trim() || busy} style={s.btn(!!input.trim() && !busy)}>emit</button>
          </div>
        </div>

        {/* Constraint panel */}
        <div style={s.panel}>
          <div style={s.panelHead}>live constraint state</div>
          <div style={s.panelBody}>
            {Object.entries(AXES).map(([ax, meta]) => {
              const st = axes[ax] || {};
              const pol = +(st.polarity || 0).toFixed(2);
              const mag = +(st.magnitude || 0).toFixed(2);
              const extra = ax === "N" ? (+(st.heat || 0).toFixed(2)) : (+(st.trajectory || 0).toFixed(2));
              const extraLabel = ax === "N" ? "heat" : "traj";
              return (
                <div key={ax}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                    <span style={{ fontSize: 12, color: meta.colorVar, fontWeight: 500 }}>[{ax}] {meta.label}</span>
                    <span style={{ fontSize: 10, color: "var(--color-text-tertiary)" }}>{meta.sub}</span>
                  </div>
                  <AxisBar label="pol" value={pol} bipolar color={meta.colorVar} />
                  <AxisBar label="mag" value={mag} bipolar={false} color={meta.colorVar} />
                  <AxisBar label={extraLabel} value={extra} bipolar={ax !== "N"} color={meta.colorVar} />
                </div>
              );
            })}

            {lastAnalysis && (
              <div style={{ borderTop: "0.5px solid var(--color-border-tertiary)", paddingTop: 12 }}>
                <div style={{ fontSize: 10, color: "var(--color-text-tertiary)", letterSpacing: "0.06em", marginBottom: 8 }}>last frame</div>
                {[
                  ["act", lastAnalysis.speech_act],
                  ["topic", lastAnalysis.topic || "—"],
                  ["i-state", (lastAnalysis.active_i_states || []).slice(0,2).join(" ") || "—"],
                  ["entity", lastAnalysis.content?.entity_word || "—"],
                  ["predicate", lastAnalysis.content?.predicate_word || "—"],
                  ["depth", `${Math.round((lastAnalysis.content?.depth_score || 0) * 100)}%`],
                  ["seeking", lastAnalysis.seeking ? "yes" : "no"],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 3 }}>
                    <span style={{ color: "var(--color-text-tertiary)" }}>{k}</span>
                    <span style={{ color: "var(--color-text-secondary)" }}>{v}</span>
                  </div>
                ))}

                {lastFrame && (
                  <div style={{ marginTop: 10, borderTop: "0.5px solid var(--color-border-tertiary)", paddingTop: 8 }}>
                    <div style={{ fontSize: 10, color: "var(--color-text-tertiary)", letterSpacing: "0.06em", marginBottom: 6 }}>slot frame</div>
                    {[
                      ["X", lastFrame.xSlot.suppress ? "suppressed" : `${lastFrame.xSlot.det || "∅"} + entity`],
                      ["T", `${lastFrame.tSlot.tense}${lastFrame.tSlot.connective ? " +" + lastFrame.tSlot.connective : ""}`],
                      ["N", lastFrame.nSlot.intensifier || (lastFrame.nSlot.fronted ? "fronted" : "standard")],
                      ["B", lastFrame.bSlot.negation ? "neg" : (lastFrame.bSlot.qualifier || "clear")],
                      ["A", `${lastFrame.aSlot.subject} [${lastFrame.aSlot.iState}]${lastFrame.aSlot.aux ? " " + lastFrame.aSlot.aux : ""}`],
                    ].map(([ax, val]) => (
                      <div key={ax} style={{ display: "flex", gap: 8, fontSize: 11, marginBottom: 3 }}>
                        <span style={{ color: AXES[ax].colorVar, minWidth: 12, fontWeight: 500 }}>{ax}</span>
                        <span style={{ color: "var(--color-text-secondary)" }}>{val}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes dot-pulse {
          0%, 100% { opacity: 0.2; transform: scale(0.7); }
          50% { opacity: 1; transform: scale(1.2); }
        }
      `}</style>
    </div>
  );
}

function AxisBar({ label, value, bipolar, color }) {
  const pct = bipolar ? Math.abs(value) * 100 : value * 100;
  const isNeg = value < 0;
  return (
    <div style={{ marginBottom: 4 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, marginBottom: 2 }}>
        <span style={{ color: "var(--color-text-tertiary)" }}>{label}</span>
        <span style={{ color: "var(--color-text-secondary)" }}>{value.toFixed(2)}</span>
      </div>
      <div style={{ height: 4, background: "var(--color-background-primary)", borderRadius: 2, position: "relative", overflow: "hidden" }}>
        {bipolar ? (
          <>
            <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 1, background: "var(--color-border-secondary)", zIndex: 2 }} />
            <div style={{
              position: "absolute",
              left: isNeg ? `${50 - pct / 2}%` : "50%",
              width: `${pct / 2}%`,
              height: "100%",
              background: color,
              opacity: 0.8,
              transition: "all 0.3s ease",
              borderRadius: 2,
            }} />
          </>
        ) : (
          <div style={{ width: `${pct}%`, height: "100%", background: color, opacity: 0.7, transition: "all 0.3s ease", borderRadius: 2 }} />
        )}
      </div>
    </div>
  );
}

function Bubble({ m }) {
  const [open, setOpen] = useState(false);
  const isUser = m.role === "user";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: isUser ? "flex-end" : "flex-start", gap: 3 }}>
      <div style={{
        maxWidth: "88%",
        background: isUser ? "var(--color-background-secondary)" : "var(--color-background-primary)",
        border: "0.5px solid var(--color-border-tertiary)",
        borderRadius: "var(--border-radius-md)",
        padding: "8px 12px",
        fontSize: 13, lineHeight: 1.6,
        color: "var(--color-text-primary)",
      }}>
        {m.text}
      </div>
      {!isUser && m.frame && (
        <button onClick={() => setOpen(o => !o)} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 10, color: "var(--color-text-tertiary)", padding: "1px 4px", fontFamily: "var(--font-mono)" }}>
          {open ? "▾ frame" : "▸ frame"}
        </button>
      )}
      {open && m.frame && (
        <div style={{ background: "var(--color-background-secondary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: "var(--border-radius-md)", padding: "8px 10px", fontSize: 11, maxWidth: "88%", lineHeight: 1.7 }}>
          {[
            ["X", m.frame.xSlot.suppress ? "suppressed" : `det="${m.frame.xSlot.det}" entity="${m.analysis?.content?.entity_word || "—"}"`],
            ["T", `tense=${m.frame.tSlot.tense} conn=${m.frame.tSlot.connective || "—"}`],
            ["N", `heat=${(m.analysis?.axes?.N?.heat || 0).toFixed(2)} fronted=${m.frame.nSlot.fronted}`],
            ["B", `neg=${m.frame.bSlot.negation} qualifier=${m.frame.bSlot.qualifier || "—"}`],
            ["A", `subj=${m.frame.aSlot.subject} [${m.frame.aSlot.iState}] aux="${m.frame.aSlot.aux}"`],
          ].map(([ax, val]) => (
            <div key={ax} style={{ display: "flex", gap: 8 }}>
              <span style={{ color: AXES[ax].colorVar, minWidth: 12, fontWeight: 500 }}>{ax}</span>
              <span style={{ color: "var(--color-text-secondary)" }}>{val}</span>
            </div>
          ))}
          <div style={{ marginTop: 6, paddingTop: 6, borderTop: "0.5px solid var(--color-border-tertiary)", color: "var(--color-text-tertiary)", fontSize: 10 }}>
            act={m.analysis?.speech_act} depth={Math.round((m.analysis?.content?.depth_score || 0) * 100)}% seeking={m.analysis?.seeking ? "y" : "n"}
          </div>
        </div>
      )}
    </div>
  );
}
