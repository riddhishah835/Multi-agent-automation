import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowRight, Clock, FileCheck, Users, XCircle } from 'lucide-react';
import PageHeader from '../components/common/PageHeader';
import StatusBadge from '../components/common/StatusBadge';
import SeverityBadge from '../components/common/SeverityBadge';
import {
  auditQueueStats,
  highRiskVendors,
  recentAudits,
} from '../data/mockData';

const statCards = [
  { key: 'activeAudits', label: 'Active Audits', icon: FileCheck, accent: true },
  { key: 'completedAudits', label: 'Completed Audits', icon: FileCheck },
  { key: 'pendingReviews', label: 'Pending Reviews', icon: Users, warn: true },
  { key: 'failedAudits', label: 'Failed Audits', icon: XCircle, danger: true },
  { key: 'avgAuditTimeMins', label: 'Avg Audit Time', icon: Clock, suffix: ' mins' },
  { key: 'highRiskVendors', label: 'High-Risk Vendors', icon: AlertTriangle, danger: true },
];

import { useState, useEffect } from 'react';
import { getHistory } from '../api/client';

export default function AuditQueue() {
  const stats = auditQueueStats;
  const [recentData, setRecentData] = useState(recentAudits);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const data = await getHistory();
        if (data && data.length > 0) {
          setRecentData(data.slice(0, 5));
        }
      } catch (err) {
        console.error('Error fetching history:', err);
      }
    };
    fetchHistory();
    const interval = setInterval(fetchHistory, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <PageHeader
        title="Audit Queue"
        subtitle="Operational command center for compliance analysts"
        actions={
          <Link to="/upload" className="btn btn--primary">
            Start new audit
          </Link>
        }
      />

      <section className="kpi-grid">
        {statCards.map(({ key, label, icon: Icon, accent, warn, danger, suffix }) => (
          <article
            key={key}
            className={`kpi-card${accent ? ' kpi-card--accent' : ''}${warn ? ' kpi-card--warn' : ''}${danger ? ' kpi-card--danger' : ''}`}
          >
            <Icon size={20} className="kpi-card__icon" />
            <span className="kpi-card__value">
              {stats[key]}
              {suffix || ''}
            </span>
            <span className="kpi-card__label">{label}</span>
          </article>
        ))}
      </section>

      <section className="dashboard-split">
        <article className="card">
          <header className="card__header">
            <h2 className="card__title">High-risk vendors</h2>
            <Link to="/findings" className="link-muted">
              View findings <ArrowRight size={14} />
            </Link>
          </header>
          <table className="data-table">
            <thead>
              <tr>
                <th>Vendor</th>
                <th>Risk</th>
                <th>Framework</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {highRiskVendors.map((v) => (
                <tr key={v.name}>
                  <td><strong>{v.name}</strong></td>
                  <td><span className="text-danger">{v.riskScore}/100</span></td>
                  <td>{v.framework}</td>
                  <td><StatusBadge status={v.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="card">
          <header className="card__header">
            <h2 className="card__title">Recent audits</h2>
            <Link to="/history" className="link-muted">
              Full history <ArrowRight size={14} />
            </Link>
          </header>
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Vendor</th>
                <th>Risk</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {recentData.map((a) => (
                <tr key={a.id}>
                  <td><code className="code-id">{a.id}</code></td>
                  <td>{a.vendor}</td>
                  <td><SeverityBadge level={a.risk} /></td>
                  <td><StatusBadge status={a.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      </section>

      <section className="quick-actions">
        <Link to="/review" className="quick-action card">
          <strong>{stats.pendingReviews} pending reviews</strong>
          <span>Human approval queue →</span>
        </Link>
        <Link to="/pipeline" className="quick-action card">
          <strong>Audit pipeline</strong>
          <span>Track node-by-node progress →</span>
        </Link>
        <Link to="/reports" className="quick-action card">
          <strong>Download reports</strong>
          <span>PDF, CSV, JSON, Markdown →</span>
        </Link>
      </section>
    </>
  );
}
