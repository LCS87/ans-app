<template>
  <div class="container">
    <h1>ANS - Inteligência de Dados</h1>

    <ThemeToggle />
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

// Cores
const getOperadoraColor = (index) => {
  const colors = [
    '#2C5282', '#3182CE', '#4299E1', '#4A5568', '#718096',
    '#2B6CB0', '#63B3ED', '#A0AEC0', '#2D3748', '#90CDF4'
  ]
  return colors[index % colors.length]
}

const getYearColor = (ano) => {
  const colors = {
    '2023': '#718096',
    '2024': '#3182CE',
    '2025': '#48BB78'
  }
  return colors[ano] || '#A0AEC0'
}

// Curto nome da operadora (para gráficos)
const getShortName = (name) => {
  if (!name) return 'N/A'
  const words = name.split(' ')
  if (words.length <= 3) return name
  return words.slice(0, 3).join(' ')
}

// ==================== GRÁFICO 1: Ranking do Ano ====================
const barChartData = computed(() => ({
  labels: ranking.value.map(item => getShortName(item['Razao Social'])),
  datasets: [{
    label: 'Gastos Anuais (R$ Bilhões)',
    data: ranking.value.map(item => (item.valor_real / 1000000000).toFixed(2)),
    backgroundColor: ranking.value.map((_, idx) => getOperadoraColor(idx)),
    borderColor: ranking.value.map((_, idx) => getOperadoraColor(idx)),
    borderWidth: 2
  }]
}))

const barChartOptions = {
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
      title: { display: true, text: 'Gastos Anuais (R$ Bilhões)', font: { size: 14, weight: 'bold' } },
      ticks: { callback: (value) => `R$ ${value} Bi` }
    },
    y: { ticks: { font: { size: 11 }, autoSkip: false } }
  },
  layout: { padding: { left: 10, right: 10 } },
  maintainAspectRatio: true
}

// ==================== GRÁFICO 2: Market Share (Pie) ====================
const pieChartData = computed(() => {
  if (ranking.value.length === 0) return { labels: [], datasets: [] }

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
        '#2C5282', '#3182CE', '#4299E1', '#4A5568', '#718096', '#A0AEC0'
      ],
      borderColor: '#ffffff',
      borderWidth: 2
    }]
  }
})

const pieChartOptions = {
  plugins: {
    legend: {
      position: 'right',
      labels: {
        font: { size: 11 },
        padding: 12,
        boxWidth: 15
      }
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          const percent = context.parsed
          return `${context.label}: ${percent}%`
        }
      }
    }
  },
  maintainAspectRatio: true
}

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

const evolucaoAnualOptions = {
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (context) => {
          const billions = context.parsed.y
          return `R$ ${billions} Bi`
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      title: { display: true, text: 'R$ Bilhões', font: { size: 12, weight: 'bold' } },
      ticks: { callback: (value) => `R$ ${value} Bi` }
    },
    x: {
      title: { display: true, text: 'Ano', font: { size: 12 } }
    }
  },
  maintainAspectRatio: true
}

// ==================== GRÁFICO 4: Comparação Temporal Top 5 ====================
const comparacaoTemporalData = computed(() => {
  // Coletar operadoras únicas que aparecem no top 5 de qualquer ano
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

const comparacaoTemporalOptions = {
  plugins: {
    legend: {
      position: 'top',
      labels: { font: { size: 12 }, padding: 15, boxWidth: 15 }
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          return `${context.dataset.label}: R$ ${context.parsed.y} Bi`
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      title: { display: true, text: 'R$ Bilhões', font: { size: 12, weight: 'bold' } },
      ticks: { callback: (value) => `R$ ${value} Bi` }
    },
    x: {
      title: { display: true, text: 'Operadora', font: { size: 12 } }
    }
  },
  maintainAspectRatio: true
}

// ==================== GRÁFICO 5: Concentração ====================
const concentrationChartData = computed(() => {
  if (ranking.value.length === 0) return { labels: [], datasets: [] }

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
        backgroundColor: 'rgba(44, 82, 130, 0.7)',
        borderColor: 'rgba(44, 82, 130, 1)',
        borderWidth: 2,
        order: 2
      },
      {
        label: 'Linha de Pareto (80%)',
        data: Array(ranking.value.length).fill(80),
        type: 'line',
        borderColor: 'rgba(239, 68, 68, 0.8)',
        borderWidth: 2,
        borderDash: [10, 5],
        pointRadius: 0,
        fill: false,
        order: 1
      }
    ]
  }
})

const concentrationChartOptions = {
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: { boxWidth: 12, padding: 10, font: { size: 11 }, usePointStyle: true }
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          if (context.datasetIndex === 0) {
            return `${context.parsed.y}% do mercado acumulado`
          } else {
            return 'Princípio de Pareto (80/20)'
          }
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      max: 100,
      title: { display: true, text: 'Percentual Acumulado (%)', font: { size: 14, weight: 'bold' } },
      ticks: { callback: (value) => `${value}%` }
    },
    x: {
      title: { display: true, text: 'Posição no Ranking', font: { size: 12 } }
    }
  }
}

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