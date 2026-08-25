import type { Source } from "../api";

export default function SourceCitation({ source }: { source: Source }) {
  return (
    <div className="source-chip">
      <span className="source-file">{source.file}</span>
      {source.function && <span className="source-fn">:: {source.function}</span>}
      <span className="source-lines">L{source.lines}</span>
    </div>
  );
}
