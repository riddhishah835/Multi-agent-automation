import { Plug, Shield, Database, Globe } from 'lucide-react';

const tools = [
  { name: 'CRM_MCP', desc: 'Customer records & deal pipeline via MCP bridge', icon: Database },
  { name: 'Policy_v3', desc: 'Governance policy engine with semantic rules', icon: Shield },
  { name: 'WebSearch', desc: 'Grounded web retrieval for research agents', icon: Globe },
  { name: 'DocParser', desc: 'PDF/Office extraction with layout awareness', icon: Plug },
];

export default function ToolsPage() {
  return (
    <>
      <header className="page-header">
        <h1>Tools</h1>
        <button type="button" className="btn btn--primary">
          Register MCP tool
        </button>
      </header>

      <section className="tools-page-grid">
        {tools.map(({ name, desc, icon: Icon }) => (
          <article key={name} className="card tool-card">
            <Icon size={22} color="var(--accent)" style={{ marginBottom: '0.5rem' }} />
            <h3>{name}</h3>
            <p>{desc}</p>
            <button type="button" className="btn btn--ghost" style={{ marginTop: '0.75rem' }}>
              Configure
            </button>
          </article>
        ))}
      </section>
    </>
  );
}
