import { useEffect, useRef } from 'react';
import { Search } from 'lucide-react';
import { useSearch } from '../../context/SearchContext';

export default function GlobalSearch() {
  const { query, setQuery, open, setOpen, results, selectResult, submitSearch } = useSearch();
  const wrapRef = useRef(null);

  useEffect(() => {
    const onDocClick = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [setOpen]);

  return (
    <section className="global-search" ref={wrapRef}>
      <label className="top-nav__search">
        <Search size={16} />
        <input
          type="search"
          placeholder="Search vendors, audits, findings…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              submitSearch();
            }
            if (e.key === 'Escape') {
              setOpen(false);
              setQuery('');
            }
          }}
          aria-label="Global search"
          aria-expanded={open && results.length > 0}
          aria-controls="search-results"
        />
      </label>

      {open && query.trim() && (
        <ul id="search-results" className="search-results" role="listbox">
          {results.length === 0 ? (
            <li className="search-results__empty">No matches — press Enter to search history</li>
          ) : (
            results.map((item) => (
              <li key={item.id} role="option">
                <button
                  type="button"
                  className="search-results__item"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => selectResult(item)}
                >
                  <span className="search-results__type">{item.type}</span>
                  <strong>{item.label}</strong>
                  {item.subtitle && <span className="search-results__sub">{item.subtitle}</span>}
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </section>
  );
}
