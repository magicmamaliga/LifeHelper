import React from "react";
import { askAI } from "../api";

export default function Transcript({ segments }) {
  const handleSelection = async () => {
    const selection = window.getSelection().toString().trim();
    if (!selection) return;
    if (!window.confirm(`Send to AI?\n\n"${selection}"`)) return;
    try {
      const { answer } = await askAI(selection);
      alert("AI says:\n\n" + answer);
    } catch (err) {
      alert("Error: " + err.message);
    }
  };

  return (
    <div onMouseUp={handleSelection}>
      {segments.map((seg, i) => (
        <div
          key={i}
          style={{
            marginBottom: "0.5rem",
            padding: "0.5rem 1rem",
            borderRadius: "8px",
            background: "#fff",
            boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
          }}
        >
          <span style={{ color: "#888", fontSize: "0.9em", marginRight: "0.5rem" }}>
            [{seg.timestamp || seg.start?.toFixed(1) || ""}]
          </span>
          {seg.text}
        </div>
      ))}
    </div>
  );
}
