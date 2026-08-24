const BASE_URL = "https://repomind-8mms.onrender.com";

export interface Source {
  file: string;
  function: string | null;
  lines: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
}

export async function indexRepo(repoUrl: string): Promise<string> {
  const res = await fetch(`${BASE_URL}/index`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Indexing failed");
  const data = await res.json();
  return data.repo_id;
}

export async function chat(repoId: string, question: string): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_id: repoId, question }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Query failed");
  return res.json();
}

export async function chatStream(
  repoId: string,
  question: string,
  onToken: (text: string) => void,
  onSources: (sources: Source[]) => void
): Promise<void> {
  const res = await fetch(`${BASE_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_id: repoId, question }),
  });
  if (!res.ok || !res.body) throw new Error("Streaming request failed");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = JSON.parse(line.slice(6));
      if (payload.type === "token") onToken(payload.text);
      else if (payload.type === "sources") onSources(payload.sources);
      else if (payload.type === "error") throw new Error(payload.text);
    }
  }
}
