import PageHeader from '../components/common/PageHeader';
import PipelineTimeline from '../components/common/PipelineTimeline';
import RiskScorePanel from '../components/common/RiskScorePanel';
import { currentAudit, pipelineSteps, riskScore } from '../data/mockData';

export default function AuditPipeline() {
  return (
    <>
      <PageHeader
        title="Audit Pipeline"
        subtitle={`Workflow progress — ${currentAudit.vendor} (${currentAudit.id})`}
        actions={
          <select className="select-pill" defaultValue={currentAudit.id}>
            <option value={currentAudit.id}>{currentAudit.id} — {currentAudit.vendor}</option>
            <option>AUD-2398 — SecureHost Inc</option>
          </select>
        }
      />

      <section className="pipeline-layout">
        <article className="card pipeline-card">
          <h2 className="card__title">Node-by-node progress</h2>
          <p className="text-muted" style={{ marginBottom: '1.25rem' }}>
            Frameworks: {currentAudit.frameworks.join(', ')}
          </p>
          <PipelineTimeline steps={pipelineSteps} />
          <section className="pipeline-legend">
            <span><span className="dot dot--done" /> Complete</span>
            <span><span className="dot dot--pause" /> Waiting approval</span>
            <span><span className="dot dot--pending" /> Pending</span>
          </section>
        </article>

        <aside>
          <RiskScorePanel data={riskScore} />
          <article className="card" style={{ marginTop: '1rem' }}>
            <h2 className="card__title">Current step</h2>
            <p className="pipeline-current">Waiting Human Approval</p>
            <p className="text-muted">
              Judge and gap analysis completed. Analyst review required before final report generation.
            </p>
          </article>
        </aside>
      </section>
    </>
  );
}
