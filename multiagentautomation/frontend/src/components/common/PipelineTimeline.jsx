import { Check, Circle, Pause } from 'lucide-react';

function StepIcon({ status }) {
  if (status === 'complete') return <Check size={14} />;
  if (status === 'paused') return <Pause size={14} />;
  return <Circle size={12} />;
}

export default function PipelineTimeline({ steps, compact = false }) {
  return (
    <ol className={`pipeline-timeline${compact ? ' pipeline-timeline--compact' : ''}`}>
      {steps.map((step) => (
        <li key={step.id} className={`pipeline-step pipeline-step--${step.status}`}>
          <span className="pipeline-step__icon">
            <StepIcon status={step.status} />
          </span>
          <span className="pipeline-step__label">{step.name}</span>
          {!compact && step.duration && (
            <span className="pipeline-step__meta">{step.duration}</span>
          )}
        </li>
      ))}
    </ol>
  );
}
