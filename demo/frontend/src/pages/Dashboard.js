import eyLogo from "../assets/ey-logo.png";
import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import "../App.css";
import "../Dashboard.css";

// ✅ Single source of truth — full-featured chat (accordions, history, cache badge)
import ChatOverlay from "../components/ChatOverlay";

const BACKEND_URL =
  process.env.REACT_APP_BACKEND_URL ||
  "https://genai-rag-system-2.onrender.com";

// ── Debounce hook ─────────────────────────────────────────────────────────────
function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

// ── Icons ─────────────────────────────────────────────────────────────────────
const IconSparkle = () => (
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style={{ width: 22, height: 22, fill: "white" }}>
    <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z" />
  </svg>
);

const IconFolder = () => (
  <svg viewBox="0 0 24 24" width="22" height="22" fill="white">
    <path d="M10 4H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V8a2 2 0 00-2-2h-8l-2-2z" />
  </svg>
);

const IconTrending = () => (
  <svg viewBox="0 0 24 24" width="22" height="22" fill="white">
    <path d="M3 17l6-6 4 4 7-7v5h2V4h-9v2h5l-5 5-4-4-7 7z" />
  </svg>
);

const IconHistoryCard = () => (
  <svg viewBox="0 0 24 24" width="22" height="22" fill="white">
    <path d="M13 3a9 9 0 100 18A9 9 0 0013 3zm0 2a7 7 0 110 14A7 7 0 0113 5zm-1 3h2v5l4 2-1 1.7-5-2.7V8z" />
  </svg>
);

// ── Search Bar ────────────────────────────────────────────────────────────────
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
    fetch(`${BACKEND_URL}/search_docs?q=${encodeURIComponent(debouncedQuery)}`)
      .then((r) => r.json())
      .then((data) => {
        setResults(data || []);
        setOpen(true);
      })
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [debouncedQuery]);

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
          placeholder="Search documents by name, heading, or topic…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
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
                <span className="db-search-result-arrow">↗</span>
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

// ── Card: Latest Documents ────────────────────────────────────────────────────
function LatestDocumentsCard() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${BACKEND_URL}/documents`)
      .then((r) => r.json())
      .then((data) => setDocs(Array.isArray(data) ? data : []))
      .catch(() => setDocs([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="db-card">
      <div className="db-card-header">
        <span className="db-card-icon">
          <IconFolder />
        </span>
        <div>
          <h2 className="db-card-title">Latest Documents</h2>
          <p className="db-card-subtitle">Recently indexed files</p>
        </div>
      </div>
      <div className="db-card-body">
        {loading && <div className="db-card-loading">Loading…</div>}
        {!loading && docs.length === 0 && (
          <div className="db-card-empty">No documents indexed yet.</div>
        )}
        {!loading &&
          docs.map((doc, i) => (
            <a
              key={i}
              href={
                doc.file_id
                  ? `https://drive.google.com/file/d/${doc.file_id}/view`
                  : "#"
              }
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

// ── Card: Frequently Visited ──────────────────────────────────────────────────
// ✅ Reads from localStorage — updates instantly when doc is clicked in chat
function FrequentDocsCard({ sessionId, refreshKey }) {
  const [docs, setDocs] = useState([]);

  useEffect(() => {
    if (!sessionId) return;
    const storageKey = `frequent_docs_${sessionId}`;
    try {
      const data = JSON.parse(localStorage.getItem(storageKey) || "[]");
      setDocs(Array.isArray(data) ? data : []);
    } catch {
      setDocs([]);
    }
  }, [sessionId, refreshKey]); // refreshKey increments on every doc_clicked event

  return (
    <div className="db-card">
      <div className="db-card-header">
        <span className="db-card-icon">
          <IconTrending />
        </span>
        <div>
          <h2 className="db-card-title">Frequently Visited</h2>
          <p className="db-card-subtitle">Most accessed documents this session</p>
        </div>
      </div>
      <div className="db-card-body">
        {docs.length === 0 && (
          <div className="db-card-empty">
            No activity yet — click a source document in chat to track it here.
          </div>
        )}

        {docs.map((doc, i) => (
          <div key={i} className="db-activity-row">
            <span className="db-activity-label">
              User ({sessionId.slice(0, 8)}) accessed:
            </span>
            <a
              href={doc.url || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="db-activity-query"
              style={{ textDecoration: "underline", cursor: "pointer" }}
            >
              {doc.file_name}
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Card: Recent Activity ─────────────────────────────────────────────────────
// ✅ Accepts refreshKey — re-fetches whenever a new query is sent
function ActivityCard({ sessionId, refreshKey }) {
  const [queries, setQueries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${BACKEND_URL}/history?session_id=${encodeURIComponent(sessionId)}`)
      .then((r) => r.json())
      .then((data) => {
        const hist = data.history || {};
        const all = [];
        Object.values(hist)
          .flat()
          .forEach((msg) => all.push(msg));

        // ✅ Sort latest first
        all.sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0));

        // ✅ Keep only latest 5
        setQueries(all.slice(0, 5));
      })
      .catch(() => setQueries([]))
      .finally(() => setLoading(false));
  }, [sessionId, refreshKey]); // ✅ refreshKey triggers re-fetch on new query

  return (
    <div className="db-card">
      <div className="db-card-header">
        <span className="db-card-icon">
          <IconHistoryCard />
        </span>
        <div>
          <h2 className="db-card-title">Recent Activity</h2>
          <p className="db-card-subtitle">Your recent document queries</p>
        </div>
      </div>
      <div className="db-card-body">
        {loading && <div className="db-card-loading">Loading…</div>}
        {!loading && queries.length === 0 && (
          <div className="db-card-empty">No queries yet this session.</div>
        )}
        {!loading &&
          queries.map((msg, i) => (
            <div key={i} className="db-activity-row">
              <span className="db-activity-label">
                User ({msg.session_id ? msg.session_id.slice(0, 8) : sessionId.slice(0, 8)}) searched:
              </span>
              <span className="db-activity-query">
                "{msg.query?.slice(0, 72)}{msg.query?.length > 72 ? "…" : ""}"
              </span>
              {msg.sources?.length > 0 && (
                <span className="db-activity-source">
                  from {msg.sources[0]?.name}
                </span>
              )}
            </div>
          ))}
      </div>
    </div>
  );
}

// ── Navbar ────────────────────────────────────────────────────────────────────
function DashboardNavbar({ sessionId }) {
  const navigate = useNavigate();
  return (
    <nav className="db-navbar">
      <div
        className="db-navbar-left"
        onClick={() => navigate("/")}
        title="Back to home"
        style={{ cursor: "pointer" }}
      >
        <img src={eyLogo} alt="EY Logo" className="db-ey-logo-img" />
        <span className="db-product-name">KnowledgeVerse</span>
      </div>

      <div className="db-navbar-center">
        <SearchBar />
      </div>

      <div className="db-navbar-right">
        <span className="db-session-label">Session</span>
        <span className="db-session-id" title={sessionId}>
          {sessionId.slice(0, 8)}…
        </span>
      </div>
    </nav>
  );
}

// ── Dashboard Page ────────────────────────────────────────────────────────────
export default function Dashboard({ sessionId }) {
  const [chatOpen, setChatOpen] = useState(false);

  // ✅ Tracks new queries → refreshes ActivityCard automatically
  const [activityRefreshKey, setActivityRefreshKey] = useState(0);

  // ✅ Tracks doc clicks → refreshes FrequentDocsCard automatically
  const [docRefreshKey, setDocRefreshKey] = useState(0);

  useEffect(() => {
    const handleQuerySent = () => setActivityRefreshKey((k) => k + 1);
    window.addEventListener("query_sent", handleQuerySent);
    return () => window.removeEventListener("query_sent", handleQuerySent);
  }, []);

  useEffect(() => {
    const handleDocClicked = () => setDocRefreshKey((k) => k + 1);
    window.addEventListener("doc_clicked", handleDocClicked);
    return () => window.removeEventListener("doc_clicked", handleDocClicked);
  }, []);

  return (
    <div className="db-root">
      <DashboardNavbar sessionId={sessionId} />

      <main className="db-main">
        <div className="db-page-header">
          <h1 className="db-page-title">
            Welcome back,{" "}
            <span className="db-session-display" title={sessionId}>
              {sessionId.slice(0, 8)}
            </span>
          </h1>
          <p className="db-page-subtitle">
            Here are your top KnowledgeVerse tools for a better working world
          </p>
        </div>

        <div className="db-card-grid">
          <LatestDocumentsCard />
          {/* ✅ Reads from localStorage — updates instantly when a source is clicked */}
          <FrequentDocsCard sessionId={sessionId} refreshKey={docRefreshKey} />
          {/* ✅ Passes activityRefreshKey — updates instantly when a query is sent */}
          <ActivityCard sessionId={sessionId} refreshKey={activityRefreshKey} />
        </div>
      </main>

      {/* Floating chat button */}
      <div className="chat-btn-container">
        <button
          className="chat-btn"
          onClick={() => setChatOpen(true)}
          aria-label="Open chat"
        >
          <IconSparkle />
        </button>
      </div>

      {/* ✅ Identical chat overlay as LandingPage */}
      <ChatOverlay
        sessionId={sessionId}
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
      />
    </div>
  );
}
