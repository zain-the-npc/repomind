import { useState } from "react";

interface Props {
    onIndexed: (repoId: string, repoUrl: string) => void;
    indexRepo: (url: string) => Promise<string>;
}

export default function RepoInput({ onIndexed, indexRepo }: Props) {
    const [url, setUrl] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!url.trim()) return;
        setLoading(true);
        setError(null);
        try {
            const repoId = await indexRepo(url.trim());
            onIndexed(repoId, url.trim());
        } catch (err) {
            setError(err instanceof Error ? err.message : "Something went wrong");
        } finally {
            setLoading(false);
        }
    }

    return (
        <form className="repo-input" onSubmit={handleSubmit}>
            <label htmlFor="repo-url">Repository URL</label>
            <div className="repo-input-row">
                <input
                    id="repo-url"
                    type="text"
                    placeholder="https://github.com/owner/repo"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={loading}
                />
                <button type="submit" disabled={loading || !url.trim()}>
                    {loading ? "Indexing…" : "Index repo"}
                </button>
            </div>
            {loading && (
                <p className="hint">
                    Fetching files, chunking, embedding. Takes a minute for larger repos.
                </p>
            )}
            {error && <p className="error">{error}</p>}
        </form>
    );
}