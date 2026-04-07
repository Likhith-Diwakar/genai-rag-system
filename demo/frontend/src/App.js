import React, { useState, useRef, useEffect } from "react";
import "./App.css";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

const BACKEND_URL =
  process.env.REACT_APP_BACKEND_URL ||
  "https://genai-rag-system-2.onrender.com";

/* ── tiny SVG icons ── */
const IconSparkle = () => (
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/>
  </svg>
);

const IconChevron = () => (
  <svg viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>
);

const IconCheck = () => (
  <svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
);

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

export default function App() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [open1, setOpen1] = useState(false);
  const [open2, setOpen2] = useState(false);
  const [open3, setOpen3] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleOpen = () => {
    setIsOpen(true);
    setOpen1(false); setOpen2(false); setOpen3(false);
  };

  const sendMessage = async (text) => {
    const query = text || input;
    if (!query.trim() || loading) return;

    setMessages(prev => [...prev, { type: "user", text: query }]);
    setInput("");
    setLoading(true);

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 120000);

      const res = await fetch(`${BACKEND_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query }),
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (!res.ok) {
        throw new Error("Server error");
      }

      const data = await res.json();

      setMessages(prev => [
        ...prev,
        {
          type: "ai",
          text: data.response || "No response",
          sources: data.sources || [],
        },
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          type: "ai",
          text: "⚠️ Backend is waking up or unreachable. Try again in a few seconds.",
          sources: [],
        },
      ]);
    }

    setLoading(false);
  };

  const handleClose = () => {
    setIsOpen(false);
    setMessages([]); setInput("");
  };

  const codeRenderer = {
    code({ inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || "");
      return !inline && match ? (
        <SyntaxHighlighter style={oneDark} language={match[1]} PreTag="div" {...props}>
          {String(children).replace(/\n$/, "")}
        </SyntaxHighlighter>
      ) : (
        <code {...props}>{children}</code>
      );
    },
  };

  return (
    <div className="app">
      {/* background layers */}
      <div className="bg-grid" />
      <div className="bg-orb1" />
      <div className="bg-orb2" />

      {/* landing */}
      <div className="landing">
        <div className="landing-badge">
          <span className="landing-badge-dot" />
          Live · Connected to Drive
        </div>
        <h1>Ask anything about<br /><span>your documents</span></h1>
        <p className="landing-sub">
          RAG-powered search across your Google Drive. Grounded answers, cited sources.
        </p>
      </div>

      {/* floating orb */}
      <div className="chat-btn-container">
        <button className="chat-btn" onClick={handleOpen} aria-label="Open chat">
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
                <div className="header-icon"><IconSparkle /></div>
                <div>
                  <div className="title">Google Drive RAG</div>
                  <div className="subtitle">Ask questions over your indexed documents</div>
                </div>
              </div>
              <button className="close-btn" onClick={handleClose}>×</button>
            </div>
            <div className="header-meta">
              <span className="meta-pill"><span className="meta-dot" /> Connected</span>
              <span className="meta-pill">⚡ Hybrid retrieval</span>
              <span className="meta-pill">🔒 Grounded answers</span>
              <span className="meta-pill">📂 PDF · DOCX · CSV</span>
            </div>
          </div>

          {/* body */}
          <div className="chat-body">
            <div className="accordions">

              {/* Accordion 1 — Capabilities */}
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
                      <div className="cap-check"><IconCheck /></div>
                      {cap}
                    </div>
                  ))}
                </div>
              </Accordion>

              {/* Accordion 2 — Doc types */}
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
                  ↻ &nbsp;Auto-synced daily from connected Google Drive folder
                </div>
              </Accordion>

              {/* Accordion 3 — Example Qs */}
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
                            onClick={() => { setOpen3(false); sendMessage(q); }}
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
                    </div>
                  )}
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={codeRenderer}>
                    {msg.text}
                  </ReactMarkdown>
                  {msg.type === "ai" && msg.sources?.length > 0 && (
                    <div className="sources">
                      {msg.sources.map((src, idx) => (
                        <a key={idx} href={src.url} target="_blank" rel="noopener noreferrer" className="source-chip">
                          {src.name}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* loading */}
            {loading && (
              <div className="loading-wrap">
                <div className="loading-bubble">
                  <span /><span /><span />
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* input */}
          <div className="input-bar">
            <div className="input-inner">
              <input
                className="chat-input"
                placeholder="Ask something about your documents…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              />
              <button className="send-btn" onClick={() => sendMessage()} disabled={loading}>↑</button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}