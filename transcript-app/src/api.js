const API_BASE = "http://127.0.0.1:8000";

export async function fetchLive(since) {
  let url = `${API_BASE}/live`;
  if (since) url += `?since=${encodeURIComponent(since)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch live data");
  return await res.json();
}

export async function askAI(question) {
  const res = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error("AI request failed");
  return await res.json();
}
