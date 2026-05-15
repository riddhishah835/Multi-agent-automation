import { useRef, useState } from 'react';
import { FileUp, Trash2, Upload } from 'lucide-react';
import PageHeader from '../components/common/PageHeader';
import { useToast } from '../context/ToastContext';
import { useUploads } from '../context/UploadContext';
import { documentTypes } from '../data/mockData';

function statusLabel(s) {
  if (s === 'complete') return 'Complete';
  if (s === 'processing') return 'Processing';
  if (s === 'queued') return 'Queued';
  if (s === 'failed') return 'Failed';
  return 'Pending';
}

export default function DocumentUpload() {
  const { addToast } = useToast();
  const { uploads, uploading, uploadFiles, removeUpload, accept } = useUploads();
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const pickFiles = () => inputRef.current?.click();

  const handleFiles = async (fileList) => {
    const result = await uploadFiles(fileList);
    if (result.ok) {
      addToast('Files uploaded and stored successfully', 'success');
    } else if (result.error) {
      addToast(result.error, 'error');
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <>
      <PageHeader
        title="Document Upload"
        subtitle="SOC2, ISO, contracts, AML, privacy, and financial statements"
        actions={
          <button
            type="button"
            className="btn btn--primary"
            disabled={uploading}
            onClick={pickFiles}
          >
            <Upload size={16} /> {uploading ? 'Uploading…' : 'Upload files'}
          </button>
        }
      />

      <input
        ref={inputRef}
        type="file"
        multiple
        accept={accept}
        className="sr-only"
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = '';
        }}
      />

      <section
        className={`upload-zone card${dragOver ? ' upload-zone--active' : ''}`}
        role="button"
        tabIndex={0}
        onClick={pickFiles}
        onKeyDown={(e) => e.key === 'Enter' && pickFiles()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <FileUp size={40} color="var(--accent)" />
        <p><strong>Drag & drop documents</strong> or click to browse</p>
        <p className="text-muted">PDF, DOCX, XLSX — max 50MB per file · stored in browser vault</p>
        <section className="upload-types">
          {documentTypes.map((t) => (
            <span key={t} className="chip">{t}</span>
          ))}
        </section>
      </section>

      <article className="card" style={{ marginTop: '1.25rem' }}>
        <h2 className="card__title">Upload queue ({uploads.length})</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>File</th>
              <th>Type</th>
              <th>Size</th>
              <th>Progress</th>
              <th>OCR</th>
              <th>Extraction</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {uploads.map((f) => (
              <tr key={f.id}>
                <td><strong>{f.name}</strong></td>
                <td>{f.type}</td>
                <td className="text-muted">
                  {f.size ? `${(f.size / 1024).toFixed(1)} KB` : '—'}
                </td>
                <td>
                  <span className="progress-bar">
                    <span className="progress-bar__fill" style={{ width: `${f.progress}%` }} />
                  </span>
                  <span className="text-muted">{f.progress}%</span>
                </td>
                <td><span className={`proc proc--${f.ocr}`}>{statusLabel(f.ocr)}</span></td>
                <td><span className={`proc proc--${f.extraction}`}>{statusLabel(f.extraction)}</span></td>
                <td>
                  <button
                    type="button"
                    className="icon-btn"
                    aria-label={`Remove ${f.name}`}
                    onClick={() => removeUpload(f.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {uploads.length === 0 && (
          <p className="empty-state">No files yet. Upload documents to start an audit.</p>
        )}
      </article>
    </>
  );
}
