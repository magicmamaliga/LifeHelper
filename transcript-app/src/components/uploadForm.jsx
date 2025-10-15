import React, { useState } from "react";
import { uploadAudio } from "../api";

export default function UploadForm({ setSegments }) {
  const [status, setStatus] = useState("");

  const handleUpload = async (e) => {
    e.preventDefault();
    const file = e.target.audioFile.files[0];
    if (!file) return alert("Choose an audio file");
    setStatus("⏳ Transcribing locally...");
    try {
      const data = await uploadAudio(file);
      setSegments(data.segments || []);
      setStatus("✅ Transcription complete!");
    } catch (err) {
      setStatus("❌ " + err.message);
    }
  };

  return (
    <div style={{ background: "#fff", padding: "1rem", borderRadius: "10px", marginBottom: "1rem" }}>
      <form onSubmit={handleUpload}>
        <label>
          Choose an audio file: <input type="file" name="audioFile" accept=".wav,.mp3,.m4a" />
        </label>
        <button type="submit">Transcribe</button>
      </form>
      <p>{status}</p>
    </div>
  );
}
