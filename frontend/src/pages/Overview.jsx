import { useNavigate } from 'react-router-dom';
import { ArrowRight, GitBranch, Eye, Network } from 'lucide-react';
import { overviewStats } from '../data/mockData';

const links = [
  { title: 'Agent Generator', desc: 'Configure models, tools, and JSON schemas', path: '/agents', icon: Network },
  { title: 'Workflow HITL', desc: 'Review AI recommendations and approve steps', path: '/workflows', icon: GitBranch },
  { title: 'Execution Trace', desc: 'DAG visualization, event logs, governance', path: '/observability', icon: Eye },
];

export default function Overview() {
  const navigate = useNavigate();

  return (
    <>
      <header className="page-header">
        <h1>Overview</h1>
        <select className="select-pill" defaultValue="ACME">
          <option>Tenant: ACME</option>
        </select>
      </header>

      <section className="stats-grid">
        {overviewStats.map((s) => (
          <article key={s.label} className="card stat-card">
            <p className="card__title">{s.label}</p>
            <p className="stat-card__value">{s.value}</p>
            <p className="stat-card__delta">{s.delta} vs last week</p>
          </article>
        ))}
      </section>

      <h2 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Quick access</h2>
      <section className="quick-links">
        {links.map(({ title, desc, path, icon: Icon }) => (
          <article
            key={path}
            className="card quick-link"
            onClick={() => navigate(path)}
            onKeyDown={(e) => e.key === 'Enter' && navigate(path)}
            role="button"
            tabIndex={0}
          >
            <Icon size={24} color="var(--accent)" style={{ marginBottom: '0.5rem' }} />
            <h3 style={{ fontSize: '0.95rem', marginBottom: '0.35rem' }}>{title}</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{desc}</p>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: '0.75rem', color: 'var(--accent)', fontSize: '0.8rem' }}>
              Open <ArrowRight size={14} />
            </span>
          </article>
        ))}
      </section>
    </>
  );
}
