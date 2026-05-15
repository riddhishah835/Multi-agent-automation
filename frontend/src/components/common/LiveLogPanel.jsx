import { useState } from 'react';
import { Terminal } from 'lucide-react';
import { liveLogs } from '../../data/mockData';

export default function LiveLogPanel() {
  const [open, setOpen] = useState(false);

  return (
    <aside className={`live-log-panel${open ? ' live-log-panel--open' : ''}`}>
      <header
        className="live-log-panel__header"
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => e.key === 'Enter' && setOpen((o) => !o)}
        role="button"
        tabIndex={0}
      >
        <span>
          <Terminal size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />
          Live agent logs
        </span>
        <span>{open ? '▼' : '▲'}</span>
      </header>
      {open && (
        <div className="live-log-panel__body">
          {liveLogs.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      )}
    </aside>
  );
}
