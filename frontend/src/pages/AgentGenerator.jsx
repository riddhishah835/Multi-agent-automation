import { useState } from 'react';
import { Info } from 'lucide-react';
import { agentConfig } from '../data/mockData';
import { useToast } from '../context/ToastContext';
import Toggle from '../components/common/Toggle';
import JsonEditor from '../components/common/JsonEditor';

export default function AgentGenerator() {
  const { addToast } = useToast();
  const [section, setSection] = useState(agentConfig.activeSection);
  const [model, setModel] = useState(agentConfig.model);
  const [tone, setTone] = useState(agentConfig.tone);
  const [strictTop, setStrictTop] = useState(agentConfig.strictJsonTop);
  const [strictBottom, setStrictBottom] = useState(agentConfig.strictJsonBottom);
  const [tools, setTools] = useState(agentConfig.tools);
  const [schema, setSchema] = useState(agentConfig.schema);

  const removeTool = (name) => setTools((t) => t.filter((x) => x !== name));

  const exportConfig = () => {
    const blob = new Blob(
      [JSON.stringify({ model, tone, strictTop, strictBottom, tools, schema }, null, 2)],
      { type: 'application/json' }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'agent-config.json';
    a.click();
    URL.revokeObjectURL(url);
    addToast('Configuration exported', 'success');
  };

  return (
    <>
      <header className="page-header">
        <h1>Agent Generator</h1>
        <select className="select-pill">Tenant context: ACME</select>
      </header>

      <section className="agent-layout">
        <nav className="agent-nav" aria-label="Config sections">
          {agentConfig.sections.map((s) => (
            <button
              key={s}
              type="button"
              className={`agent-nav__item${section === s ? ' agent-nav__item--active' : ''}`}
              onClick={() => setSection(s)}
            >
              {s}
            </button>
          ))}
        </nav>

        <section className="agent-panel">
          <header className="config-header">
            <section>
              <h2 style={{ fontSize: '1rem' }}>Parameterized templates — {section}</h2>
              <span style={{ color: 'var(--accent)', fontSize: '0.8rem' }}>Version {agentConfig.version}</span>
            </section>
            <section style={{ display: 'flex', gap: '0.5rem' }}>
              <button type="button" className="btn btn--ghost" onClick={exportConfig}>
                Export JSON
              </button>
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => addToast('Config saved & flows reloaded', 'success')}
              >
                Save config &amp; reload flows
              </button>
            </section>
          </header>

          <section className="config-grid">
            <section className="form-field">
              <label htmlFor="model">Model</label>
              <select id="model" value={model} onChange={(e) => setModel(e.target.value)}>
                <option>GPT-4</option>
                <option>GPT-4o</option>
                <option>Claude 3.5 Sonnet</option>
              </select>
            </section>

            <section className="form-field">
              <section className="form-row">
                <label>
                  Output format <Info size={12} style={{ verticalAlign: 'middle' }} />
                </label>
                <Toggle on={strictTop} onChange={setStrictTop} label="Strict JSON schema top" />
              </section>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Strict JSON Schema</span>
            </section>

            <section className="form-field">
              <label htmlFor="tone">Tone — Formal ↔ Casual ({tone.toFixed(2)})</label>
              <input
                id="tone"
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={tone}
                onChange={(e) => setTone(Number(e.target.value))}
              />
            </section>

            <section className="form-field">
              <section className="form-row">
                <label>Output format</label>
                <Toggle on={strictBottom} onChange={setStrictBottom} label="Strict JSON schema bottom" />
              </section>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Strict JSON Schema</span>
            </section>
          </section>

          <section className="form-field" style={{ marginBottom: '1rem' }}>
            <label>Allowed tools</label>
            <section className="tools-grid">
              {tools.map((t) => (
                <span key={t} className="chip">
                  {t}
                  <button type="button" onClick={() => removeTool(t)} aria-label={`Remove ${t}`}>
                    ×
                  </button>
                </span>
              ))}
            </section>
            <button
              type="button"
              className="btn btn--text"
              style={{ marginTop: '0.35rem', color: 'var(--accent)' }}
              onClick={() => setTools((prev) => [...prev, `Tool_${prev.length + 1}`])}
            >
              + Connect tool
            </button>
          </section>

          <details open>
            <summary className="card__title" style={{ cursor: 'pointer', marginBottom: '0.5rem' }}>
              JSON Schema
            </summary>
            <JsonEditor value={schema} onChange={setSchema} />
          </details>
        </section>
      </section>
    </>
  );
}
