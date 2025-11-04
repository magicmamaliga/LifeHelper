import React, { useState, useEffect } from "react";
import Transcript from "./components/Transcript.jsx";
import { fetchLive } from "./api";

function App() {
  const [segments, setSegments] = useState([]);
  const [lastTimestamp, setLastTimestamp] = useState(null);

  // Poll live transcript periodically
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const data = await fetchLive(lastTimestamp);
        const newSegs = data.segments || [];
        if (newSegs.length > 0) {
          setSegments(prev => {
            // 🔍 remove duplicates by timestamp
            const existingTimestamps = new Set(prev.map(s => s.timestamp));
            const newSegments = data.segments.filter(s => !existingTimestamps.has(s.timestamp));
            return [...prev, ...newSegments];
          });
          setLastTimestamp(newSegs[newSegs.length - 1].timestamp);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [lastTimestamp]);

  return (
    <div style={{ margin: "2rem", fontFamily: "system-ui" }}>
      <h2>🎙 Live Transcript Viewer</h2>
      <p style={{ color: "#555" }}>
        Automatically displaying new transcription lines from your running Whisper backend.
      </p>
      <Transcript segments={segments} />
    </div>
  );
}

export default App;
