import React, { useState } from "react";
import ChatOverlay from "../components/ChatOverlay";

export default function LandingPage({ sessionId }) {
  const [chatOpen, setChatOpen] = useState(false);

  return (
    <div style={{ color: "white", padding: "40px" }}>
      <h1>Main Page</h1>

      <button onClick={() => setChatOpen(true)}>
        Open Chat
      </button>

      <ChatOverlay
        sessionId={sessionId}
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
      />
    </div>
  );
}