<template>
  <div class="container">
    <header class="app-header">
      <div class="app-header-top">
        <h1 class="app-title">ANS - Inteligência de Dados</h1>
        <ThemeToggle @theme-change="handleThemeChange" />
      </div>

      <nav class="tabs">
        <button @click="view = 'search'" :class="{ active: view === 'search' }">
          🔍 Busca de Operadoras
        </button>
        <button @click="loadRanking" :class="{ active: view === 'ranking' }">
          📊 Ranking de Gastos
        </button>
        <button @click="loadDashboard" :class="{ active: view === 'dashboard' }">
          📈 Dashboard Analytics
        </button>
        <!-- v1.2 — Novas abas contábeis (Fase 2) -->
        <button @click="view = 'financeira'" :class="{ active: view === 'financeira' }">
          🏦 Financeira
        </button>
        <button @click="view = 'operacional'" :class="{ active: view === 'operacional' }">
          ⚙️ Operacional
        </button>
        <button @click="view = 'estrutura'" :class="{ active: view === 'estrutura' }">
          🏗️ Estrutura
        </button>
        <!-- v1.2 — Análises avançadas (Fase 3) -->
        <button @click="view = 'top20'" :class="{ active: view === 'top20' }">
          🏆 Top 20
        </button>
        <button @click="view = 'trimestral'" :class="{ active: view === 'trimestral' }">
          🔄 Trimestral
        </button>
        <button @click="view = 'regional'" :class="{ active: view === 'regional' }">
          🗺️ Regional
        </button>
        <button @click="view = 'admin'" :class="{ active: view === 'admin' }">
          ⚙️ Admin
        </button>
      </nav>

      <!-- v1.2 — Seletor de ano + exportação global (F4.1/F4.2) -->
      <div class="global-bar" v-if="!['search', 'admin'].includes(view)">
        <label>Ano:
          <select v-model="selectedYear" @change="onYearChange">
            <option v-for="ano in availableYears" :key="ano" :value="ano">{{ ano }}</option>
          </select>
        </label>
        <span class="spacer"></span>
        <button class="btn-export" @click="downloadExport('pdf')">📥 PDF</button>
        <button class="btn-export" @click="downloadExport('excel')">📥 Excel</button>
        <button class="btn-ghost" @click="showUpload = true">📤 Upload CSV</button>
      </div>
    </header>

    <!-- ABA: BUSCA -->
    <div v-if="view === 'search'" class="card">
      <div class="row">
        <input type="text" v-model="query" placeholder="Ex.: Bradesco ou 005711" @keydown.enter="handleEnter" />
        <select v-model="filterModalidade" class="filter-select">
          <option value="">Todas</option>
          <option>Medicina de Grupo</option>
          <option>Cooperativa</option>
        </select>
        <button :disabled="loadingSearch || !query.trim()" @click="() => doSearch(1)">Buscar</button>
        <ExportButton :data="results" filename="operadoras_ans.csv" />
      </div>

      <div v-if="results.length > 0" style="margin-top: 20px;">
        <table class="table">
          <thead>
            <tr>
              <th>Registro ANS</th>
              <th>CNPJ</th>
              <th>Nome Fantasia</th>
              <th>Razão Social</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, idx) in results" :key="idx">
              <td>{{ r.registro_ans }}</td>
              <td>{{ r.cnpj }}</td>
              <td>{{ r.nome_fantasia }}</td>
              <td>{{ r.razao_social }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="totalPages > 1" class="pagination">
          <button @click="doSearch(currentPage - 1)" :disabled="currentPage === 1">← Anterior</button>
          <span>Página {{ currentPage }} de {{ totalPages }}</span>
          <button @click="doSearch(currentPage + 1)" :disabled="currentPage === totalPages">Próxima →</button>
        </div>
      </div>
    </div>

    <!-- ABA: RANKING -->
    <div v-if="view === 'ranking'" class="card">
      <div class="ranking-header">
        <h2>
          Top 10 Maiores Gastos Assistenciais
          <YearBadge
            :year="selectedYear"
            :quarters="currentYearMeta.quarters"
            :hasAnsgap="currentYearMeta.hasAnsgap"
          />
        </h2>
        <select v-model="selectedYear" @change="onYearChange" class="year-select">
          <option v-for="ano in availableYears" :key="ano" :value="ano">
            {{ ano }}
            {{ yearMetadata[ano]?.hasAnsgap ? '⚠️' : '' }}
            {{ yearMetadata[ano]?.quarters < 4 ? `(${yearMetadata[ano].quarters}/4T)` : '✅' }}
          </option>
        </select>
      </div>

      <AcademicDisclaimer
        :year="selectedYear"
        :quarters="currentYearMeta.quarters"
        :hasAnsgap="currentYearMeta.hasAnsgap"
      />

      <p class="muted">
        Análise baseada em sinistros médico-hospitalares (ramo 41).
        Total: {{ formatCompact(dashboardExtras.totalGeral) }}
      </p>

      <SkeletonChart v-if="loadingRank" />
      <table v-else class="table">
        <thead>
          <tr>
            <th>Posição</th>
            <th>Operadora</th>
            <th style="text-align: right;">Gasto Total (R$)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in ranking" :key="idx">
            <td>{{ idx + 1 }}º</td>
            <td>
              <div>{{ item['Razao Social'] }}</div>
              <div class="progress-bar" :style="{ width: (item.valor_real / ranking[0].valor_real * 100) + '%' }"></div>
            </td>
            <td style="text-align: right; font-family: monospace; font-weight: bold; color: #4ade80;">
              {{ formatCurrency(item.valor_real) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ABA: ADMIN -->
    <div v-if="view === 'admin'" class="card">
      <AdminPanel />
    </div>

    <!-- v1.2 — ABAS CONTÁBEIS (Fase 2) -->
    <div v-if="['financeira', 'operacional', 'estrutura'].includes(view)" class="card">
      <DimensionView
        :dim="view"
        :periodo="selectedYear"
        @export="downloadExport"
        @detail="openTimeline"
      />
    </div>

    <!-- v1.2 — TOP 20 (F3.1) -->
    <div v-if="view === 'top20'" class="card">
      <TopRankingsView :periodo="selectedYear" @detail="openTimeline" />
    </div>

    <!-- v1.2 — TRIMESTRAL (F3.2) -->
    <div v-if="view === 'trimestral'" class="card">
      <QuarterlyView :periodo="selectedYear" />
    </div>

    <!-- v1.2 — REGIONAL / HEAT MAP (F3.5) -->
    <div v-if="view === 'regional'" class="card">
      <RegionalHeatmap :periodo="selectedYear" />
    </div>

    <!-- v1.2 — MODAIS -->
    <OperadoraTimelineModal
      v-if="timelineOp"
      :operadora="timelineOp"
      @close="timelineOp = null"
    />
    <UploadCsvModal v-if="showUpload" @close="showUpload = false" />

    <!-- ABA: DASHBOARD -->
    <div v-if="view === 'dashboard'" class="dashboard">
      <SkeletonChart v-if="loadingDashboard" />
      <template v-else>
        <div class="dashboard-header">
          <h2>📈 Dashboard de Analytics</h2>
          <p class="muted">Visualizações interativas dos dados de operadoras de saúde</p>
        </div>

        <YearTimeline
          :years="timelineData"
          :activeYear="selectedYear"
          @select="(y) => { selectedYear = y; onYearChange() }"
        />

        <AcademicDisclaimer
          :year="selectedYear"
          :quarters="currentYearMeta.quarters"
          :hasAnsgap="currentYearMeta.hasAnsgap"
        />

        <!-- KPI Cards -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon">💰</div>
            <div class="stat-value">{{ formatCompact(dashboardData.totalGastos) }}</div>
            <div class="stat-label">Gastos Totais ({{ selectedYear }})</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">🏥</div>
            <div class="stat-value">{{ dashboardData.totalOperadoras.toLocaleString('pt-BR') }}</div>
            <div class="stat-label">Operadoras com Gastos</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">📊</div>
            <div class="stat-value">{{ formatCompact(dashboardData.mediaGastos) }}</div>
            <div class="stat-label">Média por Operadora</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">🎯</div>
            <div class="stat-value">{{ dashboardData.concentracao }}%</div>
            <div class="stat-label">Concentração Top 3</div>
          </div>
        </div>

        <!-- Gráficos -->
        <div class="charts-grid">
          <div class="chart-card chart-card-wide">
            <h3>📊 Ranking de Gastos Anuais (R$ Bilhões) - {{ selectedYear }}</h3>
            <p class="chart-subtitle">Top 10 operadoras do período</p>
            <div class="chart-container-wide">
              <BarChart :data="barChartData" :options="barChartOptions" />
            </div>
          </div>

          <div class="chart-card">
            <h3>🎯 Market Share - {{ selectedYear }}</h3>
            <p class="chart-subtitle">Participação das Top 5 + Outras</p>
            <div class="chart-container">
              <PieChart :data="pieChartData" :options="pieChartOptions" />
            </div>
          </div>

          <div class="chart-card">
            <h3>📈 Evolução Anual dos Gastos</h3>
            <p class="chart-subtitle">Total de gastos assistenciais (R$ Bi)</p>
            <div class="chart-container">
              <BarChart :data="evolucaoAnualData" :options="evolucaoAnualOptions" />
            </div>
          </div>

          <div class="chart-card chart-card-wide">
            <h3>🔄 Comparação Temporal - Top 5 Operadoras</h3>
            <p class="chart-subtitle">Gastos por ano (R$ Bilhões)</p>
            <div class="chart-container-wide">
              <BarChart :data="comparacaoTemporalData" :options="comparacaoTemporalOptions" />
            </div>
          </div>

          <div class="chart-card chart-card-wide">
            <h3>📊 Análise de Concentração de Mercado - {{ selectedYear }}</h3>
            <p class="chart-subtitle">Percentual acumulado do Top 10</p>
            <div class="chart-container-wide">
              <BarChart :data="concentrationChartData" :options="concentrationChartOptions" />
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import AdminPanel from './components/AdminPanel.vue'
import BarChart from './components/BarChart.vue'
import ExportButton from './components/ExportButton.vue'
import PieChart from './components/PieChart.vue'
import SkeletonChart from './components/SkeletonChart.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import TreemapChart from './components/TreemapChart.vue'
import YearBadge from './components/YearBadge.vue'
import AcademicDisclaimer from './components/AcademicDisclaimer.vue'
import YearTimeline from './components/YearTimeline.vue'
// v1.2 — novos componentes (Fases 2-4)
import DimensionView from './components/DimensionView.vue'
import TopRankingsView from './components/TopRankingsView.vue'
import QuarterlyView from './components/QuarterlyView.vue'
import RegionalHeatmap from './components/RegionalHeatmap.vue'
import OperadoraTimelineModal from './components/OperadoraTimelineModal.vue'
import UploadCsvModal from './components/UploadCsvModal.vue'
import { api } from './api'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

// v1.2 — estado global de modais/export
const showUpload = ref(false)
const timelineOp = ref(null)

function openTimeline(row) {
  timelineOp.value = { registro_ans: row.registro_ans, razao_social: row.razao_social }
}

function downloadExport(kind) {
  // abre o endpoint de download do backend em nova aba (Content-Disposition attachment)
  window.open(api.exportUrl(kind, selectedYear.value), '_blank')
}

const view = ref('search')
const query = ref('')
const results = ref([])
const ranking = ref([])
const loadingSearch = ref(false)
const loadingRank = ref(false)
const loadingDashboard = ref(false)
const filterModalidade = ref('')
const currentPage = ref(1)
const totalPages = ref(1)
const totalResults = ref(0)

// ==================== TEMAS ====================
const THEMES = {
  'light-blue': {
    chart: ['#2C5282', '#3182CE', '#4299E1', '#4A5568', '#718096',
            '#2B6CB0', '#63B3ED', '#7C8BA1', '#2D3748', '#5A8FC0'],
    other: '#94A3B8', text: '#0f172a', textMuted: '#475569',
    grid: '#e2e8f0', accent: '#2563eb', danger: '#dc2626',
  },
  'dark-blue': {
    chart: ['#60A5FA', '#34D399', '#FBBF24', '#F87171', '#A78BFA',
            '#F472B6', '#FB923C', '#38BDF8', '#4ADE80', '#E879F9'],
    other: '#94A3B8', text: '#e7eefc', textMuted: '#c3d0e8',
    grid: '#2a3b63', accent: '#3b82f6', danger: '#f87171',
  },
  'light-gold': {
    chart: ['#1F4D3A', '#B8892B', '#6B4A2E', '#5E8F78', '#8C6A1F',
            '#A4573B', '#6B7A3A', '#7A6D5A', '#2F5F5A', '#8F7A3F'],
    other: '#8C8577', text: '#1F2A24', textMuted: '#46503F',
    grid: '#E2DACB', accent: '#1F4D3A', danger: '#A8402F',
  },
  'dark-gold': {
    chart: ['#4F9A78', '#D4A94A', '#A67C52', '#7FBFA0', '#B89548',
            '#D07F5F', '#9AAE5E', '#B5A890', '#5FA39B', '#E3D2A0'],
    other: '#8a9188', text: '#EDE8DC', textMuted: '#c2c9bd',
    grid: '#2C3A32', accent: '#4F9A78', danger: '#D9715E',
  },
}

const currentTheme = ref(localStorage.getItem('theme') || 'light-blue')

function getChartColors() {
  const t = THEMES[currentTheme.value] || THEMES['light-blue']
  return {
    1: t.chart[0], 2: t.chart[1], 3: t.chart[2], 4: t.chart[3], 5: t.chart[4],
    6: t.chart[5], 7: t.chart[6], 8: t.chart[7], 9: t.chart[8], 10: t.chart[9],
    other: t.other, text: t.text, textMuted: t.textMuted,
    border: t.grid, grid: t.grid, accent: t.accent, danger: t.danger,
    success: t.accent, warning: t.chart[1],
  }
}

function getOperadoraColor(index) {
  const c = getChartColors()
  const palette = [c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8], c[9], c[10]]
  return palette[index % palette.length]
}

function getYearColor(ano) {
  const c = getChartColors()
  const map = { '2024': c[1], '2025': c[2], '2026': c[5] }
  return map[ano] || c[4]
}

function handleThemeChange(themeId) {
  currentTheme.value = themeId
}

// ==================== CONTROLE DE ANO ====================
const selectedYear = ref('2025')  // começa pelo ano mais confiável
const availableYears = ref(['2024', '2025', '2026'])
const yearMetadata = ref({})

const currentYearMeta = computed(() => {
  return yearMetadata.value[selectedYear.value] || {
    quarters: 4, hasAnsgap: false, total_operadoras: 0, total_geral: 0
  }
})

const timelineData = computed(() => {
  const totals = Object.values(yearMetadata.value).map(m => m.total_geral || 1)
  const maxTotal = totals.length ? Math.max(...totals) : 1
  return availableYears.value.map(year => {
    const m = yearMetadata.value[year] || {}
    return {
      year,
      total: m.total_geral || 0,
      quarters: m.quarters || 4,
      hasAnsgap: m.hasAnsgap || false,
      heightPct: Math.max(10, ((m.total_geral || 0) / maxTotal) * 100),
      color: getYearColor(year),
    }
  })
})

// Carregar metadata no mount
onMounted(async () => {
  try {
    const res = await fetch(`${API_BASE}/api/v1/analytics/year-metadata`)
    if (res.ok) {
      const meta = await res.json()
      yearMetadata.value = meta
      const years = Object.keys(meta).sort()
      if (years.length) {
        availableYears.value = years
        // se o ano padrão não existe, usa o mais recente
        if (!years.includes(selectedYear.value)) {
          selectedYear.value = years[years.length - 1]
        }
      }
    }
  } catch (e) {
    console.warn('Falha ao buscar year-metadata:', e)
  }
})

// Dados extras
const dashboardExtras = ref({
  totalGeral: 0, totalOperadoras: 0, cachePorAno: {}
})

const evolucaoAnual = ref({})

// Formatação
const formatCompact = (value) => {
  if (value >= 1e9) return `R$ ${(value / 1e9).toFixed(2)} Bi`
  if (value >= 1e6) return `R$ ${(value / 1e6).toFixed(2)} Mi`
  if (value >= 1e3) return `R$ ${(value / 1e3).toFixed(2)} Mil`
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}
const formatCurrency = (val) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val)

// Dashboard data
const dashboardData = computed(() => {
  if (ranking.value.length === 0)
    return { totalGastos: 0, totalOperadoras: 0, mediaGastos: 0, concentracao: 0 }
  const total = dashboardExtras.value.totalGeral || ranking.value.reduce((s, i) => s + i.valor_real, 0)
  const top3 = ranking.value.slice(0, 3).reduce((s, i) => s + i.valor_real, 0)
  const totalOperadoras = dashboardExtras.value.totalOperadoras || ranking.value.length
  return {
    totalGastos: total,
    totalOperadoras,
    mediaGastos: total / Math.max(totalOperadoras, 1),
    concentracao: total > 0 ? ((top3 / total) * 100).toFixed(1) : 0
  }
})

const getShortName = (name) => {
  if (!name) return 'N/A'
  const words = name.split(' ')
  return words.length <= 3 ? name : words.slice(0, 3).join(' ')
}

// ==================== GRÁFICOS ====================
const barChartData = computed(() => ({
  labels: ranking.value.map(i => getShortName(i['Razao Social'])),
  datasets: [{
    label: 'Gastos Anuais (R$ Bi)',
    data: ranking.value.map(i => (i.valor_real / 1e9).toFixed(2)),
    backgroundColor: ranking.value.map((_, i) => getOperadoraColor(i)),
    borderColor: ranking.value.map((_, i) => getOperadoraColor(i)),
    borderWidth: 2
  }]
}))

const barChartOptions = computed(() => {
  const c = getChartColors()
  return {
    indexAxis: 'y',
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: ctx => `R$ ${ctx.parsed.x} Bi (R$ ${(ctx.parsed.x * 1e9).toLocaleString('pt-BR')})` } }
    },
    scales: {
      x: {
        beginAtZero: true,
        title: { display: true, text: 'Gastos Anuais (R$ Bi)', font: { size: 14, weight: 'bold' }, color: c.text },
        ticks: { callback: v => `R$ ${v} Bi`, color: c.textMuted },
        grid: { color: c.border }
      },
      y: { ticks: { font: { size: 11 }, autoSkip: false, color: c.text }, grid: { color: c.border } }
    },
    maintainAspectRatio: true
  }
})

const pieChartData = computed(() => {
  if (ranking.value.length === 0) return { labels: [], datasets: [] }
  const c = getChartColors()
  const total = dashboardExtras.value.totalGeral || ranking.value.reduce((s, i) => s + i.valor_real, 0)
  const top5 = ranking.value.slice(0, 5)
  const top5Total = top5.reduce((s, i) => s + i.valor_real, 0)
  const labels = top5.map(i => getShortName(i['Razao Social']))
  const values = top5.map(i => i.valor_real)
  if (total - top5Total > 0) { labels.push('Outras Operadoras'); values.push(total - top5Total) }
  return {
    labels,
    datasets: [{
      data: values.map(v => ((v / total) * 100).toFixed(1)),
      backgroundColor: [c[1], c[2], c[3], c[4], c[5], c.other],
      borderColor: c.border, borderWidth: 2
    }]
  }
})

const pieChartOptions = computed(() => {
  const c = getChartColors()
  return {
    plugins: {
      legend: { position: 'right', labels: { font: { size: 11 }, padding: 12, boxWidth: 15, color: c.text } },
      tooltip: { callbacks: { label: ctx => `${ctx.label}: ${ctx.parsed}%` } }
    },
    maintainAspectRatio: true
  }
})

const evolucaoAnualData = computed(() => {
  const anos = availableYears.value.filter(a => evolucaoAnual.value[a])
  return {
    labels: anos,
    datasets: [{
      label: 'Gastos Totais (R$ Bi)',
      data: anos.map(a => (evolucaoAnual.value[a] / 1e9).toFixed(2)),
      backgroundColor: anos.map(a => getYearColor(a)),
      borderColor: anos.map(a => getYearColor(a)),
      borderWidth: 2
    }]
  }
})

const evolucaoAnualOptions = computed(() => {
  const c = getChartColors()
  return {
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => `R$ ${ctx.parsed.y} Bi` } } },
    scales: {
      y: { beginAtZero: true, title: { display: true, text: 'R$ Bi', font: { size: 12, weight: 'bold' }, color: c.text },
           ticks: { callback: v => `R$ ${v} Bi`, color: c.textMuted }, grid: { color: c.border } },
      x: { title: { display: true, text: 'Ano', font: { size: 12 }, color: c.text }, ticks: { color: c.text } }
    },
    maintainAspectRatio: true
  }
})

const comparacaoTemporalData = computed(() => {
  const opSet = new Set()
  const dados = {}
  availableYears.value.forEach(ano => {
    if (evolucaoAnual.value[ano + '_top5']) {
      dados[ano] = evolucaoAnual.value[ano + '_top5']
      evolucaoAnual.value[ano + '_top5'].forEach(i => opSet.add(i.razao_social))
    }
  })
  if (opSet.size === 0) return { labels: [], datasets: [] }
  const ops = Array.from(opSet).slice(0, 5)
  return {
    labels: ops.map(op => getShortName(op)),
    datasets: availableYears.value
      .filter(a => dados[a])
      .map(a => ({
        label: a,
        data: ops.map(op => {
          const it = dados[a].find(i => i.razao_social === op)
          return it ? (it.valor_total / 1e9).toFixed(2) : 0
        }),
        backgroundColor: getYearColor(a),
        borderColor: getYearColor(a),
        borderWidth: 2
      }))
  }
})

const comparacaoTemporalOptions = computed(() => {
  const c = getChartColors()
  return {
    plugins: { legend: { position: 'top', labels: { font: { size: 12 }, padding: 15, boxWidth: 15, color: c.text } } },
    scales: {
      y: { beginAtZero: true, title: { display: true, text: 'R$ Bi', font: { size: 12, weight: 'bold' }, color: c.text },
           ticks: { callback: v => `R$ ${v} Bi`, color: c.textMuted }, grid: { color: c.border } },
      x: { title: { display: true, text: 'Operadora', font: { size: 12 }, color: c.text }, ticks: { color: c.textMuted } }
    },
    maintainAspectRatio: true
  }
})

const concentrationChartData = computed(() => {
  if (ranking.value.length === 0) return { labels: [], datasets: [] }
  const c = getChartColors()
  const total = dashboardExtras.value.totalGeral || ranking.value.reduce((s, i) => s + i.valor_real, 0)
  let acc = 0
  const accData = ranking.value.map(i => { acc += i.valor_real; return ((acc / total) * 100).toFixed(1) })
  return {
    labels: ranking.value.map((_, i) => `Top ${i + 1}`),
    datasets: [
      { label: 'Concentração Acumulada (%)', data: accData,
        backgroundColor: c[1] + 'B3', borderColor: c[1], borderWidth: 2, order: 2 },
      { label: 'Linha de Pareto (80%)', data: Array(ranking.value.length).fill(80),
        type: 'line', borderColor: c.danger, borderWidth: 2, borderDash: [10, 5],
        pointRadius: 0, fill: false, order: 1 }
    ]
  }
})

const concentrationChartOptions = computed(() => {
  const c = getChartColors()
  return {
    plugins: { legend: { display: true, position: 'top', labels: { boxWidth: 12, padding: 10, font: { size: 11 }, usePointStyle: true, color: c.text } } },
    scales: {
      y: { beginAtZero: true, max: 100,
           title: { display: true, text: 'Percentual Acumulado (%)', font: { size: 14, weight: 'bold' }, color: c.text },
           ticks: { callback: v => `${v}%`, color: c.textMuted }, grid: { color: c.border } },
      x: { title: { display: true, text: 'Posição no Ranking', font: { size: 12 }, color: c.text }, ticks: { color: c.textMuted } }
    }
  }
})

// ==================== BUSCA E NAVEGAÇÃO ====================
function handleEnter(event) { event.preventDefault(); doSearch(1) }

async function doSearch(page = 1) {
  if (!query.value.trim()) return
  loadingSearch.value = true
  try {
    const res = await fetch(`${API_BASE}/api/v1/operadoras?q=${encodeURIComponent(query.value)}&page=${page}&limit=50`)
    const data = await res.json()
    if (data.results) {
      results.value = data.results
      currentPage.value = data.metadata.page
      totalPages.value = data.metadata.pages
      totalResults.value = data.metadata.total
    }
  } catch (e) {
    alert("Erro na API de busca"); console.error(e)
  } finally {
    loadingSearch.value = false
  }
}

async function fetchAnalyticsData(ano = null) {
  const periodo = ano || selectedYear.value
  try {
    const res = await fetch(`${API_BASE}/api/v1/analytics/gastos?periodo=${periodo}&top=10`)
    const data = await res.json()
    const resultado = {
      ranking: data.ranking ? data.ranking.map(i => ({
        'Razao Social': i.razao_social, 'valor_real': i.valor_total
      })) : [],
      totalGeral: data.total_geral || 0,
      totalOperadoras: data.total_operadoras || 0,
      top5: data.ranking ? data.ranking.slice(0, 5) : []
    }
    if (resultado.totalGeral > 0) {
      dashboardExtras.value.cachePorAno[periodo] = {
        totalGeral: resultado.totalGeral, totalOperadoras: resultado.totalOperadoras
      }
    }
    return resultado
  } catch (e) {
    console.error('Erro ao buscar analytics:', e); return null
  }
}

async function fetchEvolucaoAnual() {
  const promises = availableYears.value.map(a =>
    fetch(`${API_BASE}/api/v1/analytics/gastos?periodo=${a}&top=5`)
      .then(r => r.json()).catch(() => null)
  )
  const results = await Promise.all(promises)
  const ev = {}
  results.forEach((data, idx) => {
    if (data && data.total_geral) {
      const a = availableYears.value[idx]
      ev[a] = data.total_geral
      ev[a + '_top5'] = data.ranking || []
    }
  })
  return ev
}

async function onYearChange() {
  const ano = selectedYear.value
  ranking.value = []
  dashboardExtras.value.totalGeral = 0
  dashboardExtras.value.totalOperadoras = 0

  const cached = dashboardExtras.value.cachePorAno[ano]
  if (cached) {
    dashboardExtras.value.totalGeral = cached.totalGeral
    dashboardExtras.value.totalOperadoras = cached.totalOperadoras
  }

  if (view.value === 'ranking') await loadRanking()
  else if (view.value === 'dashboard') await loadDashboard()
  // v1.2: abas novas (financeira/operacional/estrutura/top20/trimestral/regional)
  // reagem à mudança de selectedYear via watch interno dos próprios componentes.
}

async function loadRanking() {
  view.value = 'ranking'
  loadingRank.value = true
  try {
    const data = await fetchAnalyticsData(selectedYear.value)
    if (data && data.ranking.length > 0) {
      ranking.value = data.ranking
      if (data.totalGeral > 0) dashboardExtras.value.totalGeral = data.totalGeral
      if (data.totalOperadoras > 0) dashboardExtras.value.totalOperadoras = data.totalOperadoras
    }
  } catch (e) { console.error(e); alert("Erro ao carregar ranking") }
  finally { loadingRank.value = false }
}

async function loadDashboard() {
  view.value = 'dashboard'
  loadingDashboard.value = true
  try {
    const data = await fetchAnalyticsData(selectedYear.value)
    if (data && data.ranking.length > 0) {
      ranking.value = data.ranking
      if (data.totalGeral > 0) dashboardExtras.value.totalGeral = data.totalGeral
      if (data.totalOperadoras > 0) dashboardExtras.value.totalOperadoras = data.totalOperadoras
    }
    const ev = await fetchEvolucaoAnual()
    if (ev && Object.keys(ev).length > 0) evolucaoAnual.value = ev
  } catch (e) { console.error(e); alert("Erro ao carregar dashboard") }
  finally { loadingDashboard.value = false }
}
</script>

<style scoped>
/* v1.2 — barra global de ano + exportação */
.global-bar {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  margin-top: 10px; padding: 8px 0;
}
.global-bar label { font-size: 13px; font-weight: 600; }
.global-bar select { padding: 6px 10px; border-radius: 8px; border: 1px solid #cbd5e1; }
.global-bar .spacer { flex: 1; }
.btn-export { background: #1f4d3a; color: #fff; border: none; padding: 7px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-export:hover { opacity: .9; }
.btn-ghost { background: transparent; border: 1px solid #cbd5e1; padding: 7px 14px; border-radius: 8px; cursor: pointer; }

.ranking-header {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px; margin-bottom: 8px;
}
.ranking-header h2 {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
</style>