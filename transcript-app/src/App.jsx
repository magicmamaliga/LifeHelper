import React, { useState, useEffect } from "react";
import Transcript from "./components/Transcript";
import UploadForm from "./components/UploadForm";
import { fetchLive } from "./api";

function App() {
  const [segments, setSegments] = useState([]);
  const [lastTimestamp, setLastTimestamp] = useState(null);

  // Poll /live endpoint every 3 seconds
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const data = await fetchLive(lastTimestamp);
        const newSegs = data.segments || [];
        if (newSegs.length > 0) {
          setSegments((prev) => [...prev, ...newSegs]);
          setLastTimestamp(newSegs[newSegs.length - 1].timestamp);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [lastTimestamp]);

  return (
    <div style={{ margin: "2rem", fontFamily: "system-ui" }}>
      <h2>🎙 Live Transcript Viewer</h2>
      <UploadForm setSegments={setSegments} />
      <Transcript segments={segments} />
    </div>
  );
}

export default App;
