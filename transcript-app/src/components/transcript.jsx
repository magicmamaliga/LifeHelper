import React, { useEffect, useRef } from "react";
import { askAI } from "../api";

export default function Transcript({ segments }) {
  const containerRef = useRef(null);
  const PARAGRAPH_LENGTH = 4; // number of segments per paragraph

  // --- Group text into paragraphs automatically ---
  const paragraphs = [];
  for (let i = 0; i < segments.length; i += PARAGRAPH_LENGTH) {
    const chunk = segments.slice(i, i + PARAGRAPH_LENGTH);
    const text = chunk.map((s) => s.text.trim()).join(" ");
    paragraphs.push(text);
  }

  // --- Scroll to bottom whenever new text arrives ---
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [paragraphs.length]); // run each time a new paragraph appears

  // --- Handle text selection for AI ---
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
    <div
      ref={containerRef}
      onMouseUp={handleSelection}
      style={{
        height: "70vh",               // make transcript scrollable
        overflowY: "auto",
        whiteSpace: "pre-wrap",
        background: "#fff",
        padding: "1.5rem",
        borderRadius: "10px",
        boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        lineHeight: 1.7,
      }}
    >
      {paragraphs.length === 0 ? (
        <p style={{ color: "#888" }}>Waiting for transcript...</p>
      ) : (
        paragraphs.map((p, i) => (
          <p key={i} style={{ marginBottom: "1rem" }}>
            {p}
          </p>
        ))
      )}
    </div>
  );
}
