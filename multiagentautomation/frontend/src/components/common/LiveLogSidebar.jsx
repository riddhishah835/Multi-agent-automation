import { useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';
import { useLogs } from '../../context/LogsContext';

export default function LiveLogSidebar({ collapsed }) {
  const { logs } = useLogs();
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  if (collapsed) {
    return (
      <section className="sidebar-logs sidebar-logs--collapsed" title="Live agent logs">
        <Terminal size={18} />
      </section>
    );
  }

  return (
    <section className="sidebar-logs">
      <header className="sidebar-logs__header">
        <Terminal size={14} />
        <span>Live agent logs</span>
      </header>
      <div className="sidebar-logs__body">
        {logs.map((line, i) => (
          <p key={`${line}-${i}`}>{line}</p>
        ))}
        <span ref={bottomRef} />
      </div>
    </section>
  );
}
