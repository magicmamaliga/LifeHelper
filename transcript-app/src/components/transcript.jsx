import React, { useEffect, useRef, useState } from "react";
import { askAI } from "../api";

export default function Transcript({ segments }) {
  const containerRef = useRef(null);

  // State
  const [selectedText, setSelectedText] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const [history, setHistory] = useState([]); // [{question, answer}]
  const [currentIndex, setCurrentIndex] = useState(-1); // -1 means "live"
  const [userInput, setUserInput] = useState("");

  const PARAGRAPH_LENGTH = 4;

  // --- Group text into paragraphs automatically ---
  const paragraphs = [];
  for (let i = 0; i < segments.length; i += PARAGRAPH_LENGTH) {
    const chunk = segments.slice(i, i + PARAGRAPH_LENGTH);
    const text = chunk.map((s) => s.text.trim()).join(" ");
    paragraphs.push(text);
  }

  // --- Scroll to bottom on new transcript text ---
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [paragraphs.length]);

  // --- Handle text selection + stream AI response ---
  const handleSelection = async () => {
    const selection = window.getSelection().toString().trim();
    if (!selection) return;

    setSelectedText(selection);
    setAiResponse("⏳ Thinking...");

    let streamed = "";
    try {
      await askAI(selection, (token) => {
        streamed += token;
        setAiResponse(streamed);
      });

      // After completion → save Q&A in history
      setHistory((prev) => [...prev, { question: selection, answer: streamed }]);
      setCurrentIndex((prev) => prev + 1);
    } catch (err) {
      setAiResponse("❌ Error: " + err.message);
    }
  };

  // --- Navigation controls ---
  const handlePrev = () => {
    if (currentIndex > 0) {
      const prevQA = history[currentIndex - 1];
      setCurrentIndex(currentIndex - 1);
      setSelectedText(prevQA.question);
      setAiResponse(prevQA.answer);
    }
  };

  const handleNext = () => {
    if (currentIndex < history.length - 1) {
      const nextQA = history[currentIndex + 1];
      setCurrentIndex(currentIndex + 1);
      setSelectedText(nextQA.question);
      setAiResponse(nextQA.answer);
    }
  };

  const handleUserInputKey = async (e) => {
  if (e.key === "Enter" && userInput.trim()) {
    e.preventDefault();

    const question = userInput.trim();
    setSelectedText(question);
    setAiResponse("⏳ Thinking...");
    setUserInput("");

    let streamed = "";
    try {
      await askAI(question, (token) => {
        streamed += token;
        setAiResponse(streamed);
      });

      // Save into history
      setHistory((prev) => [...prev, { question, answer: streamed }]);
      setCurrentIndex((prev) => prev + 1);
    } catch (err) {
      setAiResponse("❌ Error: " + err.message);
    }
  }
};


  // --- Display counters ---
  const total = history.length;
  const current = currentIndex >= 0 ? currentIndex + 1 : total;

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "1rem",
        height: "100%",
      }}
    >
      {/* LEFT SIDE — LIVE TRANSCRIPT */}
      <div
        ref={containerRef}
        onMouseUp={handleSelection}
        style={{
          overflowY: "auto",
          background: "#fff",
          padding: ".6rem",
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
          display: "flex",
          flexDirection: "column",
          overflowY: "auto",
          background: "#fafafa",
          border: "1px solid #ddd",
          padding: ".6rem",
          borderRadius: "10px",
        }}
      >
      <input
        type="text"
        placeholder="Ask something about this text... (press Enter)"
        value={userInput}
        onChange={(e) => setUserInput(e.target.value)}
        onKeyDown={handleUserInputKey}
        style={{
          padding: "0.6rem 1rem",
          marginBottom: "1rem",
          borderRadius: "8px",
          border: "1px solid #ccc",
          outline: "none",
          fontSize: "1rem",
        }}
      />
      <span>📝 Selected Text</span>
      <div
        style={{
          minHeight: "4rem",
          maxHeight: "6rem",
          background: "#fff",
          padding: "1rem",
          borderRadius: "8px",
          boxShadow: "inset 0 1px 2px rgba(0,0,0,0.05)",
          marginBottom: "0.5rem",
          whiteSpace: "pre-wrap",
          overflowY: "auto",
        }}
      >
        {selectedText || "Select some text from the transcript or answer."}
      </div>

        <span>🤖 AI Response</span>
        <div
          onMouseUp={handleSelection} // 🔥 enable selection inside AI answer too
          style={{
            flexGrow: 1,
            background: "#fff",
            padding: "1rem",
            borderRadius: "8px",
            boxShadow: "inset 0 1px 2px rgba(0,0,0,0.05)",
            whiteSpace: "pre-wrap",
            marginBottom: "1rem",
            overflowY: "auto",
            cursor: "text", // show text cursor to hint you can select
          }}
        >
          {aiResponse}
        </div>

        {/* Navigation Bar */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: "1rem",
          }}
        >
          <button
            onClick={handlePrev}
            disabled={currentIndex <= 0}
            style={{
              padding: "0.2rem 1rem",
              borderRadius: "6px",
              border: "1px solid #ccc",
              background: currentIndex <= 0 ? "#eee" : "#fff",
              cursor: currentIndex <= 0 ? "not-allowed" : "pointer",
              minWidth: "80px",
            }}
          >
            ⬅️ Prev
          </button>

          <span style={{ fontSize: "0.9rem", color: "#555" }}>
            {total > 0 ? `Query ${current} of ${total}` : "No previous queries yet"}
          </span>

          <button
            onClick={handleNext}
            disabled={currentIndex >= history.length - 1}
            style={{
              padding: "0.2rem 1rem",
              borderRadius: "6px",
              border: "1px solid #ccc",
              background:
                currentIndex >= history.length - 1 ? "#eee" : "#fff",
              cursor:
                currentIndex >= history.length - 1 ? "not-allowed" : "pointer",
              minWidth: "80px",
            }}
          >
            Next ➡️
          </button>
        </div>
      </div>
    </div>
  );
}
