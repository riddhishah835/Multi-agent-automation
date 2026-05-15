import { useState } from 'react';
import PageHeader from '../components/common/PageHeader';
import SeverityBadge from '../components/common/SeverityBadge';
import PipelineTimeline from '../components/common/PipelineTimeline';
import { useToast } from '../context/ToastContext';
import { pendingApprovals, pipelineSteps } from '../data/mockData';

export default function HumanReview() {
  const { addToast } = useToast();
  const [selected, setSelected] = useState(pendingApprovals[0]);
  const [comment, setComment] = useState('');

  const act = (action) => {
    addToast(`${selected.vendor}: ${action}`, action === 'rejected' ? 'error' : 'success');
  };

  return (
    <>
      <PageHeader
        title="Human Review (HITL)"
        subtitle="Audits waiting for compliance analyst approval"
      />

      <section className="review-layout">
        <article className="card review-queue">
          <h2 className="card__title">Pending approvals ({pendingApprovals.length})</h2>
          <ul className="review-list">
            {pendingApprovals.map((a) => (
              <li key={a.id}>
                <button
                  type="button"
                  className={`review-card${selected?.id === a.id ? ' review-card--active' : ''}`}
                  onClick={() => setSelected(a)}
                >
                  <strong>{a.vendor}</strong>
                  <span className="text-muted">{a.id}</span>
                  <span className="review-card__risk">Risk: {a.riskScore}/100</span>
                  <SeverityBadge level={a.aiRecommendation === 'reject' ? 'high' : a.aiRecommendation === 'approve' ? 'low' : 'medium'} />
                </button>
              </li>
            ))}
          </ul>
        </article>

        {selected && (
          <article className="card review-detail">
            <header className="review-detail__header">
              <section>
                <h2>Vendor: {selected.vendor}</h2>
                <p className="text-muted">Status: Waiting Approval · {selected.submittedAt}</p>
              </section>
              <span className="review-ai-rec">AI: {selected.aiRecommendation}</span>
            </header>

            <p>{selected.summary}</p>

            <h3 className="card__title" style={{ marginTop: '1rem' }}>Pipeline status</h3>
            <PipelineTimeline steps={pipelineSteps} compact />

            <section className="review-actions">
              <button type="button" className="btn btn--primary" onClick={() => act('approved')}>
                Approve vendor
              </button>
              <button type="button" className="btn btn--primary" onClick={() => act('rejected')}>
                Reject vendor
              </button>
              <button type="button" className="btn btn--ghost" onClick={() => act('more docs requested')}>
                Request more documents
              </button>
            </section>

            <label className="comment-field">
              <span className="card__title">Governance comment</span>
              <textarea
                placeholder="Add comment for audit trail…"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
            </label>
          </article>
        )}
      </section>
    </>
  );
}
