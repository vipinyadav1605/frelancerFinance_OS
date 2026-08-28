import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { globalSearch } from "../api/endpoints";
import type { SearchResult } from "../types";

const DEBOUNCE_MS = 250;

export function GlobalSearch() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    const timer = setTimeout(() => {
      globalSearch(query.trim()).then((data) => { setResults(data); setOpen(true); }).catch(() => {});
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSelect(result: SearchResult) {
    setOpen(false);
    setQuery("");
    navigate(result.link_path);
  }

  return (
    <div className="navbar-search" ref={containerRef}>
      <input
        type="search"
        placeholder="Search invoices, clients..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => { if (results.length > 0) setOpen(true); }}
      />
      {open && (
        <div className="notification-dropdown" style={{ left: 0, right: "auto" }}>
          {results.length === 0 ? (
            <div className="notification-empty">No matches.</div>
          ) : (
            results.map((r, i) => (
              <button key={`${r.type}-${i}`} className="notification-item" onClick={() => handleSelect(r)}>
                <span className={`badge ${r.type === "invoice" ? "badge-blue" : "badge-grey"}`} style={{ marginRight: "0.5rem" }}>
                  {r.type}
                </span>
                {r.label}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
