import { useState } from "react";
import RepoInput from "./components/RepoInput";
import ChatWindow from "./components/ChatWindow";
import { indexRepo, chat } from "./api";
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

            <main className="app-main">
                {!repoId ? (
                    <RepoInput onIndexed={handleIndexed} indexRepo={indexRepo} />
                ) : (
                    <ChatWindow repoId={repoId} repoUrl={repoUrl} chat={chat} />
                )}
            </main>
        </div>
    );
}