import PageHeader from '../components/common/PageHeader';
import Sparkline from '../components/common/Sparkline';
import { systemHealth } from '../data/mockData';

export default function Observability() {
  const h = systemHealth;

  return (
    <>
      <PageHeader
        title="System Health"
        subtitle="Agent latency, failures, token usage, and cache performance"
      />

      <section className="kpi-grid kpi-grid--health">
        <article className="kpi-card">
          <span className="kpi-card__value">{h.readerLatencySec}s</span>
          <span className="kpi-card__label">Reader latency</span>
        </article>
        <article className="kpi-card">
          <span className="kpi-card__value">{h.judgeLatencySec}s</span>
          <span className="kpi-card__label">Judge latency</span>
        </article>
        <article className="kpi-card kpi-card--accent">
          <span className="kpi-card__value">{h.qdrantHitRate}%</span>
          <span className="kpi-card__label">Qdrant hit rate</span>
        </article>
        <article className="kpi-card">
          <span className="kpi-card__value">{h.cacheHitRate}%</span>
          <span className="kpi-card__label">Cache hit rate</span>
        </article>
        <article className="kpi-card kpi-card--danger">
          <span className="kpi-card__value">{h.failedRuns24h}</span>
          <span className="kpi-card__label">Failed runs (24h)</span>
        </article>
        <article className="kpi-card">
          <span className="kpi-card__value">{h.tokenUsage24h}</span>
          <span className="kpi-card__label">Token usage (24h)</span>
        </article>
      </section>

      <section className="dashboard-split">
        <article className="card">
          <h2 className="card__title">Agent performance</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Latency</th>
                <th>Runs (24h)</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {h.agentRuns.map((a) => (
                <tr key={a.agent}>
                  <td><strong>{a.agent}</strong></td>
                  <td>{a.latency}</td>
                  <td>{a.runs}</td>
                  <td>
                    <span className={`health-dot health-dot--${a.status}`}>{a.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="card">
          <h2 className="card__title">API &amp; infrastructure</h2>
          <ul className="health-list">
            <li>
              <span>API failures (24h)</span>
              <strong className="text-danger">{h.apiFailures24h}</strong>
            </li>
            <li>
              <span>Gap analysis latency</span>
              <strong>{h.gapAnalysisLatencySec}s</strong>
            </li>
            <li>
              <span>Vector retrieval trend</span>
              <Sparkline data={[65, 70, 68, 73, 71, 74, h.qdrantHitRate]} />
            </li>
          </ul>
        </article>
      </section>
    </>
  );
}
