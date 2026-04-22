import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import Dashboard from "./pages/Dashboard";

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

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage sessionId={SESSION_ID} />} />
        <Route path="/dashboard" element={<Dashboard sessionId={SESSION_ID} />} />
      </Routes>
    </BrowserRouter>
  );
}
