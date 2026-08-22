import { useState } from "react";
import type { ChatResponse, Source } from "../api";
import SourceCitation from "./SourceCitation";

interface Message {
  role: "user" | "assistant";
  text: string;
  sources?: Source[];
}

interface Props {
  repoId: string;
  repoUrl: string;
  chatStream: (
    repoId: string,
    question: string,
    onToken: (text: string) => void,
    onSources: (sources: Source[]) => void
  ) => Promise<void>;
}

export default function ChatWindow({ repoId, repoUrl, chatStream }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setMessages((m) => [...m, { role: "user", text: question }, { role: "assistant", text: "" }]);
    setInput("");
    setLoading(true);

    try {
      await chatStream(
        repoId,
        question,
        (token) => {
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = {
              ...copy[copy.length - 1],
              text: copy[copy.length - 1].text + token,
            };
            return copy;
          });
        },
        (sources) => {
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = { ...copy[copy.length - 1], sources };
            return copy;
          });
        }
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong";
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = { role: "assistant", text: `Error: ${msg}` };
        return copy;
      });
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
            <div className="message-text">
              {m.text || (loading && i === messages.length - 1 ? "▋" : "")}
            </div>
            {m.sources && m.sources.length > 0 && (
              <div className="sources">
                {m.sources.map((s, j) => (
                  <SourceCitation key={j} source={s} />
                ))}
              </div>
            )}
          </div>
        ))}
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
