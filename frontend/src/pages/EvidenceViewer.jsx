import { useState, useEffect } from 'react';
import { FileText, Link2 } from 'lucide-react';
import PageHeader from '../components/common/PageHeader';
import { getAuditState } from '../api/client';
import { useToast } from '../context/ToastContext';

export default function EvidenceViewer() {
  const { addToast } = useToast();
  const [evidenceItems, setEvidenceItems] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    const auditId = localStorage.getItem('current_audit_id');
    let errorToastShown = false;

    if (!auditId) return;

    const fetchState = async () => {
      try {
        const state = await getAuditState(auditId);
        if (state && state.findings) {
          const mapped = state.findings.map((f, i) => ({
            id: f.finding_id || `ev-${i}`,
            findingId: f.finding_id || `F-${i+1}`,
            category: f.issue || 'Compliance Issue',
            quote: f.evidence || 'No evidence provided.',
            page: f.page_reference || 'N/A',
            source: (f.frameworks || []).join(', ') || 'Framework'
          }));
          setEvidenceItems(mapped);
          
          if (mapped.length > 0 && (!selected || !mapped.find(m => m.id === selected?.id))) {
            setSelected(mapped[0]);
          }
        }
      } catch (err) {
        if (!errorToastShown) {
          addToast('Backend disconnected - showing empty evidence', 'error');
          errorToastShown = true;
        }
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 2000);
    return () => clearInterval(interval);
  }, [addToast, selected?.id]);

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
            {evidenceItems.length === 0 && (
              <li className="empty-state" style={{ padding: '1rem', color: 'var(--text-muted)' }}>
                No evidence items available.
              </li>
            )}
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
                <dd>{selected.page}</dd>
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
