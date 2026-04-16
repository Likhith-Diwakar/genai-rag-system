import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import LandingPage from "./pages/LandingPage";
import "./App.css";

// ─── SESSION ID (unchanged — same logic you already had) ───────────────────
const SESSION_ID =
  localStorage.getItem("session_id") ||
  (() => {
    const id = `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    localStorage.setItem("session_id", id);
    return id;
  })();

// ─── LANDING PAGE (your existing JSX, kept exactly as-is) ─────────────────
// Move your existing landing page JSX here OR keep it in a separate file.
// Below is a minimal passthrough so the route still works if you keep
// your existing App component code in LandingPage.js instead.
// If your current App.js renders the landing page inline, paste that
// JSX into a new file src/pages/LandingPage.js and import it here.

export { SESSION_ID };

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Existing landing page — no changes inside LandingPage */}
        <Route path="/" element={<LandingPage sessionId={SESSION_ID} />} />

        {/* New dashboard */}
        <Route
          path="/dashboard"
          element={<Dashboard sessionId={SESSION_ID} />}
        />
      </Routes>
    </Router>
  );
}