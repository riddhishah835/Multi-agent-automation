import { useState } from 'react';
import { Check, Sparkles } from 'lucide-react';
import { workflowRun, auditTrail } from '../data/mockData';
import { useToast } from '../context/ToastContext';
import ConfidenceRing from '../components/common/ConfidenceRing';

export default function WorkflowHitl() {
  const { addToast } = useToast();
  const [comment, setComment] = useState('');
  const [decision, setDecision] = useState(workflowRun.humanDecision);
  const run = workflowRun;

  const handleDecision = (action) => {
    setDecision(action);
    addToast(`Workflow ${run.id}: ${action}`, action === 'rejected' ? 'error' : 'success');
  };

  return (
    <>
      <header className="page-header">
        <h1>
          Workflow: {run.name} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(ID: {run.id})</span>
        </h1>
        <div className="page-header__meta">
          <select className="select-pill">Tenant: {run.tenant}</select>
          <select className="select-pill">User: {run.user}</select>
        </div>
      </header>

      <div className="workflow-grid">
        <article className="card">
          <p className="card__title">Current node</p>
          <p style={{ fontSize: '0.9rem', marginBottom: '1rem' }}>{run.currentNode}</p>
          <ul className="timeline">
            {run.steps.map((step) => (
              <li
                key={step.id}
                className={`timeline__item${step.active ? ' timeline__item--active' : ''}`}
              >
                <span className={`timeline__icon timeline__icon--${step.status === 'complete' || step.status === 'flags_found' ? 'done' : ''}`}>
                  {(step.status === 'complete' || step.status === 'flags_found') && <Check size={14} />}
                </span>
                <div>
                  <strong style={{ fontSize: '0.85rem' }}>{step.name}</strong>
                  <br />
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {step.status === 'complete' && 'Complete'}
                    {step.status === 'flags_found' && 'Flags found'}
                    {step.status === 'pending' && 'Pending'}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <p className="card__title">Decision point</p>
          <div className="decision-grid">
            <section className="decision-panel">
              <h3>
                AI recommendation{' '}
                <span className="badge badge--danger">({run.aiRecommendation.decision})</span>
              </h3>
              <ConfidenceRing value={run.aiRecommendation.confidence} />
              <ul style={{ marginTop: '0.75rem' }}>
                {run.aiRecommendation.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </section>
            <section className="decision-panel">
              <h3>
                Human decision{' '}
                <span className="badge badge--warning">({decision})</span>
              </h3>
              <div className="decision-actions">
                <button type="button" className="btn btn--primary" onClick={() => handleDecision('approved')}>
                  Approve &amp; resume flow
                </button>
                <button type="button" className="btn btn--primary" onClick={() => handleDecision('rejected')}>
                  Reject &amp; terminate
                </button>
                <button type="button" className="btn btn--ghost" onClick={() => handleDecision('more_data')}>
                  Request more data
                </button>
              </div>
            </section>
          </div>
        </article>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: '1rem', marginTop: '1rem' }}>
        <article className="card comment-area">
          <p className="card__title">Comment</p>
          <textarea
            placeholder="Add comment for governance…"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <footer className="comment-footer">
            <button type="button" className="btn btn--text">Cancel</button>
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => addToast('Comment saved to audit log', 'success')}
            >
              <Sparkles size={14} /> Approve
            </button>
          </footer>
        </article>

        <article className="card">
          <p className="card__title">Audit trail</p>
          <ul className="audit-list">
            {auditTrail.map((e) => (
              <li key={`${e.time}-${e.action}`}>
                <span>{e.time}</span>
                <span>{e.action}</span>
                <span>{e.actor}</span>
              </li>
            ))}
          </ul>
        </article>
      </div>
    </>
  );
}
