import React, { useEffect, useRef, useState } from "react";
import { askAI } from "../api";

export default function Transcript({ segments }) {
  const containerRef = useRef(null);
  const [selectedText, setSelectedText] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const PARAGRAPH_LENGTH = 4; // number of segments per paragraph

  // --- Group text into paragraphs automatically ---
  const paragraphs = [];
  for (let i = 0; i < segments.length; i += PARAGRAPH_LENGTH) {
    const chunk = segments.slice(i, i + PARAGRAPH_LENGTH);
    const text = chunk.map((s) => s.text.trim()).join(" ");
    paragraphs.push(text);
  }

  // --- Scroll to bottom on new text ---
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [paragraphs.length]);

  // --- Handle text selection and query AI ---
  const handleSelection = async () => {
    const selection = window.getSelection().toString().trim();
    if (!selection) return;

    setSelectedText(selection);
    setAiResponse("⏳ Thinking...");

    try {
      const { answer } = await askAI(selection);
      setAiResponse(answer);
    } catch (err) {
      setAiResponse("❌ Error: " + err.message);
    }
  };

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "1rem",
        height: "85vh",
      }}
    >
      {/* LEFT SIDE — LIVE TRANSCRIPT */}
      <div
        ref={containerRef}
        onMouseUp={handleSelection}
        style={{
          overflowY: "auto",
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

      {/* RIGHT SIDE — AI ANSWER PANEL */}
      <div
        style={{
          overflowY: "auto",
          background: "#fafafa",
          border: "1px solid #ddd",
          padding: "1.5rem",
          borderRadius: "10px",
        }}
      >
        <h3>📝 Selected Text</h3>
        <div
          style={{
            minHeight: "6rem",
            background: "#fff",
            padding: "1rem",
            borderRadius: "8px",
            boxShadow: "inset 0 1px 2px rgba(0,0,0,0.05)",
            marginBottom: "1rem",
            whiteSpace: "pre-wrap",
          }}
        >
          {selectedText || "Select some text from the transcript on the left."}
        </div>

        <h3>🤖 AI Response</h3>
        <div
          style={{
            minHeight: "10rem",
            background: "#fff",
            padding: "1rem",
            borderRadius: "8px",
            boxShadow: "inset 0 1px 2px rgba(0,0,0,0.05)",
            whiteSpace: "pre-wrap",
          }}
        >
          {aiResponse}
        </div>
      </div>
    </div>
  );
}
