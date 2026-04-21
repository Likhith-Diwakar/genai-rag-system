import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../App.css";

// ✅ Shared chat component — same as Dashboard
import ChatOverlay from "../components/ChatOverlay";

// ── LandingPage ───────────────────────────────────────────────────────────────
export default function LandingPage({ sessionId }) {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="app">
      <div className="bg-grid" />
      <div className="bg-orb1" />
      <div className="bg-orb2" />

      {/* Landing hero */}
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
          RAG-powered search across your Google Drive. Grounded answers, cited sources.
        </p>
        <button
          className="dashboard-link-btn"
          onClick={() => navigate("/dashboard")}
        >
          Open Knowledge Hub →
        </button>
      </div>

      {/* Floating orb button */}
      <div className="chat-btn-container">
        <button className="chat-btn" onClick={() => setIsOpen(true)} aria-label="Open chat">
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z" />
          </svg>
        </button>
      </div>

      {/* ✅ Shared ChatOverlay — same component as Dashboard */}
      <ChatOverlay
        sessionId={sessionId}
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
      />
    </div>
  );
}