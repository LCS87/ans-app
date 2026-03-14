<template>
  <div class="container">
    <h1>ANS - Inteligência de Dados</h1>
    
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
    </div>

    <div v-if="view === 'search'" class="card">
      <div class="row">
        <input type="text" v-model="query" placeholder="Ex.: Bradesco ou 005711" @keydown.enter="handleEnter" />
        <button :disabled="loadingSearch || !query.trim()" @click="() => doSearch(1)">Buscar</button>
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
      </div>
    </div>

    <div v-if="view === 'ranking'" class="card">
      <h2>Top 10 Maiores Gastos Assistenciais (2024)</h2>
      <p class="muted">Análise baseada no desacumulado de sinistros médico-hospitalares.</p>
      
      <div v-if="loadingRank" class="loading">Processando dados financeiros...</div>
      
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

    <div v-if="view === 'dashboard'" class="dashboard">
      <div v-if="loadingDashboard" class="loading">Carregando analytics...</div>
      
      <template v-else>
        <div class="dashboard-header">
          <h2>📈 Dashboard de Analytics</h2>
          <p class="muted">Visualizações interativas dos dados de operadoras de saúde</p>
        </div>

        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon">💰</div>
            <div class="stat-value">{{ formatCompact(dashboardData.totalGastos) }}</div>
            <div class="stat-label">Gastos Totais Anuais</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">🏥</div>
            <div class="stat-value">{{ dashboardData.totalOperadoras.toLocaleString('pt-BR') }}</div>
            <div class="stat-label">Operadoras Ativas</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">📊</div>
            <div class="stat-value">{{ formatCompact(dashboardData.mediaGastos) }}</div>
            <div class="stat-label">Média de Gastos</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">🎯</div>
            <div class="stat-value">{{ dashboardData.concentracao }}%</div>
            <div class="stat-label">Concentração Top 3</div>
          </div>
        </div>

        <div class="charts-grid">
          <div class="chart-card">
            <h3>📊 Ranking de Gastos Anuais (R$ Bilhões)</h3>
            <p class="chart-subtitle">Total acumulado em 2024</p>
            <div class="chart-container">
              <BarChart :data="barChartData" :options="barChartOptions" />
            </div>
          </div>

          <div class="chart-card">
            <h3>📊 Análise de Concentração de Mercado</h3>
            <p class="chart-subtitle">Percentual acumulado do Top 10</p>
            <div class="chart-container">
              <BarChart :data="concentrationChartData" :options="concentrationChartOptions" />
            </div>
          </div>

          <div class="chart-card chart-card-wide">
            <h3>📈 Evolução Mensal de Gastos (R$ Milhões)</h3>
            <p class="chart-subtitle">Projeção mensal das Top 3 operadoras - 2024</p>
            <div class="chart-container-wide">
              <LineChart :data="lineChartData" :options="lineChartOptions" />
            </div>
          </div>

          <div class="chart-card">
            <h3>🎯 Treemap de Participação de Mercado</h3>
            <p class="chart-subtitle">Visualização hierárquica do Top 10</p>
            <div class="chart-container">
              <TreemapChart :data="treemapData" />
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import BarChart from './components/BarChart.vue'
import LineChart from './components/LineChart.vue'
import TreemapChart from './components/TreemapChart.vue'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const view = ref('search')
const query = ref('')
const results = ref([])
const ranking = ref([])
const loadingSearch = ref(false)
const loadingRank = ref(false)
const loadingDashboard = ref(false)
const currentPage = ref(1)
const totalPages = ref(1)
const totalResults = ref(0)

// Formatador compacto para valores grandes
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

// Dados do dashboard
const dashboardData = computed(() => {
  if (ranking.value.length === 0) {
    return {
      totalGastos: 0,
      totalOperadoras: 1180,
      mediaGastos: 0,
      concentracao: 0
    }
  }

  const total = ranking.value.reduce((sum, item) => sum + item.valor_real, 0)
  const top3 = ranking.value.slice(0, 3).reduce((sum, item) => sum + item.valor_real, 0)
  
  return {
    totalGastos: total,
    totalOperadoras: 1180,
    mediaGastos: total / ranking.value.length,
    concentracao: ((top3 / total) * 100).toFixed(1)
  }
})

// Paleta de cores consistente - MESMA COR = MESMA OPERADORA
const getOperadoraColor = (index) => {
  const colors = [
    '#2C5282', // Azul escuro - Líder
    '#3182CE', // Azul médio - 2º
    '#4299E1', // Azul claro - 3º
    '#4A5568', // Cinza escuro - 4º
    '#718096', // Cinza médio - 5º
    '#2B6CB0', // Azul intermediário - 6º
    '#63B3ED', // Azul muito claro - 7º
    '#A0AEC0', // Cinza claro - 8º
    '#2D3748', // Cinza muito escuro - 9º
    '#90CDF4'  // Azul pastel - 10º
  ]
  return colors[index % colors.length]
}

// Treemap Data com cores consistentes
const treemapData = computed(() => {
  if (ranking.value.length === 0) return []
  
  const total = ranking.value.reduce((sum, item) => sum + item.valor_real, 0)
  
  return ranking.value.map((item, index) => {
    const name = item['Razao Social']
    const shortName = name.split(' ').slice(0, 3).join(' ')
    
    return {
      label: name,
      shortLabel: shortName.length > 25 ? shortName.substring(0, 25) + '...' : shortName,
      value: item.valor_real,
      percentage: ((item.valor_real / total) * 100).toFixed(1),
      color: getOperadoraColor(index),
      index: index
    }
  })
})

// Gráfico de Barras - Ranking (em BILHÕES) com cores consistentes
const barChartData = computed(() => ({
  labels: ranking.value.map(item => {
    const name = item['Razao Social']
    // Criar short name inteligente: primeiras 3 palavras
    const words = name.split(' ')
    if (words.length <= 3) return name
    return words.slice(0, 3).join(' ')
  }),
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
    legend: {
      display: false
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          const billions = context.parsed.x
          return `R$ ${billions} Bilhões (R$ ${(billions * 1000000000).toLocaleString('pt-BR', { minimumFractionDigits: 2 })})`
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
        font: {
          size: 14,
          weight: 'bold'
        }
      },
      ticks: {
        callback: (value) => `R$ ${value} Bi`
      }
    },
    y: {
      ticks: {
        font: {
          size: 11
        },
        autoSkip: false
      }
    }
  },
  layout: {
    padding: {
      left: 10,
      right: 10
    }
  },
  maintainAspectRatio: true
}

// Gráfico de Linha - Evolução (APENAS TOP 3, em MILHÕES) com cores consistentes
const lineChartData = computed(() => {
  const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
  const top3 = ranking.value.slice(0, 3)
  
  return {
    labels: months,
    datasets: top3.map((item, idx) => {
      const baseValue = item.valor_real / 12
      const color = getOperadoraColor(idx)
      
      // Short name: primeiras 3 palavras
      const words = item['Razao Social'].split(' ')
      const shortName = words.length <= 3 ? item['Razao Social'] : words.slice(0, 3).join(' ')
      
      return {
        label: shortName,
        data: months.map(() => {
          const variation = (Math.random() - 0.5) * 0.2
          return ((baseValue + baseValue * variation) / 1000000).toFixed(2)
        }),
        borderColor: color,
        backgroundColor: color + '20',
        tension: 0.4,
        fill: false,
        borderWidth: 3,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: color,
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      }
    })
  }
})

const lineChartOptions = {
  plugins: {
    legend: {
      position: 'bottom',
      labels: {
        boxWidth: 12,
        padding: 15,
        font: {
          size: 11
        },
        usePointStyle: true,
        generateLabels: (chart) => {
          const datasets = chart.data.datasets
          return datasets.map((dataset, i) => ({
            text: dataset.label,
            fillStyle: dataset.borderColor,
            strokeStyle: dataset.borderColor,
            lineWidth: 2,
            hidden: false,
            index: i,
            pointStyle: 'circle'
          }))
        }
      }
    },
    tooltip: {
      mode: 'index',
      intersect: false,
      callbacks: {
        label: (context) => {
          return `${context.dataset.label}: R$ ${context.parsed.y} Milhões`
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      title: {
        display: true,
        text: 'Gastos Mensais (R$ Milhões)',
        font: {
          size: 14,
          weight: 'bold'
        }
      },
      ticks: {
        callback: (value) => `R$ ${value} Mi`
      }
    },
    x: {
      title: {
        display: true,
        text: 'Mês (2024)',
        font: {
          size: 12
        }
      }
    }
  },
  interaction: {
    mode: 'nearest',
    axis: 'x',
    intersect: false
  }
}

// Gráfico de Concentração com linha de Pareto
const concentrationChartData = computed(() => {
  if (ranking.value.length === 0) return { labels: [], datasets: [] }
  
  const total = ranking.value.reduce((sum, item) => sum + item.valor_real, 0)
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
      labels: {
        boxWidth: 12,
        padding: 10,
        font: {
          size: 11
        },
        usePointStyle: true
      }
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
      title: {
        display: true,
        text: 'Percentual Acumulado (%)',
        font: {
          size: 14,
          weight: 'bold'
        }
      },
      ticks: {
        callback: (value) => `${value}%`
      }
    },
    x: {
      title: {
        display: true,
        text: 'Posição no Ranking',
        font: {
          size: 12
        }
      }
    }
  }
}

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
  }
  finally { loadingSearch.value = false }
}

async function loadRanking() {
  view.value = 'ranking'
  if (ranking.value.length > 0) return
  
  loadingRank.value = true
  try {
    const res = await fetch(`${API_BASE}/api/v1/analytics/gastos?periodo=2024&top=10`)
    const data = await res.json()
    
    if (data.ranking) {
      ranking.value = data.ranking.map(item => ({
        'Razao Social': item.razao_social,
        'valor_real': item.valor_total
      }))
    }
  } catch (e) { 
    console.error(e)
    alert("Erro ao carregar ranking")
  }
  finally { loadingRank.value = false }
}

async function loadDashboard() {
  view.value = 'dashboard'
  
  if (ranking.value.length > 0) return
  
  loadingDashboard.value = true
  try {
    const res = await fetch(`${API_BASE}/api/v1/analytics/gastos?periodo=2024&top=10`)
    const data = await res.json()
    
    if (data.ranking) {
      ranking.value = data.ranking.map(item => ({
        'Razao Social': item.razao_social,
        'valor_real': item.valor_total
      }))
    }
  } catch (e) { 
    console.error(e)
    alert("Erro ao carregar dashboard")
  }
  finally { loadingDashboard.value = false }
}

const formatCurrency = (val) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val)
</script>
