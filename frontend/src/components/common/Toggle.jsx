export default function Toggle({ on, onChange, label }) {
  return (
    <button
      type="button"
      className={`toggle${on ? ' toggle--on' : ''}`}
      onClick={() => onChange(!on)}
      role="switch"
      aria-checked={on}
      aria-label={label}
    >
      <span className="toggle__knob" />
    </button>
  );
}
