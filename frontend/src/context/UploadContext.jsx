import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { uploads as seedUploads } from '../data/mockData';
import { deleteFileRecord, getAllFileRecords, saveFileRecord } from '../utils/fileStore';
import { useLogs } from './LogsContext';

const UploadContext = createContext(null);

const MAX_BYTES = 50 * 1024 * 1024;
const ACCEPT = '.pdf,.doc,.docx,.xls,.xlsx,.txt';

function inferDocType(name) {
  const n = name.toLowerCase();
  if (n.includes('soc2') || n.includes('soc_2')) return 'SOC2 Report';
  if (n.includes('iso')) return 'ISO Certification';
  if (n.includes('aml')) return 'AML Policy';
  if (n.includes('privacy') || n.includes('gdpr')) return 'Privacy Policy';
  if (n.includes('financial') || n.includes('statement')) return 'Financial Statement';
  if (n.includes('contract') || n.includes('agreement')) return 'Contract';
  if (n.endsWith('.pdf')) return 'SOC2 Report';
  return 'Contract';
}

function recordToRow(record) {
  return {
    id: record.id,
    name: record.name,
    type: record.type,
    size: record.size,
    progress: record.progress ?? 0,
    ocr: record.ocr ?? 'pending',
    extraction: record.extraction ?? 'pending',
    uploadedAt: record.uploadedAt,
  };
}

async function readFileWithProgress(file, onProgress) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(file);
  });
}

function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

export function UploadProvider({ children }) {
  const { appendLog } = useLogs();
  const [uploads, setUploads] = useState([]);
  const [uploading, setUploading] = useState(false);

  const refreshFromDb = useCallback(async () => {
    try {
      const stored = await getAllFileRecords();
      if (stored.length) {
        setUploads(stored.map(recordToRow).sort((a, b) => b.uploadedAt - a.uploadedAt));
      } else {
        setUploads(seedUploads);
      }
    } catch {
      setUploads(seedUploads);
    }
  }, []);

  useEffect(() => {
    refreshFromDb();
  }, [refreshFromDb]);

  const updateRecord = useCallback(async (id, patch) => {
    const all = await getAllFileRecords();
    const existing = all.find((r) => r.id === id);
    if (!existing) return;
    const next = { ...existing, ...patch };
    await saveFileRecord(next);
    setUploads((prev) =>
      prev.map((u) => (u.id === id ? recordToRow(next) : u)).sort((a, b) => (b.uploadedAt || 0) - (a.uploadedAt || 0))
    );
  }, []);

  const runPipeline = useCallback(
    async (id, name) => {
      appendLog(`ocr: started ${name}`);
      await updateRecord(id, { ocr: 'processing' });
      await delay(800);
      await updateRecord(id, { ocr: 'complete' });
      appendLog(`ocr: complete ${name}`);

      appendLog(`extraction: started ${name}`);
      await updateRecord(id, { extraction: 'processing' });
      await delay(1000);
      await updateRecord(id, { extraction: 'complete', progress: 100 });
      appendLog(`extraction: complete ${name}`);
      appendLog(`ingestion: ${name} ready for audit pipeline`);
    },
    [appendLog, updateRecord]
  );

  const uploadFiles = useCallback(
    async (fileList) => {
      const files = Array.from(fileList || []);
      if (!files.length) return { ok: false, error: 'No files selected' };

      const tooBig = files.find((f) => f.size > MAX_BYTES);
      if (tooBig) {
        return { ok: false, error: `${tooBig.name} exceeds 50MB limit` };
      }

      setUploading(true);
      appendLog(`upload: ${files.length} file(s) queued`);

      for (const file of files) {
        const id = crypto.randomUUID();
        const type = inferDocType(file.name);
        const base = {
          id,
          name: file.name,
          type,
          size: file.size,
          mimeType: file.type,
          progress: 0,
          ocr: 'queued',
          extraction: 'pending',
          uploadedAt: Date.now(),
        };

        await saveFileRecord({ ...base, data: null });
        setUploads((prev) => [recordToRow(base), ...prev]);
        appendLog(`upload: receiving ${file.name} (${(file.size / 1024).toFixed(1)} KB)`);

        try {
          const buffer = await readFileWithProgress(file, (pct) => {
            const progress = Math.min(pct, 95);
            setUploads((prev) =>
              prev.map((u) => (u.id === id ? { ...u, progress } : u))
            );
          });

          await saveFileRecord({
            ...base,
            data: buffer,
            progress: 100,
            ocr: 'queued',
          });
          setUploads((prev) =>
            prev.map((u) => (u.id === id ? { ...u, progress: 100, ocr: 'queued' } : u))
          );
          appendLog(`upload: stored ${file.name} in local vault`);

          runPipeline(id, file.name);
        } catch (err) {
          appendLog(`upload: failed ${file.name} — ${err.message}`);
          await updateRecord(id, { ocr: 'failed', extraction: 'failed' });
        }
      }

      setUploading(false);
      return { ok: true };
    },
    [appendLog, runPipeline, updateRecord]
  );

  const removeUpload = useCallback(
    async (id) => {
      await deleteFileRecord(id);
      setUploads((prev) => prev.filter((u) => u.id !== id));
      appendLog(`upload: removed file ${id}`);
    },
    [appendLog]
  );

  return (
    <UploadContext.Provider
      value={{
        uploads,
        uploading,
        uploadFiles,
        removeUpload,
        accept: ACCEPT,
        refreshFromDb,
      }}
    >
      {children}
    </UploadContext.Provider>
  );
}

export function useUploads() {
  const ctx = useContext(UploadContext);
  if (!ctx) throw new Error('useUploads must be used within UploadProvider');
  return ctx;
}
