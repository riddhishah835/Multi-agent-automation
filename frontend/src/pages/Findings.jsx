import { useState, useEffect } from 'react';
import PageHeader from '../components/common/PageHeader';
import SeverityBadge from '../components/common/SeverityBadge';
import RiskScorePanel from '../components/common/RiskScorePanel';
import { getAuditState } from '../api/client';
import { useToast } from '../context/ToastContext';

export default function Findings() {
  const { addToast } = useToast();
  const [filter, setFilter] = useState('all');
  const [realTimeState, setRealTimeState] = useState(null);

  useEffect(() => {
    const auditId = localStorage.getItem('current_audit_id');
    let errorToastShown = false;

    if (!auditId) return;

    const fetchState = async () => {
      try {
        const state = await getAuditState(auditId);
        if (state) setRealTimeState(state);
      } catch (err) {
        if (!errorToastShown) {
          addToast('Backend disconnected - using demo mode', 'error');
          errorToastShown = true;
        }
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 2000);
    return () => clearInterval(interval);
  }, [addToast]);

  const currentFindings = realTimeState?.findings || [];
  const currentRiskScore = realTimeState?.risk_score !== undefined 
    ? { 
        overall: realTimeState.risk_score, 
        compliance: Math.max(0, 100 - realTimeState.risk_score), 
        recommendation: realTimeState.risk_score > 70 ? 'Reject (High Risk)' : 'Approve (Low Risk)'
      } 
    : { overall: 0, compliance: 100, recommendation: 'Pending' };

  const rows = currentFindings.filter((f) => filter === 'all' || f.severity === filter);

  return (
    <>
      <PageHeader
        title="Findings Dashboard"
        subtitle="All compliance risks identified across the current audit"
        actions={
          <select className="select-pill" value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">All severities</option>
            <option value="high">High only</option>
            <option value="medium">Medium only</option>
            <option value="low">Low only</option>
          </select>
        }
      />

      <section className="findings-layout">
        <article className="card findings-table-wrap">
          <table className="data-table data-table--findings">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Category</th>
                <th>Finding</th>
                <th>Framework</th>
                <th>Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((f) => (
                <tr key={f.id}>
                  <td><SeverityBadge level={f.severity} /></td>
                  <td>{f.category}</td>
                  <td><strong>{f.finding}</strong></td>
                  <td><code className="code-id">{f.framework}</code></td>
                  <td className="text-muted">{f.recommendation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <aside>
          <RiskScorePanel data={currentRiskScore} />
        </aside>
      </section>
    </>
  );
}
