import { useState } from "react";
import type { ChatResponse } from "./api";
import SourceCitation from "./SourceCitation";

interface Message {
    role: "user" | "assistant";
    text: string;
    sources?: ChatResponse["sources"];
}

interface Props {
    repoId: string;
    repoUrl: string;
    chat: (repoId: string, question: string) => Promise<ChatResponse>;
}

export default function ChatWindow({ repoId, repoUrl, chat }: Props) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        const question = input.trim();
        if (!question || loading) return;

        setMessages((m) => [...m, { role: "user", text: question }]);
        setInput("");
        setLoading(true);

        try {
            const result = await chat(repoId, question);
            setMessages((m) => [
                ...m,
                { role: "assistant", text: result.answer, sources: result.sources },
            ]);
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Something went wrong";
            setMessages((m) => [...m, { role: "assistant", text: `Error: ${msg}` }]);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="chat-window">
            <div className="chat-header">
                <span className="repo-badge">{repoUrl.replace("https://github.com/", "")}</span>
            </div>

            <div className="messages">
                {messages.length === 0 && (
                    <p className="empty-state">Ask anything about this codebase.</p>
                )}
                {messages.map((m, i) => (
                    <div key={i} className={`message message-${m.role}`}>
                        <div className="message-text">{m.text}</div>
                        {m.sources && m.sources.length > 0 && (
                            <div className="sources">
                                {m.sources.map((s, j) => (
                                    <SourceCitation key={j} source={s} />
                                ))}
                            </div>
                        )}
                    </div>
                ))}
                {loading && <div className="message message-assistant loading">Thinking…</div>}
            </div>

            <form className="chat-input-row" onSubmit={handleSubmit}>
                <input
                    type="text"
                    placeholder="How does authentication work?"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={loading}
                />
                <button type="submit" disabled={loading || !input.trim()}>
                    Send
                </button>
            </form>
        </div>
    );
}