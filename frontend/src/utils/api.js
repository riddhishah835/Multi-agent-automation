const API_BASE = import.meta.env.VITE_API_URL || '/api';

export function getApiBase() {
  return API_BASE;
}

export async function apiFetch(path, { token, method = 'GET', body, headers = {} } = {}) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const reqHeaders = { ...headers };

  if (token) {
    reqHeaders.Authorization = `Bearer ${token}`;
  }

  if (body && !(body instanceof FormData)) {
    reqHeaders['Content-Type'] = 'application/json';
  }

  const res = await fetch(url, {
    method,
    headers: reqHeaders,
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });

  return res;
}

export async function checkApiHealth() {
  try {
    const res = await apiFetch('/health');
    return res.ok;
  } catch {
    return false;
  }
}
