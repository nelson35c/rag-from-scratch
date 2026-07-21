"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Shape returned by the FastAPI /ask endpoint. */
type AskResponse = {
  answer: string;
  citations: string[];
};

type Turn = {
  id: number;
  question: string;
  answer?: string;
  citations?: string[];
  error?: string;
};

type Connection = "checking" | "online" | "offline";

const STARTERS = [
  "Why do I keep getting ModuleNotFoundError after pip install?",
  "What does overlap do in chunking, and why does it matter?",
  "Why isn't similarity stored as a column in the table?",
  "Why does the number 1536 appear in so many places?",
];

/** Renders [chunk#1] markers inside answer text as real citation chips. */
function withCitations(text: string): ReactNode[] {
  return text.split(/(\[[^\]\s]+\])/g).map((part, i) => {
    const match = part.match(/^\[([^\]\s]+)\]$/);
    if (!match) return <span key={i}>{part}</span>;
    return (
      <span
        key={i}
        className="mx-0.5 inline-flex items-center rounded-sm bg-accent-soft px-1 py-px align-baseline font-mono text-[11px] text-accent"
      >
        {match[1]}
      </span>
    );
  });
}

export default function Home() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [connection, setConnection] = useState<Connection>("checking");
  const [theme, setTheme] = useState<"light" | "dark" | null>(null);

  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Confirm the backend is reachable before the user types into a dead box.
  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => (r.ok ? setConnection("online") : setConnection("offline")))
      .catch(() => setConnection("offline"));
  }, []);

  useEffect(() => {
    const stored = document.documentElement.getAttribute("data-theme");
    if (stored === "dark" || stored === "light") {
      setTheme(stored);
    } else {
      setTheme(
        window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light",
      );
    }
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, busy]);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("theme", next);
    } catch {
      // Private browsing — the toggle still works for this session.
    }
  }

  async function ask(question: string) {
    const trimmed = question.trim();
    if (!trimmed || busy) return;

    const id = Date.now();
    setTurns((prev) => [...prev, { id, question: trimmed }]);
    setDraft("");
    setBusy(true);

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed }),
      });

      if (!response.ok) {
        throw new Error(`The API returned ${response.status}.`);
      }

      const data: AskResponse = await response.json();
      setTurns((prev) =>
        prev.map((t) =>
          t.id === id
            ? { ...t, answer: data.answer, citations: data.citations }
            : t,
        ),
      );
      setConnection("online");
    } catch {
      setTurns((prev) =>
        prev.map((t) =>
          t.id === id
            ? {
                ...t,
                error:
                  "Couldn't reach the API. Check that uvicorn is running on port 8000, then ask again.",
              }
            : t,
        ),
      );
      setConnection("offline");
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  const statusColor =
    connection === "online"
      ? "bg-ok"
      : connection === "offline"
        ? "bg-bad"
        : "bg-muted";

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-10 border-b border-line bg-bg/85 backdrop-blur">
        <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-4 px-5 py-3.5">
          <div className="min-w-0">
            <h1 className="truncate text-[15px] font-semibold tracking-tight text-ink">
              Notes Retrieval
            </h1>
            <p className="label mt-0.5">Grounded in your own RAG notes</p>
          </div>

          <div className="flex shrink-0 items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className={`size-1.5 rounded-full ${statusColor}`} />
              <span className="label">
                {connection === "online"
                  ? "API up"
                  : connection === "offline"
                    ? "API down"
                    : "…"}
              </span>
            </span>

            <button
              type="button"
              onClick={toggleTheme}
              className="cursor-pointer rounded-sm border border-line px-2 py-1 font-mono text-[10px] font-medium tracking-[0.14em] text-muted uppercase transition-colors hover:border-line-strong hover:text-ink"
            >
              {theme === "dark" ? "Light" : "Dark"}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-5">
        {turns.length === 0 ? (
          <section className="py-14">
            <p className="label">Start here</p>
            <p className="mt-3 max-w-[46ch] text-[19px] leading-relaxed text-ink-soft">
              Ask anything covered in your seeded notes. Every answer cites the
              chunks it was built from.
            </p>

            <ul className="mt-7 flex flex-col gap-px overflow-hidden rounded-md border border-line bg-line">
              {STARTERS.map((s) => (
                <li key={s}>
                  <button
                    type="button"
                    onClick={() => ask(s)}
                    className="w-full cursor-pointer bg-surface px-4 py-3 text-left text-[14px] text-ink-soft transition-colors hover:bg-surface-2 hover:text-ink"
                  >
                    {s}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ) : (
          <div className="flex flex-col gap-10 py-10">
            {turns.map((turn) => (
              <article key={turn.id} className="rise">
                <p className="label">Question</p>
                <h2 className="mt-2 text-[19px] leading-snug font-medium text-balance text-ink">
                  {turn.question}
                </h2>

                <div className="mt-5 border-l-2 border-line pl-4">
                  {turn.answer ? (
                    <p className="max-w-[68ch] text-[15px] leading-[1.75] whitespace-pre-wrap text-ink-soft">
                      {withCitations(turn.answer)}
                    </p>
                  ) : turn.error ? (
                    <p className="max-w-[68ch] text-[15px] leading-relaxed text-bad">
                      {turn.error}
                    </p>
                  ) : (
                    <p className="label blink">Searching notes…</p>
                  )}

                  {turn.citations && turn.citations.length > 0 && (
                    <div className="mt-5 flex flex-wrap items-center gap-1.5">
                      <span className="label mr-1">Sources</span>
                      {turn.citations.map((c) => (
                        <span
                          key={c}
                          className="rounded-sm border border-line bg-surface px-1.5 py-0.5 font-mono text-[11px] text-muted"
                        >
                          {c}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            ))}
            <div ref={endRef} />
          </div>
        )}
      </main>

      <div className="sticky bottom-0 border-t border-line bg-bg/85 backdrop-blur">
        <form
          className="mx-auto flex w-full max-w-3xl items-end gap-2 px-5 py-3.5"
          onSubmit={(e) => {
            e.preventDefault();
            ask(draft);
          }}
        >
          <textarea
            ref={inputRef}
            rows={1}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                ask(draft);
              }
            }}
            placeholder="Ask about embeddings, chunking, the database…"
            className="max-h-40 flex-1 resize-none rounded-md border border-line bg-surface px-3.5 py-2.5 text-[15px] text-ink placeholder:text-muted focus-visible:border-accent"
          />
          <button
            type="submit"
            disabled={busy || draft.trim().length === 0}
            className="cursor-pointer rounded-md bg-accent px-4 py-2.5 text-[14px] font-medium text-accent-ink transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? "…" : "Ask"}
          </button>
        </form>
      </div>
    </div>
  );
}
