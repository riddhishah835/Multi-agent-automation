export default function RiskScorePanel({ data, compact = false }) {
  const recClass =
    data.recommendation.toLowerCase().includes('reject')
      ? 'risk-rec--reject'
      : data.recommendation.toLowerCase().includes('approve')
        ? 'risk-rec--approve'
        : 'risk-rec--conditional';

  return (
    <article className={`risk-panel${compact ? ' risk-panel--compact' : ''}`}>
      <section className="risk-panel__scores">
        <section className="risk-panel__main">
          <span className="risk-panel__label">Risk Score</span>
          <span className="risk-panel__value risk-panel__value--risk">{data.overall}/100</span>
        </section>
        <section className="risk-panel__main">
          <span className="risk-panel__label">Compliance Score</span>
          <span className="risk-panel__value">{data.compliance}/100</span>
        </section>
      </section>
      <section className={`risk-panel__rec ${recClass}`}>
        <span className="risk-panel__label">Recommendation</span>
        <strong>{data.recommendation}</strong>
      </section>
      {!compact && data.breakdown && (
        <ul className="risk-panel__breakdown">
          {data.breakdown.map((b) => (
            <li key={b.label}>
              <span>{b.label}</span>
              <span className="risk-bar">
                <span className="risk-bar__fill" style={{ width: `${b.score}%` }} />
              </span>
              <span>{b.score}</span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
