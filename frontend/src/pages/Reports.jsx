import { Download, FileJson, FileSpreadsheet, FileText } from 'lucide-react';
import PageHeader from '../components/common/PageHeader';
import { useToast } from '../context/ToastContext';
import { currentAudit, riskScore } from '../data/mockData';

const formats = [
  { id: 'pdf', label: 'PDF Report', desc: 'Executive summary + findings', icon: FileText },
  { id: 'csv', label: 'CSV Export', desc: 'Findings table for spreadsheets', icon: FileSpreadsheet },
  { id: 'json', label: 'JSON Bundle', desc: 'Full audit artifact for integrations', icon: FileJson },
  { id: 'md', label: 'Markdown', desc: 'Readable report for Confluence/wiki', icon: FileText },
];

export default function Reports() {
  const { addToast } = useToast();

  const download = (fmt) => {
    addToast(`Downloading ${fmt.toUpperCase()} for ${currentAudit.id}`, 'success');
  };

  return (
    <>
      <PageHeader
        title="Final Audit Report"
        subtitle={`${currentAudit.vendor} — ${currentAudit.id}`}
      />

      <article className="card report-summary">
        <section className="report-summary__grid">
          <div>
            <span className="text-muted">Vendor</span>
            <strong>{currentAudit.vendor}</strong>
          </div>
          <div>
            <span className="text-muted">Risk score</span>
            <strong className="text-danger">{riskScore.overall}/100</strong>
          </div>
          <div>
            <span className="text-muted">Recommendation</span>
            <strong>{riskScore.recommendation}</strong>
          </div>
          <div>
            <span className="text-muted">Frameworks</span>
            <strong>{currentAudit.frameworks.join(', ')}</strong>
          </div>
        </section>
      </article>

      <section className="report-formats">
        {formats.map(({ id, label, desc, icon: Icon }) => (
          <article key={id} className="card report-format-card">
            <Icon size={28} color="var(--accent)" />
            <h3>{label}</h3>
            <p className="text-muted">{desc}</p>
            <button type="button" className="btn btn--primary" onClick={() => download(id)}>
              <Download size={14} /> Download
            </button>
          </article>
        ))}
      </section>
    </>
  );
}
