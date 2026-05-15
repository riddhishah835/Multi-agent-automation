import { createContext, useCallback, useContext, useState } from 'react';
import { liveLogs as seedLogs } from '../data/mockData';

const LogsContext = createContext(null);

function ts() {
  return new Date().toTimeString().slice(0, 8);
}

export function LogsProvider({ children }) {
  const [logs, setLogs] = useState(seedLogs);

  const appendLog = useCallback((message) => {
    const line = `[${ts()}] ${message}`;
    setLogs((prev) => [...prev.slice(-49), line]);
    return line;
  }, []);

  return (
    <LogsContext.Provider value={{ logs, appendLog }}>
      {children}
    </LogsContext.Provider>
  );
}

export function useLogs() {
  const ctx = useContext(LogsContext);
  if (!ctx) throw new Error('useLogs must be used within LogsProvider');
  return ctx;
}
