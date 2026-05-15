import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { buildSearchIndex, searchItems } from '../utils/searchIndex';
import { useUploads } from './UploadContext';

const SearchContext = createContext(null);

export function SearchProvider({ children }) {
  const navigate = useNavigate();
  const { uploads } = useUploads();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);

  const index = useMemo(() => buildSearchIndex(uploads), [uploads]);
  const results = useMemo(() => searchItems(index, query), [index, query]);

  const selectResult = useCallback(
    (item) => {
      setQuery('');
      setOpen(false);
      navigate(item.path);
    },
    [navigate]
  );

  const submitSearch = useCallback(() => {
    if (results.length > 0) {
      selectResult(results[0]);
    } else if (query.trim()) {
      navigate(`/history?vendor=${encodeURIComponent(query.trim())}`);
      setQuery('');
      setOpen(false);
    }
  }, [results, query, navigate, selectResult]);

  return (
    <SearchContext.Provider
      value={{
        query,
        setQuery,
        open,
        setOpen,
        results,
        selectResult,
        submitSearch,
      }}
    >
      {children}
    </SearchContext.Provider>
  );
}

export function useSearch() {
  const ctx = useContext(SearchContext);
  if (!ctx) throw new Error('useSearch must be used within SearchProvider');
  return ctx;
}
