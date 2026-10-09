/* API client – uses relative paths so Vite proxy forwards to FastAPI */
const BASE = import.meta.env.VITE_API_URL || '/api';
const ROOT = import.meta.env.VITE_API_ROOT || '';

async function call(method, path, body) {
  const url = path.startsWith('/health') ? `${ROOT}${path}` : `${BASE}${path}`;
  const resp = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export const api = {
  health:            ()          => call('GET',  '/health'),
  extract:           (text)      => call('POST', '/requirements/extract', { text }),
  validate:          (req)       => call('POST', '/requirements/validate', req),
  recommend:         (body)      => call('POST', '/recommendations', body),
  startTrip:         (req)       => call('POST', '/trip/start', req),
  quote:             (trip)      => call('POST', '/quote/generate', trip),
  validateQuote:     (trip)      => call('POST', '/quote/validate', trip),
  modify:            (trip, cmd) => call('POST', '/trip/modify', { trip, command: cmd }),
  itinerary:         (trip)      => call('POST', '/itinerary/generate', trip),
  optimizeItinerary: (trip)      => call('POST', '/itinerary/optimize', trip),
  destinations:      ()          => call('GET',  '/destinations'),
  hotels:            (params)    => {
    const q = new URLSearchParams(params || {}).toString();
    return call('GET', `/hotels${q ? '?' + q : ''}`);
  },
  activities:        (dest)      => call('GET', `/activities${dest ? '?destination=' + encodeURIComponent(dest) : ''}`),
  suppliers:         ()          => call('GET',  '/suppliers'),
  supplierHealth:    (id)        => call('GET',  `/suppliers/${id}/health`),
};

export function formatINR(n) {
  if (n == null) return '—';
  return '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}
export function pct(n) {
  if (n == null) return '—';
  return (n * 100).toFixed(0) + '%';
}
export function stars(n) {
  return '★'.repeat(n || 0) + '☆'.repeat(5 - (n || 0));
}
