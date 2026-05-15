import { useState } from 'react';
import { FileText, Link2 } from 'lucide-react';
import PageHeader from '../components/common/PageHeader';
import { evidenceItems } from '../data/mockData';

export default function EvidenceViewer() {
  const [selected, setSelected] = useState(evidenceItems[0]);

  return (
    <>
      <PageHeader
        title="Evidence Viewer"
        subtitle="Verify why the AI flagged each finding — source, page, and quote"
      />

      <section className="evidence-layout">
        <article className="card evidence-list">
          <h2 className="card__title">Evidence items ({evidenceItems.length})</h2>
          <ul>
            {evidenceItems.map((e) => (
              <li key={e.id}>
                <button
                  type="button"
                  className={`evidence-item${selected?.id === e.id ? ' evidence-item--active' : ''}`}
                  onClick={() => setSelected(e)}
                >
                  <span className="evidence-item__cat">{e.category}</span>
                  <span className="evidence-item__preview">{e.quote.slice(0, 60)}…</span>
                </button>
              </li>
            ))}
          </ul>
        </article>

        {selected && (
          <article className="card evidence-detail">
            <header className="evidence-detail__header">
              <FileText size={22} color="var(--accent)" />
              <span>Finding {selected.findingId}</span>
            </header>
            <blockquote className="evidence-quote">"{selected.quote}"</blockquote>
            <dl className="evidence-meta">
              <div>
                <dt>Page</dt>
                <dd>Page {selected.page}</dd>
              </div>
              <div>
                <dt>Source</dt>
                <dd><code>{selected.source}</code></dd>
              </div>
              <div>
                <dt>Category</dt>
                <dd>{selected.category}</dd>
              </div>
            </dl>
            <button type="button" className="btn btn--ghost">
              <Link2 size={14} /> Open in findings dashboard
            </button>
          </article>
        )}
      </section>
    </>
  );
}
