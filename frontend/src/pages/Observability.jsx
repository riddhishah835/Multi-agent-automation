import { useState } from 'react';
import { AlertTriangle, ArrowLeft, Bug } from 'lucide-react';
import { traceRun } from '../data/mockData';
import { useToast } from '../context/ToastContext';
import ExecutionFlow from '../components/observability/ExecutionFlow';
import JsonEditor from '../components/common/JsonEditor';
import Sparkline from '../components/common/Sparkline';

export default function Observability() {
  const { addToast } = useToast();
  const [activeEvent, setActiveEvent] = useState(3);
  const [tab, setTab] = useState('events');
  const [filter, setFilter] = useState('all');
  const trace = traceRun;

  const filteredEvents = trace.events.filter((e) => {
    if (filter === 'errors') return e.label.toLowerCase().includes('pause');
    if (filter === 'success') return !e.label.toLowerCase().includes('pause');
    return true;
  });

  return (
    <>
      <header className="page-header">
        <h1>Execution Trace</h1>
        <section style={{ display: 'flex', gap: '0.5rem' }}>
          <button type="button" className="btn btn--ghost">Trace</button>
          <button type="button" className="btn btn--ghost">
            <ArrowLeft size={14} /> Back
          </button>
          <button type="button" className="btn btn--primary" onClick={() => addToast('Debug log streaming…', 'info')}>
            <Bug size={14} /> Debug log
          </button>
        </section>
      </header>

      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        ← {trace.name}, ID: {trace.id}
        <input
          type="search"
          placeholder="Find workflow"
          style={{
            marginLeft: '1rem',
            padding: '0.35rem 0.75rem',
            borderRadius: 999,
            border: '1px solid var(--border)',
            background: 'var(--bg-card)',
          }}
        />
      </p>

      <section className="obs-grid">
        <article className="card obs-graph">
          <ExecutionFlow />
        </article>

        <aside className="obs-side">
          <article className="card">
            <section className="tabs">
              <button
                type="button"
                className={`tab${tab === 'events' ? ' tab--active' : ''}`}
                onClick={() => setTab('events')}
              >
                Event log
              </button>
              <button
                type="button"
                className={`tab${tab === 'state' ? ' tab--active' : ''}`}
                onClick={() => setTab('state')}
              >
                State
              </button>
            </section>
            {tab === 'events' && (
              <>
                <select
                  className="select-pill"
                  style={{ marginBottom: '0.5rem', width: '100%' }}
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="all">All events</option>
                  <option value="errors">Warnings / pauses</option>
                  <option value="success">Success</option>
                </select>
                <ul className="event-log">
                  {filteredEvents.map((ev) => (
                    <li
                      key={ev.id}
                      className={activeEvent === ev.id ? 'event-log__item--active' : ''}
                      onClick={() => setActiveEvent(ev.id)}
                    >
                      [{ev.time}] {ev.label}
                    </li>
                  ))}
                </ul>
              </>
            )}
            {tab === 'state' && (
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Checkpoint state: waiting on policy_checker HITL gate.
              </p>
            )}
          </article>

          <article className="card">
            <p className="card__title">Strict JSON Schema Contracts</p>
            <JsonEditor value={trace.schema} readOnly />
          </article>
        </aside>
      </section>

      <section className="obs-bottom" style={{ marginTop: '1rem' }}>
        <article className="card">
          <header style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <p className="card__title" style={{ margin: 0 }}>
              Layer 6: 3-Tier Memory &amp; Governance Checkpoints
            </p>
            <button type="button" className="btn btn--ghost">Schedule runs</button>
          </header>
          <table className="checkpoint-table">
            <thead>
              <tr>
                <th>Check</th>
                <th>Time series</th>
                <th>Hit</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {trace.checkpoints.map((row) => (
                <tr key={row.check}>
                  <td>{row.check}</td>
                  <td>
                    <Sparkline data={row.series} />
                  </td>
                  <td>{row.hit}</td>
                  <td style={{ color: row.status === 'miss' ? 'var(--danger)' : 'var(--success)' }}>
                    {row.status === 'miss' ? 'Miss' : 'Hit'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="alert-box">
          <AlertTriangle color="var(--warning)" size={22} />
          <section>
            <strong style={{ display: 'block', marginBottom: '0.35rem' }}>Alert status</strong>
            <p>{trace.alert}</p>
          </section>
        </article>
      </section>
    </>
  );
}
