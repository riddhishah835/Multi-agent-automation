import { useMemo } from 'react';
import { Sparkles } from 'lucide-react';

function highlightJson(text) {
  return text
    .replace(/"([^"]+)":/g, '<span class="key">"$1"</span>:')
    .replace(/: "([^"]*)"/g, ': <span class="str">"$1"</span>')
    .replace(/: (\d+\.?\d*)/g, ': <span class="num">$1</span>');
}

export default function JsonEditor({ value, onChange, readOnly = false }) {
  const html = useMemo(() => highlightJson(value), [value]);

  if (readOnly) {
    return (
      <div className="code-editor">
        <pre
          className="code-editor__preview"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </div>
    );
  }

  return (
    <div className="code-editor" style={{ position: 'relative' }}>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} spellCheck={false} />
      <Sparkles
        size={16}
        style={{
          position: 'absolute',
          bottom: 10,
          right: 10,
          color: 'var(--accent)',
          opacity: 0.7,
        }}
        title="AI schema assist"
      />
    </div>
  );
}
