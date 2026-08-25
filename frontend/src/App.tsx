import { useState } from "react";
import RepoInput from "./components/RepoInput";
import ChatWindow from "./components/ChatWindow";
import { indexRepo, chatStream } from "./api";
import "./App.css";

export default function App() {
  const [repoId, setRepoId] = useState<string | null>(null);
  const [repoUrl, setRepoUrl] = useState<string>("");

  function handleIndexed(id: string, url: string) {
    setRepoId(id);
    setRepoUrl(url);
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>RepoMind</h1>
        <p className="tagline">Paste a repo. Ask it anything. Get cited answers.</p>
      </header>

      <div className="hosting-note">
        Hosted on a free-tier backend — first request after idle time may take
        30-60s to wake up, and responses can occasionally be slower under load.
        Not a bug, just free hosting limits.
      </div>

      <main className="app-main">
        {!repoId ? (
          <RepoInput onIndexed={handleIndexed} indexRepo={indexRepo} />
        ) : (
          <ChatWindow repoId={repoId} repoUrl={repoUrl} chatStream={chatStream} />
        )}
      </main>
    </div>
  );
}
