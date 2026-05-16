export default function Sparkline({ data = [] }) {
  const max = Math.max(...data, 1);

  return (
    <div className="sparkline" title={data.join(', ')}>
      {data.map((v, i) => (
        <div
          key={i}
          className="sparkline__bar"
          style={{ height: `${(v / max) * 100}%` }}
        />
      ))}
    </div>
  );
}
