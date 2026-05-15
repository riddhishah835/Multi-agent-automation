import { useState } from 'react';
import PageHeader from '../components/common/PageHeader';
import SeverityBadge from '../components/common/SeverityBadge';
import RiskScorePanel from '../components/common/RiskScorePanel';
import { findings, riskScore } from '../data/mockData';

export default function Findings() {
  const [filter, setFilter] = useState('all');

  const rows = findings.filter((f) => filter === 'all' || f.severity === filter);

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
          <RiskScorePanel data={riskScore} />
        </aside>
      </section>
    </>
  );
}
