import React, { useState, useRef, useEffect } from "react";
import "./App.css";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

// ── FIX: use the correct deployed backend URL ────────────────────────────────
const BACKEND_URL =
  process.env.REACT_APP_BACKEND_URL ||
  "https://genai-rag-system-3.onrender.com";

// ── Session ID: generated once, persisted in localStorage ───────────────────
function getOrCreateSessionId() {
  const KEY = "rag_session_id";
  let sid = localStorage.getItem(KEY);
  if (!sid) {
    sid =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `session-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    localStorage.setItem(KEY, sid);
  }
  return sid;
}

const SESSION_ID = getOrCreateSessionId();

// ── Tiny SVG icons ───────────────────────────────────────────────────────────
const IconSparkle = () => (
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z" />
  </svg>
);

const IconChevron = () => (
  <svg viewBox="0 0 24 24">
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

const IconCheck = () => (
  <svg viewBox="0 0 24 24">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

const IconHistory = () => (
  <svg
    viewBox="0 0 24 24"
    width="18"
    height="18"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="10" />
    <polyline points="12 6 12 12 16 14" />
  </svg>
);

const IconClose = () => (
  <svg
    viewBox="0 0 24 24"
    width="16"
    height="16"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

// ── Static data ──────────────────────────────────────────────────────────────
const CAPABILITIES = [
  "Semantic vector search",
  "Keyword + semantic hybrid",
  "PDF, DOCX, CSV support",
  "OCR for scanned docs",
  "Table structure preserved",
  "Strictly grounded answers",
];

const DOC_TYPES = [
  { ext: "PDF", label: "PDF Documents", cls: "ext-pdf" },
  { ext: "DOCX", label: "Word Documents", cls: "ext-docx" },
  { ext: "CSV", label: "CSV Datasets", cls: "ext-csv" },
];

const EXAMPLE_SECTIONS = [
  {
    label: "ExoHabitAI Dataset",
    questions: [
      "What is the objective of the ExoHabitAI dataset?",
      "Which planetary parameters evaluate habitability?",
      "How is habitability predicted in the dataset?",
    ],
  },
  {
    label: "Internship Certificate",
    questions: [
      "What does the No Objection Certificate state?",
      "What internship duration is mentioned?",
      "Which organization issued the certificate?",
    ],
  },
  {
    label: "Generative AI & LLMs",
    questions: [
      "What is Generative AI?",
      "How is GenAI different from traditional AI?",
      "What are Large Language Models?",
      "What are foundation models?",
    ],
  },
  {
    label: "AI Concepts",
    questions: [
      "What is the transformer architecture?",
      "What are vector embeddings?",
      "Why are vector databases used in AI?",
      "What is Retrieval-Augmented Generation?",
    ],
  },
  {
    label: "LLM Development",
    questions: [
      "What is prompt engineering?",
      "What is zero-shot prompting?",
      "What is few-shot prompting?",
      "What is in-context learning?",
    ],
  },
  {
    label: "AI Project Lifecycle",
    questions: [
      "What are the stages of the LLM project lifecycle?",
      "How do you select the right LLM for a project?",
      "What is fine-tuning in language models?",
      "What is reinforcement learning from human feedback?",
    ],
  },
];

// ── Helpers ──────────────────────────────────────────────────────────────────
function formatDateLabel(dateKey) {
  const today = new Date().toISOString().slice(0, 10);
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
  if (dateKey === today) return "Today";
  if (dateKey === yesterday) return "Yesterday";
  return new Date(dateKey + "T00:00:00").toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

// ── Accordion ────────────────────────────────────────────────────────────────
function Accordion({ icon, iconClass, label, open, onToggle, children }) {
  return (
    <div className="dd">
      <div className="dd-header" onClick={onToggle}>
        <div className="dd-header-left">
          <div className={`dd-header-icon ${iconClass}`}>{icon}</div>
          <span className="dd-header-label">{label}</span>
        </div>
        <div className={`dd-chevron ${open ? "open" : ""}`}>
          <IconChevron />
        </div>
      </div>
      <div className={`dd-content ${open ? "show" : ""}`}>
        <div className="dd-inner">{children}</div>
      </div>
    </div>
  );
}

// ── History Panel ─────────────────────────────────────────────────────────────
function HistoryPanel({ sessionId, onClose, onReplay }) {
  const [history, setHistory] = useState({});
  const [loading, setLoading] = useState(true);
  const [expandedDate, setExpandedDate] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(
      `${BACKEND_URL}/history?session_id=${encodeURIComponent(sessionId)}`
    )
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        const hist = data.history || {};
        setHistory(hist);
        // Auto-expand the most recent date
        const dates = Object.keys(hist);
        if (dates.length > 0) setExpandedDate(dates[0]);
        setLoading(false);
      })
      .catch(() => {
        setError("Could not load history. Please try again.");
        setLoading(false);
      });
  }, [sessionId]);

  const dates = Object.keys(history);

  return (
    <div className="history-panel">
      {/* header */}
      <div className="history-header">
        <span className="history-title">Chat history</span>
        <button className="history-close-btn" onClick={onClose}>
          <IconClose />
        </button>
      </div>

      {/* states */}
      {loading && <div className="history-loading">Loading…</div>}
      {error && <div className="history-error">{error}</div>}
      {!loading && !error && dates.length === 0 && (
        <div className="history-empty">No history yet. Start chatting!</div>
      )}

      {/* ── FIX: wrap date groups in .history-scroll so CSS overflow/scroll works ── */}
      {!loading && !error && dates.length > 0 && (
        <div className="history-scroll">
          {dates.map((dateKey) => (
            <div key={dateKey} className="history-date-group">
              {/* date pill / toggle */}
              <button
                className={`history-date-pill ${
                  expandedDate === dateKey ? "active" : ""
                }`}
                onClick={() =>
                  setExpandedDate(expandedDate === dateKey ? null : dateKey)
                }
              >
                <span
                  className={`history-chevron ${
                    expandedDate === dateKey ? "open" : ""
                  }`}
                >
                  ›
                </span>
                {formatDateLabel(dateKey)}
                <span className="history-count">
                  {history[dateKey].length}
                </span>
              </button>

              {/* messages for this date */}
              {expandedDate === dateKey && (
                <div className="history-messages">
                  {history[dateKey].map((msg, idx) => (
                    <div key={idx} className="history-message-item">
                      {/* clicking the query text replays it */}
                      <div
                        className="history-query"
                        onClick={() => onReplay(msg.query)}
                        title="Click to ask again"
                      >
                        <span className="history-q-icon">Q</span>
                        {msg.query}
                      </div>
                      <div className="history-answer">
                        {msg.answer.length > 200
                          ? msg.answer.slice(0, 200) + "…"
                          : msg.answer}
                      </div>
                      {msg.sources?.length > 0 && (
                        <div className="history-sources">
                          {msg.sources.map((s, i) => (
                            <span key={i} className="history-source-chip">
                              {s.name}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [open1, setOpen1] = useState(false);
  const [open2, setOpen2] = useState(false);
  const [open3, setOpen3] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleOpen = () => {
    setIsOpen(true);
    setOpen1(false);
    setOpen2(false);
    setOpen3(false);
    setShowHistory(false);
  };

  const sendMessage = async (text) => {
    const query = (text || input).trim();
    if (!query || loading) return;

    // Close history panel when user starts chatting
    setShowHistory(false);

    setMessages((prev) => [...prev, { type: "user", text: query }]);
    setInput("");
    setLoading(true);

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 120000);

      const res = await fetch(`${BACKEND_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          session_id: SESSION_ID,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          type: "ai",
          text: data.response || "No response",
          sources: data.sources || [],
          cacheHit: data.cache_hit || false,
        },
      ]);
    } catch (err) {
      const isAbort = err.name === "AbortError";
      setMessages((prev) => [
        ...prev,
        {
          type: "ai",
          text: isAbort
            ? "⚠️ Request timed out. The backend may be waking up — please try again in a few seconds."
            : "⚠️ Backend is unreachable. Please try again in a few seconds.",
          sources: [],
          cacheHit: false,
        },
      ]);
    }

    setLoading(false);
  };

  const handleClose = () => {
    setIsOpen(false);
    // NOTE: we do NOT clear messages — they stay in React state for this
    // browser tab session. Full history is persisted in Firebase and
    // survives page reloads via the /history endpoint.
    setInput("");
    setShowHistory(false);
  };

  const handleHistoryReplay = (query) => {
    setShowHistory(false);
    sendMessage(query);
  };

  const codeRenderer = {
    code({ inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || "");
      return !inline && match ? (
        <SyntaxHighlighter
          style={oneDark}
          language={match[1]}
          PreTag="div"
          {...props}
        >
          {String(children).replace(/\n$/, "")}
        </SyntaxHighlighter>
      ) : (
        <code {...props}>{children}</code>
      );
    },
  };

  return (
    <div className="app">
      <div className="bg-grid" />
      <div className="bg-orb1" />
      <div className="bg-orb2" />

      {/* landing */}
      <div className="landing">
        <div className="landing-badge">
          <span className="landing-badge-dot" />
          Live · Connected to Drive
        </div>
        <h1>
          Ask anything about
          <br />
          <span>your documents</span>
        </h1>
        <p className="landing-sub">
          RAG-powered search across your Google Drive. Grounded answers, cited
          sources.
        </p>
      </div>

      {/* floating orb button */}
      <div className="chat-btn-container">
        <button
          className="chat-btn"
          onClick={handleOpen}
          aria-label="Open chat"
        >
          <IconSparkle />
        </button>
      </div>

      {/* overlay + panel */}
      <div className={`overlay ${isOpen ? "open" : ""}`}>
        <div className={`chat-panel ${isOpen ? "panel-open" : ""}`}>

          {/* header */}
          <div className="chat-header">
            <div className="header-top">
              <div className="header-left">
                <div className="header-icon">
                  <IconSparkle />
                </div>
                <div>
                  <div className="title">Google Drive RAG</div>
                  <div className="subtitle">
                    Ask questions over your indexed documents
                  </div>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                {/* History toggle */}
                <button
                  className={`history-btn ${showHistory ? "active" : ""}`}
                  onClick={() => setShowHistory((prev) => !prev)}
                  title="Chat history"
                  aria-label="Toggle chat history"
                >
                  <IconHistory />
                </button>
                <button className="close-btn" onClick={handleClose}>
                  ×
                </button>
              </div>
            </div>
            <div className="header-meta">
              <span className="meta-pill">
                <span className="meta-dot" /> Connected
              </span>
              <span className="meta-pill">⚡ Hybrid retrieval</span>
              <span className="meta-pill">🔒 Grounded answers</span>
              <span className="meta-pill">📂 PDF · DOCX · CSV</span>
            </div>
          </div>

          {/* ── History panel (overlays the chat body when open) ── */}
          {showHistory && (
            <HistoryPanel
              sessionId={SESSION_ID}
              onClose={() => setShowHistory(false)}
              onReplay={handleHistoryReplay}
            />
          )}

          {/* ── Chat body + input — hidden when history is open ── */}
          {!showHistory && (
            <>
              <div className="chat-body">
                {/* accordions */}
                <div className="accordions">
                  <Accordion
                    icon="✦"
                    iconClass="blue"
                    label="What this assistant can do"
                    open={open1}
                    onToggle={() => setOpen1(!open1)}
                  >
                    <div className="cap-grid">
                      {CAPABILITIES.map((cap) => (
                        <div className="cap-item" key={cap}>
                          <div className="cap-check">
                            <IconCheck />
                          </div>
                          {cap}
                        </div>
                      ))}
                    </div>
                  </Accordion>

                  <Accordion
                    icon="📄"
                    iconClass="purple"
                    label="Supported document types"
                    open={open2}
                    onToggle={() => setOpen2(!open2)}
                  >
                    <div className="doc-row">
                      {DOC_TYPES.map(({ ext, label, cls }) => (
                        <div className="doc-chip" key={ext}>
                          <span className={`doc-chip-ext ${cls}`}>{ext}</span>
                          {label}
                        </div>
                      ))}
                    </div>
                    <div className="doc-sync-note">
                      ↻ &nbsp;Auto-synced daily from connected Google Drive
                      folder
                    </div>
                  </Accordion>

                  <Accordion
                    icon="💬"
                    iconClass="green"
                    label="Example questions you can ask"
                    open={open3}
                    onToggle={() => setOpen3(!open3)}
                  >
                    <div className="question-sections">
                      {EXAMPLE_SECTIONS.map(({ label, questions }) => (
                        <div key={label}>
                          <div className="q-section-label">{label}</div>
                          <div className="q-chips">
                            {questions.map((q) => (
                              <button
                                key={q}
                                className="q-chip"
                                onClick={() => {
                                  setOpen3(false);
                                  sendMessage(q);
                                }}
                              >
                                {q}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </Accordion>
                </div>

                {/* messages */}
                {messages.map((msg, i) => (
                  <div key={i} className={`msg-row ${msg.type}`}>
                    <div className="bubble">
                      {msg.type === "ai" && (
                        <div className="ai-label">
                          <span className="ai-label-dot" /> RAG · Response
                          {msg.cacheHit && (
                            <span
                              className="cache-hit-badge"
                              title="Answered from your session cache — no LLM call made"
                            >
                              ⚡ cached
                            </span>
                          )}
                        </div>
                      )}
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={codeRenderer}
                      >
                        {msg.text}
                      </ReactMarkdown>
                      {msg.type === "ai" && msg.sources?.length > 0 && (
                        <div className="sources">
                          {msg.sources.map((src, idx) =>
                            src.url ? (
                              <a
                                key={idx}
                                href={src.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="source-chip"
                              >
                                {src.name}
                              </a>
                            ) : (
                              <span key={idx} className="source-chip">
                                {src.name}
                              </span>
                            )
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="loading-wrap">
                    <div className="loading-bubble">
                      <span />
                      <span />
                      <span />
                    </div>
                  </div>
                )}

                <div ref={chatEndRef} />
              </div>

              {/* input bar */}
              <div className="input-bar">
                <div className="input-inner">
                  <input
                    className="chat-input"
                    placeholder="Ask something about your documents…"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                  />
                  <button
                    className="send-btn"
                    onClick={() => sendMessage()}
                    disabled={loading}
                  >
                    ↑
                  </button>
                </div>
              </div>
            </>
          )}

        </div>
      </div>
    </div>
  );
}