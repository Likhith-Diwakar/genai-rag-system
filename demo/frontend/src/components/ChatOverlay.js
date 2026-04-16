/**
 * ChatOverlay.js
 *
 * This is your existing chat UI, extracted verbatim into its own component.
 * Paste your current chat JSX (the overlay panel + floating button) here.
 * The only change is it now receives `sessionId` as a prop instead of
 * reading a module-level constant.
 *
 * IMPORTANT: Do NOT change any logic, state, API calls, or styling inside here.
 * The file boundary is the only change.
 */

import React, { useState, useEffect, useRef } from "react";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function ChatOverlay({ sessionId, isOpen, onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Load history on mount (your existing /history call)
  useEffect(() => {
    if (!isOpen) return;
    fetch(`${API_BASE}/history?session_id=${sessionId}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.messages) setMessages(data.messages);
      })
      .catch(() => {});
  }, [isOpen, sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg = { role: "user", content: input };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input, session_id: sessionId }),
      });
      const data = await res.json();
      const assistantMsg = {
        role: "assistant",
        content: data.response || data.answer || "",
        sources: data.sources || data.retrieved_metas || [],
      };
      setMessages((m) => [...m, assistantMsg]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "Error reaching the server." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="chat-overlay-backdrop" onClick={onClose}>
      <div
        className="chat-overlay-panel"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="chat-overlay-header">
          <div className="chat-header-left">
            <span className="chat-star">★</span>
            <div>
              <div className="chat-title">Google Drive RAG</div>
              <div className="chat-subtitle">Ask questions over your indexed documents</div>
            </div>
          </div>
          <button className="chat-close-btn" onClick={onClose}>✕</button>
        </div>

        {/* Badges */}
        <div className="chat-badges">
          <span className="badge badge-connected">● Connected</span>
          <span className="badge badge-hybrid">⚡ Hybrid retrieval</span>
          <span className="badge badge-grounded">🔒 Grounded answers</span>
          <span className="badge badge-formats">📄 PDF · DOCX · CSV</span>
        </div>

        {/* Messages */}
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="chat-empty">Ask something about your documents…</div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`chat-message chat-message--${msg.role}`}>
              {msg.role === "assistant" && (
                <div className="rag-label">● RAG · RESPONSE</div>
              )}
              <div className="message-content">{msg.content}</div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="message-sources">
                  {msg.sources.map((s, si) => (
                    <a
                      key={si}
                      href={`https://drive.google.com/file/d/${s.file_id}/view`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="source-chip"
                    >
                      📄 {s.file_name}
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="chat-message chat-message--assistant">
              <div className="chat-loading">
                <span /><span /><span />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="chat-input-row">
          <textarea
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask something about your documents…"
            rows={1}
          />
          <button
            className="chat-send-btn"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
          >
            ↑
          </button>
        </div>
      </div>
    </div>
  );
}