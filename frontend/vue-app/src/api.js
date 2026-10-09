// Cliente HTTP central do frontend (Fases 2-4 v1.2)
const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function getJSON(path, params = {}) {
  const url = new URL(`${API_BASE}${path}`)
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v)
  })
  const res = await fetch(url.toString())
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try { detail = (await res.json()).detail || detail } catch (_) { /* ignore */ }
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  base: API_BASE,
  yearMetadata: () => getJSON('/api/v1/analytics/year-metadata'),
  gastos: (periodo, top = 20) => getJSON('/api/v1/analytics/gastos', { periodo, top }),
  dimension: (dim, periodo, opts = {}) =>
    getJSON(`/api/v1/dimension/${dim}`, { periodo, ...opts }),
  topRankings: (periodo, top = 20) => getJSON('/api/v1/top-rankings', { periodo, top }),
  quarterly: (periodo, registroAns = null) =>
    getJSON('/api/v1/quarterly', { periodo, registro_ans: registroAns }),
  regional: (periodo, metric = 'gasto_total') =>
    getJSON('/api/v1/regional', { periodo, metric }),
  summary: (periodo) => getJSON('/api/v1/summary', { periodo }),
  operadoraHistory: (registroAns) =>
    getJSON(`/api/v1/operadoras/${encodeURIComponent(registroAns)}/history`),
  searchOperadoras: (q, page = 1, limit = 50) =>
    getJSON('/api/v1/operadoras', { q, page, limit }),
  exportUrl: (kind, periodo) => `${API_BASE}/api/v1/export/${kind}?periodo=${periodo}`,
  uploadCsv: async (file) => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${API_BASE}/api/v1/upload-csv`, { method: 'POST', body: fd })
    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try { detail = (await res.json()).detail || detail } catch (_) { /* ignore */ }
      throw new Error(detail)
    }
    return res.json()
  },
}

// Formatadores compartilhados
export const fmtCompact = (v) => {
  const n = Number(v) || 0
  if (Math.abs(n) >= 1e9) return `R$ ${(n / 1e9).toFixed(2)} Bi`
  if (Math.abs(n) >= 1e6) return `R$ ${(n / 1e6).toFixed(2)} Mi`
  if (Math.abs(n) >= 1e3) return `R$ ${(n / 1e3).toFixed(2)} Mil`
  return fmtCurrency(n)
}
export const fmtCurrency = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(v) || 0)
export const fmtPercent = (v) => `${((Number(v) || 0) * 100).toFixed(1)}%`
