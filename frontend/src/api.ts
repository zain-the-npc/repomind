const BASE_URL = "http://127.0.0.1:8000";

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