import React, { useState, useEffect, useCallback, useRef } from "react";
import ChatOverlay from "../components/ChatOverlay";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

// ─── DEBOUNCE HOOK ─────────────────────────────────────────────────────────
function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

// ─── SEARCH BAR ────────────────────────────────────────────────────────────
function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debouncedQuery = useDebounce(query, 300);
  const wrapperRef = useRef(null);

  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    fetch(`${API_BASE}/search_docs?q=${encodeURIComponent(debouncedQuery)}`)
      .then((r) => r.json())
      .then((data) => {
        setResults(data || []);
        setOpen(true);
      })
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [debouncedQuery]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div className="db-searchbar-wrapper" ref={wrapperRef}>
      <div className="db-searchbar">
        <span className="db-search-icon">🔍</span>
        <input
          className="db-search-input"
          type="text"
          placeholder="Search documents…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
        />
        {loading && <span className="db-search-spinner" />}
      </div>

      {open && results.length > 0 && (
        <ul className="db-search-dropdown">
          {results.map((doc, i) => (
            <li key={i} className="db-search-result">
              <a
                href={doc.url}
                target="_blank"
                rel="noopener noreferrer"
                className="db-search-result-link"
                onClick={() => setOpen(false)}
              >
                <span className="db-search-result-icon">📄</span>
                <span className="db-search-result-name">{doc.file_name}</span>
                <span className="db-search-result-arrow">→</span>
              </a>
            </li>
          ))}
        </ul>
      )}

      {open && results.length === 0 && !loading && query.trim() && (
        <ul className="db-search-dropdown">
          <li className="db-search-no-result">No documents found for "{query}"</li>
        </ul>
      )}
    </div>
  );
}

// ─── CARD: LATEST DOCUMENTS ───────────────────────────────────────────────
function LatestDocumentsCard() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/documents`)
      .then((r) => r.json())
      .then((data) => setDocs(data || []))
      .catch(() => setDocs([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="db-card">
      <div className="db-card-header">
        <span className="db-card-icon">📁</span>
        <h2 className="db-card-title">Latest Documents</h2>
      </div>
      <div className="db-card-body">
        {loading && <div className="db-card-loading">Loading…</div>}
        {!loading && docs.length === 0 && (
          <div className="db-card-empty">No documents indexed yet.</div>
        )}
        {!loading && docs.map((doc, i) => (
          <a
            key={i}
            href={`https://drive.google.com/file/d/${doc.file_id}/view`}
            target="_blank"
            rel="noopener noreferrer"
            className="db-doc-row"
          >
            <span className="db-doc-row-icon">📄</span>
            <span className="db-doc-row-name">{doc.file_name}</span>
            <span className="db-doc-row-arrow">↗</span>
          </a>
        ))}
      </div>
    </div>
  );
}

// ─── CARD: FREQUENTLY VISITED ─────────────────────────────────────────────
function FrequentDocsCard({ sessionId }) {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/frequent_docs?session_id=${sessionId}`)
      .then((r) => r.json())
      .then((data) => setDocs(data || []))
      .catch(() => setDocs([]))
      .finally(() => setLoading(false));
  }, [sessionId]);

  return (
    <div className="db-card">
      <div className="db-card-header">
        <span className="db-card-icon">🔥</span>
        <h2 className="db-card-title">Frequently Visited</h2>
      </div>
      <div className="db-card-body">
        {loading && <div className="db-card-loading">Loading…</div>}
        {!loading && docs.length === 0 && (
          <div className="db-card-empty">No activity yet this session.</div>
        )}
        {!loading && docs.map((doc, i) => (
          <a
            key={i}
            href={`https://drive.google.com/file/d/${doc.file_id}/view`}
            target="_blank"
            rel="noopener noreferrer"
            className="db-doc-row"
          >
            <span className="db-doc-rank">#{i + 1}</span>
            <span className="db-doc-row-name">{doc.file_name}</span>
            <span className="db-doc-freq-badge">{doc.count}×</span>
          </a>
        ))}
      </div>
    </div>
  );
}

// ─── CARD: ACTIVITY ───────────────────────────────────────────────────────
function ActivityCard({ sessionId }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/history?session_id=${sessionId}`)
      .then((r) => r.json())
      .then((data) => {
        // Extract user messages from history
        const msgs = (data.messages || [])
          .filter((m) => m.role === "user")
          .slice(-10)
          .reverse();
        setHistory(msgs);
      })
      .catch(() => setHistory([]))
      .finally(() => setLoading(false));
  }, [sessionId]);

  return (
    <div className="db-card">
      <div className="db-card-header">
        <span className="db-card-icon">⚡</span>
        <h2 className="db-card-title">Recent Activity</h2>
      </div>
      <div className="db-card-body">
        {loading && <div className="db-card-loading">Loading…</div>}
        {!loading && history.length === 0 && (
          <div className="db-card-empty">No queries yet this session.</div>
        )}
        {!loading && history.map((msg, i) => (
          <div key={i} className="db-activity-row">
            <span className="db-activity-label">User searched:</span>
            <span className="db-activity-query">
              "{msg.content?.slice(0, 80)}{msg.content?.length > 80 ? "…" : ""}"
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── NAVBAR ───────────────────────────────────────────────────────────────
function DashboardNavbar({ sessionId }) {
  return (
    <nav className="db-navbar">
      <div className="db-navbar-left">
        <span className="db-ey-logo">EY</span>
        <span className="db-product-name">KnowledgeVerse</span>
      </div>

      <div className="db-navbar-center">
        <SearchBar />
      </div>

      <div className="db-navbar-right">
        <span className="db-session-label">Session</span>
        <span className="db-session-id" title={sessionId}>
          {sessionId.slice(0, 16)}…
        </span>
      </div>
    </nav>
  );
}

// ─── DASHBOARD PAGE ───────────────────────────────────────────────────────
export default function Dashboard({ sessionId }) {
  const [chatOpen, setChatOpen] = useState(false);

  return (
    <div className="db-root">
      <DashboardNavbar sessionId={sessionId} />

      <main className="db-main">
        <div className="db-page-header">
          <h1 className="db-page-title">Knowledge Hub</h1>
          <p className="db-page-subtitle">
            Your indexed documents, activity, and insights — all in one place.
          </p>
        </div>

        <div className="db-card-grid">
          <LatestDocumentsCard />
          <FrequentDocsCard sessionId={sessionId} />
          <ActivityCard sessionId={sessionId} />
        </div>
      </main>

      {/* Floating chat button — identical to landing page behavior */}
      <button
        className="chat-fab"
        onClick={() => setChatOpen(true)}
        aria-label="Open chat"
      >
        ★
      </button>

      {/* Existing ChatOverlay — zero changes to its internals */}
      <ChatOverlay
        sessionId={sessionId}
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
      />
    </div>
  );
}
