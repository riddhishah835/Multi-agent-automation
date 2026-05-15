import { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import PageHeader from '../components/common/PageHeader';
import SeverityBadge from '../components/common/SeverityBadge';
import StatusBadge from '../components/common/StatusBadge';
import { getHistory } from '../api/client';
import { auditHistory } from '../data/mockData';

export default function AuditHistory() {
  const [params] = useSearchParams();
  const [vendor, setVendor] = useState('');
  const [risk, setRisk] = useState('all');
  const [framework, setFramework] = useState('all');
  const [historyData, setHistoryData] = useState(auditHistory);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const data = await getHistory();
        if (data && data.length > 0) {
          setHistoryData(data);
        }
      } catch (err) {
        console.error('Error fetching history:', err);
      }
    };
    fetchHistory();
    // Poll every 5 seconds for updates
    const interval = setInterval(fetchHistory, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const q = params.get('vendor');
    if (q) setVendor(q);
  }, [params]);

  const filtered = useMemo(() => {
    return historyData.filter((a) => {
      if (vendor && !a.vendor.toLowerCase().includes(vendor.toLowerCase())) return false;
      if (risk !== 'all' && a.risk !== risk) return false;
      if (framework !== 'all' && !a.framework.toLowerCase().includes(framework.toLowerCase())) return false;
      return true;
    });
  }, [vendor, risk, framework, historyData]);

  return (
    <>
      <PageHeader
        title="Audit History"
        subtitle="Search past audits by vendor, date, risk level, and framework"
      />

      <article className="card filters-bar">
        <label className="search-inline">
          <Search size={16} />
          <input
            type="search"
            placeholder="Search vendor…"
            value={vendor}
            onChange={(e) => setVendor(e.target.value)}
          />
        </label>
        <select className="select-pill" value={risk} onChange={(e) => setRisk(e.target.value)}>
          <option value="all">All risk levels</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select className="select-pill" value={framework} onChange={(e) => setFramework(e.target.value)}>
          <option value="all">All frameworks</option>
          <option value="SOC2">SOC2</option>
          <option value="ISO">ISO</option>
          <option value="RBI">RBI</option>
          <option value="GDPR">GDPR</option>
          <option value="AICPA">AICPA</option>
        </select>
      </article>

      <article className="card" style={{ marginTop: '1rem' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Audit ID</th>
              <th>Vendor</th>
              <th>Date</th>
              <th>Risk</th>
              <th>Framework</th>
              <th>Outcome</th>
              <th>Analyst</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((a) => (
              <tr key={a.id}>
                <td><code className="code-id">{a.id}</code></td>
                <td><strong>{a.vendor}</strong></td>
                <td>{a.date}</td>
                <td><SeverityBadge level={a.risk} /></td>
                <td>{a.framework}</td>
                <td><StatusBadge status={a.outcome} /></td>
                <td>{a.analyst}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="empty-state">No audits match your filters.</p>
        )}
      </article>
    </>
  );
}
