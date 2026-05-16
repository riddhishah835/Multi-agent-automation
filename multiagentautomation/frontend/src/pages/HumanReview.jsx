import { useState, useEffect } from 'react';
import PageHeader from '../components/common/PageHeader';
import SeverityBadge from '../components/common/SeverityBadge';
import PipelineTimeline from '../components/common/PipelineTimeline';
import { useToast } from '../context/ToastContext';
import { pipelineSteps } from '../data/mockData';
import { sendHITLDecision, getAuditState } from '../api/client';

export default function HumanReview() {
  const { addToast } = useToast();
  const [selected, setSelected] = useState(null);
  const [comment, setComment] = useState('');

  useEffect(() => {
    const auditId = localStorage.getItem('current_audit_id');
    if (!auditId) return;

    const fetchState = async () => {
      try {
        const state = await getAuditState(auditId);
        if (state && state.status === 'hitl_paused') {
          setSelected({
            id: auditId,
            vendor: state.vendor_name || 'Unknown Vendor',
            riskScore: state.risk_score || 0,
            aiRecommendation: 'review',
            summary: 'AI has flagged this audit for manual review due to compliance concerns.',
            submittedAt: new Date().toLocaleDateString()
          });
        } else {
          setSelected(null);
        }
      } catch (err) {
        // Silently fail or log, user might not have a pending audit
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 2000);
    return () => clearInterval(interval);
  }, []);

  const act = async (action) => {
    if (action === 'more docs requested') {
      addToast(`${selected.vendor}: ${action}`, 'success');
      return;
    }
    try {
      const auditId = selected.id;
      await sendHITLDecision(auditId, action);
      addToast(`${selected.vendor}: ${action}`, action === 'rejected' ? 'error' : 'success');
      setSelected(null); // Clear from list after decision
    } catch (err) {
      addToast('Backend disconnected - using demo mode', 'error');
    }
  };

  return (
    <>
      <PageHeader
        title="Human Review (HITL)"
        subtitle="Audits waiting for compliance analyst approval"
      />

      <section className="review-layout">
        <article className="card review-queue">
          <h2 className="card__title">Pending approvals ({selected ? 1 : 0})</h2>
          <ul className="review-list">
            {selected && (
              <li key={selected.id}>
                <button
                  type="button"
                  className="review-card review-card--active"
                  onClick={() => {}}
                >
                  <strong>{selected.vendor}</strong>
                  <span className="text-muted">{selected.id}</span>
                  <span className="review-card__risk">Risk: {selected.riskScore}/100</span>
                  <SeverityBadge level={selected.aiRecommendation === 'reject' ? 'high' : selected.aiRecommendation === 'approve' ? 'low' : 'medium'} />
                </button>
              </li>
            )}
            {!selected && (
              <li className="empty-state">No audits currently waiting for human review.</li>
            )}
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
