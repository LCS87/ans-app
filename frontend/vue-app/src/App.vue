<template>
  <div class="container">
    <h1>ANS - Inteligência de Dados</h1>

    <ThemeToggle @theme-change="handleThemeChange" />
    <div class="tabs">
      <button @click="view = 'search'" :class="{ active: view === 'search' }">
        🔍 Busca de Operadoras
      </button>
      <button @click="loadRanking" :class="{ active: view === 'ranking' }">
        📊 Ranking de Gastos
      </button>
      <button @click="loadDashboard" :class="{ active: view === 'dashboard' }">
        📈 Dashboard Analytics
      </button>
      <button @click="view = 'admin'" :class="{ active: view === 'admin' }">
        ⚙️ Admin
      </button>
    </div>

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
        <h2>Top 10 Maiores Gastos Assistenciais ({{ selectedYear }})</h2>
        <select v-model="selectedYear" @change="onYearChange" class="year-select">
          <option v-for="ano in availableYears" :key="ano" :value="ano">{{ ano }}</option>
        </select>
      </div>
      <p class="muted">Análise baseada em sinistros médico-hospitalares. Total: {{ formatCompact(dashboardExtras.totalGeral) }}</p>

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

    <!-- ABA: DASHBOARD -->
    <div v-if="view === 'dashboard'" class="dashboard">
      <SkeletonChart v-if="loadingDashboard" />
      <template v-else>
        <div class="dashboard-header">
          <h2>📈 Dashboard de Analytics</h2>
          <p class="muted">Visualizações interativas dos dados de operadoras de saúde</p>
          <div class="year-control">
            <label>Período:</label>
            <select v-model="selectedYear" @change="onYearChange" class="year-select">
              <option v-for="ano in availableYears" :key="ano" :value="ano">{{ ano }}</option>
            </select>
          </div>
        </div>

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
          <!-- Ranking do ano selecionado -->
          <div class="chart-card chart-card-wide">
            <h3>📊 Ranking de Gastos Anuais (R$ Bilhões) - {{ selectedYear }}</h3>
            <p class="chart-subtitle">Top 10 operadoras do período</p>
            <div class="chart-container-wide">
              <BarChart :data="barChartData" :options="barChartOptions" />
            </div>
          </div>

          <!-- Market Share (Pie) -->
          <div class="chart-card">
            <h3>🎯 Market Share - {{ selectedYear }}</h3>
            <p class="chart-subtitle">Participação das Top 5 + Outras</p>
            <div class="chart-container">
              <PieChart :data="pieChartData" :options="pieChartOptions" />
            </div>
          </div>

          <!-- Evolução Anual -->
          <div class="chart-card">
            <h3>📈 Evolução Anual dos Gastos</h3>
            <p class="chart-subtitle">Total de gastos assistenciais (R$ Bi)</p>
            <div class="chart-container">
              <BarChart :data="evolucaoAnualData" :options="evolucaoAnualOptions" />
            </div>
          </div>

          <!-- Comparação Temporal Top 5 -->
          <div class="chart-card chart-card-wide">
            <h3>🔄 Comparação Temporal - Top 5 Operadoras</h3>
            <p class="chart-subtitle">Gastos por ano (R$ Bilhões)</p>
            <div class="chart-container-wide">
              <BarChart :data="comparacaoTemporalData" :options="comparacaoTemporalOptions" />
            </div>
          </div>

          <!-- Concentração de Mercado -->
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
import { computed, ref } from 'vue'
import AdminPanel from './components/AdminPanel.vue'
import BarChart from './components/BarChart.vue'
import ExportButton from './components/ExportButton.vue'
import PieChart from './components/PieChart.vue'
import SkeletonChart from './components/SkeletonChart.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import TreemapChart from './components/TreemapChart.vue'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

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
// ==================== CORES POR TEMA ====================
// ==================== MAPA DE TEMAS (JS — REATIVO) ====================
const THEMES = {
  'light-blue': {
    chart: ['#2C5282', '#3182CE', '#4299E1', '#4A5568', '#718096',
            '#2B6CB0', '#63B3ED', '#7C8BA1', '#2D3748', '#5A8FC0'],
    other: '#94A3B8',
    text: '#0f172a',
    textMuted: '#475569',   // mais escuro p/ contraste em fundo claro
    grid: '#e2e8f0',
    accent: '#2563eb',
    danger: '#dc2626',
  },
  'dark-blue': {
    chart: ['#60A5FA', '#34D399', '#FBBF24', '#F87171', '#A78BFA',
            '#F472B6', '#FB923C', '#38BDF8', '#4ADE80', '#E879F9'],
    other: '#94A3B8',
    text: '#e7eefc',
    textMuted: '#c3d0e8',   // mais claro p/ contraste em fundo escuro
    grid: '#2a3b63',
    accent: '#3b82f6',
    danger: '#f87171',
  },
  'light-gold': {
    chart: ['#1F4D3A', '#B8892B', '#6B4A2E', '#5E8F78', '#8C6A1F',
            '#A4573B', '#6B7A3A', '#7A6D5A', '#2F5F5A', '#8F7A3F'],
    other: '#8C8577',       // taupe mais escuro p/ legibilidade
    text: '#1F2A24',
    textMuted: '#46503F',   // mais escuro que #5C6659
    grid: '#E2DACB',
    accent: '#1F4D3A',
    danger: '#A8402F',
  },
  'dark-gold': {
    chart: ['#4F9A78', '#D4A94A', '#A67C52', '#7FBFA0', '#B89548',
            '#D07F5F', '#9AAE5E', '#B5A890', '#5FA39B', '#E3D2A0'],
    other: '#8a9188',       // taupe mais claro p/ fundo escuro
    text: '#EDE8DC',
    textMuted: '#c2c9bd',   // mais claro que #A7B0A3
    grid: '#2C3A32',
    accent: '#4F9A78',
    danger: '#D9715E',
  },
}

const currentTheme = ref(localStorage.getItem('theme') || 'light-blue')

function getChartColors() {
  const t = THEMES[currentTheme.value] || THEMES['light-blue']
  return {
    1: t.chart[0], 2: t.chart[1], 3: t.chart[2], 4: t.chart[3], 5: t.chart[4],
    6: t.chart[5], 7: t.chart[6], 8: t.chart[7], 9: t.chart[8], 10: t.chart[9],
    other: t.other,
    text: t.text,
    textMuted: t.textMuted,
    border: t.grid,
    grid: t.grid,
    accent: t.accent,
    danger: t.danger,
    success: t.accent,
    warning: t.chart[1],
  }
}

function getOperadoraColor(index) {
  const c = getChartColors()
  const palette = [c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8], c[9], c[10]]
  return palette[index % palette.length]
}

function getYearColor(ano) {
  const c = getChartColors()
  const map = { '2023': c[3], '2024': c[1], '2025': c[2] }
  return map[ano] || c[4]
}

function handleThemeChange(themeId) {
  currentTheme.value = themeId   // reatividade cuida do resto — sem setTimeout
}

// Controle de ano
const selectedYear = ref('2024')
const availableYears = ['2023', '2024', '2025']

// Dados extras
const dashboardExtras = ref({
  totalGeral: 0,
  totalOperadoras: 0,
  cachePorAno: {}  // Cache para não perder dados ao trocar de ano
})

// Dados de comparação temporal
const evolucaoAnual = ref({})

// Formatação
const formatCompact = (value) => {
  if (value >= 1000000000) {
    return `R$ ${(value / 1000000000).toFixed(2)} Bi`
  } else if (value >= 1000000) {
    return `R$ ${(value / 1000000).toFixed(2)} Mi`
  } else if (value >= 1000) {
    return `R$ ${(value / 1000).toFixed(2)} Mil`
  }
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}

const formatCurrency = (val) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val)

// Dados do dashboard
const dashboardData = computed(() => {
  if (ranking.value.length === 0) {
    return { totalGastos: 0, totalOperadoras: 0, mediaGastos: 0, concentracao: 0 }
  }

  const total = dashboardExtras.value.totalGeral ||
                ranking.value.reduce((sum, item) => sum + item.valor_real, 0)

  const top3 = ranking.value.slice(0, 3).reduce((sum, item) => sum + item.valor_real, 0)
  
  // ✅ CORREÇÃO: usar totalOperadoras da API, não ranking.length
  const totalOperadoras = dashboardExtras.value.totalOperadoras || ranking.value.length

  return {
    totalGastos: total,
    totalOperadoras: totalOperadoras,  // ← ERA: ranking.value.length
    mediaGastos: total / Math.max(totalOperadoras, 1),
    concentracao: total > 0 ? ((top3 / total) * 100).toFixed(1) : 0
  }
})

// Curto nome da operadora (para gráficos)
const getShortName = (name) => {
  if (!name) return 'N/A'
  const words = name.split(' ')
  if (words.length <= 3) return name
  return words.slice(0, 3).join(' ')
}

// ==================== GRÁFICO 1: Ranking do Ano ====================
const barChartData = computed(() => {
  const colors = getChartColors()
  return {
    labels: ranking.value.map(item => getShortName(item['Razao Social'])),
    datasets: [{
      label: 'Gastos Anuais (R$ Bilhões)',
      data: ranking.value.map(item => (item.valor_real / 1000000000).toFixed(2)),
      backgroundColor: ranking.value.map((_, idx) => getOperadoraColor(idx)),
      borderColor: ranking.value.map((_, idx) => getOperadoraColor(idx)),
      borderWidth: 2
    }]
  }
})

const barChartOptions = computed(() => {
  const colors = getChartColors()
  return {
    indexAxis: 'y',
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context) => {
            const billions = context.parsed.x
            return `R$ ${billions} Bi (R$ ${(billions * 1000000000).toLocaleString('pt-BR', { minimumFractionDigits: 2 })})`
          }
        }
      }
    },
    scales: {
      x: {
        beginAtZero: true,
        title: { 
          display: true, 
          text: 'Gastos Anuais (R$ Bilhões)', 
          font: { size: 14, weight: 'bold' },
          color: colors.text
        },
        ticks: { 
          callback: (value) => `R$ ${value} Bi`,
          color: colors.textMuted
        },
        grid: { color: colors.border }
      },
      y: { 
        ticks: { 
          font: { size: 11 }, 
          autoSkip: false,
          color: colors.text
        },
        grid: { color: colors.border }
      }
    },
    maintainAspectRatio: true
  }
})

// ==================== GRÁFICO 2: Market Share (Pie) ====================
const pieChartData = computed(() => {
  if (ranking.value.length === 0) return { labels: [], datasets: [] }
  const colors = getChartColors()

  const total = dashboardExtras.value.totalGeral ||
                ranking.value.reduce((sum, item) => sum + item.valor_real, 0)

  const top5 = ranking.value.slice(0, 5)
  const top5Total = top5.reduce((sum, item) => sum + item.valor_real, 0)
  const outrasTotal = total - top5Total

  const labels = top5.map(item => getShortName(item['Razao Social']))
  const values = top5.map(item => item.valor_real)

  if (outrasTotal > 0) {
    labels.push('Outras Operadoras')
    values.push(outrasTotal)
  }

  return {
    labels: labels,
    datasets: [{
      data: values.map(v => (v / total * 100).toFixed(1)),
      backgroundColor: [
        colors[1], colors[2], colors[3], colors[4], colors[5], colors.other
      ],
      borderColor: colors.border,
      borderWidth: 2
    }]
  }
})

const pieChartOptions = computed(() => {
  const colors = getChartColors()
  return {
    plugins: {
      legend: {
        position: 'right',
        labels: {
          font: { size: 11 },
          padding: 12,
          boxWidth: 15,
          color: colors.text
        }
      },
      tooltip: {
        callbacks: {
          label: (context) => `${context.label}: ${context.parsed}%`
        }
      }
    },
    maintainAspectRatio: true
  }
})

// ==================== GRÁFICO 3: Evolução Anual ====================
const evolucaoAnualData = computed(() => {
  const anos = availableYears.filter(ano => evolucaoAnual.value[ano])
  return {
    labels: anos,
    datasets: [{
      label: 'Gastos Totais (R$ Bi)',
      data: anos.map(ano => (evolucaoAnual.value[ano] / 1000000000).toFixed(2)),
      backgroundColor: anos.map(ano => getYearColor(ano)),
      borderColor: anos.map(ano => getYearColor(ano)),
      borderWidth: 2
    }]
  }
})

const evolucaoAnualOptions = computed(() => {
  const colors = getChartColors()
  return {
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (c) => `R$ ${c.parsed.y} Bi` } }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: { display: true, text: 'R$ Bilhões', font: { size: 12, weight: 'bold' }, color: colors.text },
        ticks: { callback: (v) => `R$ ${v} Bi`, color: colors.textMuted },
        grid: { color: colors.border }
      },
      x: {
        title: { display: true, text: 'Ano', font: { size: 12 }, color: colors.text },
        ticks: { color: colors.text }
      }
    },
    maintainAspectRatio: true
  }
})

// ==================== GRÁFICO 4: Comparação Temporal Top 5 ====================
const comparacaoTemporalData = computed(() => {
  const operadorasSet = new Set()
  const dadosPorAno = {}
  availableYears.forEach(ano => {
    if (evolucaoAnual.value[ano + '_top5']) {
      dadosPorAno[ano] = evolucaoAnual.value[ano + '_top5']
      evolucaoAnual.value[ano + '_top5'].forEach(item => {
        operadorasSet.add(item.razao_social)
      })
    }
  })
  if (operadorasSet.size === 0) return { labels: [], datasets: [] }
  const operadoras = Array.from(operadorasSet).slice(0, 5)
  return {
    labels: operadoras.map(op => getShortName(op)),
    datasets: availableYears
      .filter(ano => dadosPorAno[ano])
      .map(ano => ({
        label: ano,
        data: operadoras.map(op => {
          const item = dadosPorAno[ano].find(i => i.razao_social === op)
          return item ? (item.valor_total / 1000000000).toFixed(2) : 0
        }),
        backgroundColor: getYearColor(ano),
        borderColor: getYearColor(ano),
        borderWidth: 2
      }))
  }
})

const comparacaoTemporalOptions = computed(() => {
  const colors = getChartColors()
  return {
    plugins: {
      legend: {
        position: 'top',
        labels: { font: { size: 12 }, padding: 15, boxWidth: 15, color: colors.text }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: { display: true, text: 'R$ Bilhões', font: { size: 12, weight: 'bold' }, color: colors.text },
        ticks: { callback: (v) => `R$ ${v} Bi`, color: colors.textMuted },
        grid: { color: colors.border }
      },
      x: {
        title: { display: true, text: 'Operadora', font: { size: 12 }, color: colors.text },
        ticks: { color: colors.textMuted }
      }
    },
    maintainAspectRatio: true
  }
})

// ==================== GRÁFICO 5: Concentração ====================
const concentrationChartData = computed(() => {
  if (ranking.value.length === 0) return { labels: [], datasets: [] }
  const colors = getChartColors()
  const total = dashboardExtras.value.totalGeral ||
                ranking.value.reduce((sum, item) => sum + item.valor_real, 0)
  let accumulated = 0
  const accumulatedData = ranking.value.map(item => {
    accumulated += item.valor_real
    return ((accumulated / total) * 100).toFixed(1)
  })
  return {
    labels: ranking.value.map((_, idx) => `Top ${idx + 1}`),
    datasets: [
      {
        label: 'Concentração Acumulada (%)',
        data: accumulatedData,
        backgroundColor: colors[1] + 'B3', // 70% opacity
        borderColor: colors[1],
        borderWidth: 2,
        order: 2
      },
      {
        label: 'Linha de Pareto (80%)',
        data: Array(ranking.value.length).fill(80),
        type: 'line',
        borderColor: colors.danger,
        borderWidth: 2,
        borderDash: [10, 5],
        pointRadius: 0,
        fill: false,
        order: 1
      }
    ]
  }
})

const concentrationChartOptions = computed(() => {
  const colors = getChartColors()
  return {
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: { boxWidth: 12, padding: 10, font: { size: 11 }, usePointStyle: true, color: colors.text }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        title: { display: true, text: 'Percentual Acumulado (%)', font: { size: 14, weight: 'bold' }, color: colors.text },
        ticks: { callback: (v) => `${v}%`, color: colors.textMuted },
        grid: { color: colors.border }
      },
      x: {
        title: { display: true, text: 'Posição no Ranking', font: { size: 12 }, color: colors.text },
        ticks: { color: colors.textMuted }
      }
    }
  }
})

// ==================== FUNÇÕES DE DADOS ====================

function handleEnter(event) {
  event.preventDefault()
  doSearch(1)
}

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
    alert("Erro na API de busca")
    console.error(e)
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
      ranking: data.ranking ? data.ranking.map(item => ({
        'Razao Social': item.razao_social,
        'valor_real': item.valor_total
      })) : [],
      totalGeral: data.total_geral || 0,
      totalOperadoras: data.total_operadoras || 0,
      top5: data.ranking ? data.ranking.slice(0, 5) : []
    }

    // Guardar no cache para acesso rápido
    if (resultado.totalGeral > 0) {
      dashboardExtras.value.cachePorAno[periodo] = {
        totalGeral: resultado.totalGeral,
        totalOperadoras: resultado.totalOperadoras
      }
    }

    return resultado
  } catch (e) {
    console.error('Erro ao buscar analytics:', e)
    return null
  }
}

async function fetchEvolucaoAnual() {
  // Buscar total de cada ano em paralelo
  const promises = availableYears.map(ano =>
    fetch(`${API_BASE}/api/v1/analytics/gastos?periodo=${ano}&top=5`)
      .then(res => res.json())
      .catch(() => null)
  )

  const results = await Promise.all(promises)

  const evolucao = {}
  results.forEach((data, idx) => {
    if (data && data.total_geral) {
      const ano = availableYears[idx]
      evolucao[ano] = data.total_geral
      evolucao[ano + '_top5'] = data.ranking || []
    }
  })

  return evolucao
}

async function onYearChange() {
  const ano = selectedYear.value
  
  // Resetar dados visuais
  ranking.value = []
  dashboardExtras.value.totalGeral = 0
  dashboardExtras.value.totalOperadoras = 0

  // Se tiver em cache, aplicar imediatamente (sem delay)
  const cached = dashboardExtras.value.cachePorAno[ano]
  if (cached) {
    dashboardExtras.value.totalGeral = cached.totalGeral
    dashboardExtras.value.totalOperadoras = cached.totalOperadoras
  }

  // Recarregar dados frescos da view atual
  if (view.value === 'ranking') {
    await loadRanking()
  } else if (view.value === 'dashboard') {
    await loadDashboard()
  }
}

// ==================== RANKING ====================
async function loadRanking() {
  view.value = 'ranking'
  loadingRank.value = true

  try {
    const data = await fetchAnalyticsData(selectedYear.value)
    if (data && data.ranking.length > 0) {
      ranking.value = data.ranking
      
      // ✅ CORRIGIDO: Atualizar AMBOS os valores
      if (data.totalGeral > 0) {
        dashboardExtras.value.totalGeral = data.totalGeral
      }
      if (data.totalOperadoras > 0) {
        dashboardExtras.value.totalOperadoras = data.totalOperadoras
      }
    }
  } catch (e) {
    console.error(e)
    alert("Erro ao carregar ranking")
  } finally {
    loadingRank.value = false
  }
}

// ==================== DASHBOARD ====================
async function loadDashboard() {
  view.value = 'dashboard'
  loadingDashboard.value = true

  try {
    // Buscar dados do ano selecionado
    const data = await fetchAnalyticsData(selectedYear.value)
    if (data && data.ranking.length > 0) {
      ranking.value = data.ranking
      
      // Atualizar AMBOS os valores
      if (data.totalGeral > 0) {
        dashboardExtras.value.totalGeral = data.totalGeral
      }
      if (data.totalOperadoras > 0) {
        dashboardExtras.value.totalOperadoras = data.totalOperadoras
      }
    }

    // Buscar evolução anual (todos os anos em paralelo)
    const evolucao = await fetchEvolucaoAnual()
    if (evolucao && Object.keys(evolucao).length > 0) {
      evolucaoAnual.value = evolucao
    }
  } catch (e) {
    console.error(e)
    alert("Erro ao carregar dashboard")
  } finally {
    loadingDashboard.value = false
  }
}
</script>