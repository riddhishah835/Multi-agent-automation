import { useState } from 'react';
import PageHeader from '../components/common/PageHeader';
import Toggle from '../components/common/Toggle';
import { useToast } from '../context/ToastContext';
import { tenantConfig } from '../data/mockData';

export default function TenantSettings() {
  const { addToast } = useToast();
  const [frameworks, setFrameworks] = useState(tenantConfig.frameworks);
  const [thresholds, setThresholds] = useState(tenantConfig.thresholds);

  const toggleFramework = (id) => {
    setFrameworks((prev) =>
      prev.map((f) => (f.id === id ? { ...f, enabled: !f.enabled } : f))
    );
  };

  return (
    <>
      <PageHeader
        title="Tenant Configuration"
        subtitle="Frameworks, thresholds, controls, and severity mapping"
        actions={
          <button type="button" className="btn btn--primary" onClick={() => addToast('Settings saved', 'success')}>
            Save configuration
          </button>
        }
      />

      <section className="settings-grid">
        <article className="card">
          <h2 className="card__title">Compliance frameworks</h2>
          <ul className="settings-list">
            {frameworks.map((f) => (
              <li key={f.id} className="settings-row">
                <span>{f.name}</span>
                <Toggle on={f.enabled} onChange={() => toggleFramework(f.id)} label={f.name} />
              </li>
            ))}
          </ul>
          <p className="text-muted settings-hint">e.g. ISO, AICPA, Reserve Bank of India</p>
        </article>

        <article className="card">
          <h2 className="card__title">Risk thresholds</h2>
          <div className="form-field">
            <label>Auto-reject above (score)</label>
            <input
              type="number"
              value={thresholds.autoRejectAbove}
              onChange={(e) => setThresholds({ ...thresholds, autoRejectAbove: +e.target.value })}
            />
          </div>
          <section className="form-field">
            <label>HITL required above (score)</label>
            <input
              type="number"
              value={thresholds.hitlRequiredAbove}
              onChange={(e) => setThresholds({ ...thresholds, hitlRequiredAbove: +e.target.value })}
            />
          </section>
          <div className="form-field">
            <label>Max audit duration (days)</label>
            <input
              type="number"
              value={thresholds.maxAuditDays}
              onChange={(e) => setThresholds({ ...thresholds, maxAuditDays: +e.target.value })}
            />
          </div>
        </article>

        <article className="card">
          <h2 className="card__title">Severity mapping</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>Level</th>
                <th>Min score</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {tenantConfig.severityMapping.map((s) => (
                <tr key={s.level}>
                  <td><SeverityLabel level={s.level} /></td>
                  <td>{s.scoreMin}+</td>
                  <td>{s.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="card">
          <h2 className="card__title">Required controls</h2>
          <ul className="controls-list">
            {tenantConfig.requiredControls.map((c) => (
              <li key={c} className="chip">{c}</li>
            ))}
          </ul>
        </article>
      </section>
    </>
  );
}

function SeverityLabel({ level }) {
  return <span className={`severity-badge severity--${level}`}>{level}</span>;
}
