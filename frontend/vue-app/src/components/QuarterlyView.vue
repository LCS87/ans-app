<template>
  <div class="quarterly-view">
    <SkeletonChart v-if="loading" />
    <div v-else-if="error" class="alert">⚠️ {{ error }}</div>
    <template v-else-if="data">
      <div class="chart-card chart-card-wide">
        <h3>🔄 Sazonalidade Trimestral — {{ data.periodo }} (Top 5)</h3>
        <p class="muted">Distribuição 1T × 2T × 3T × 4T dos gastos assistenciais.</p>
        <BarChart v-if="hasData" :data="groupedData" :options="groupedOptions" />
        <p v-else class="muted">Sem dados trimestrais para este período.</p>
      </div>

      <!-- Drill-down por operadora (F3.2) -->
      <div class="row" style="margin: 16px 0;">
        <label style="font-weight:600">Drill-down:
          <select v-model="selectedReg" @change="loadDetail">
            <option value="">Consolidado (todas)</option>
            <option v-for="s in seriesList" :key="s.registro_ans" :value="s.registro_ans">
              {{ s.razao_social }}
            </option>
          </select>
        </label>
      </div>

      <div class="chart-card" v-if="detail">
        <h3>{{ detail.razao_social }} — {{ detail.registro_ans }}</h3>
        <PieChart :data="pieData" :options="pieOptions" />
        <table class="table">
          <thead><tr><th>Trimestre</th><th style="text-align:right">Valor (R$)</th><th style="text-align:right">% do ano</th></tr></thead>
          <tbody>
            <tr v-for="(v, q) in detail.trimestres" :key="q">
              <td>{{ q }}</td>
              <td class="num">{{ fmtCompact(v) }}</td>
              <td class="num">{{ detail.total ? ((v / detail.total) * 100).toFixed(1) + '%' : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import BarChart from './BarChart.vue'
import PieChart from './PieChart.vue'
import SkeletonChart from './SkeletonChart.vue'
import { api, fmtCompact } from '../api'

const props = defineProps({ periodo: { type: String, required: true } })

const data = ref(null)
const detail = ref(null)
const selectedReg = ref('')
const loading = ref(false)
const error = ref('')

const QCOLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']
const QKEYS = ['1T', '2T', '3T', '4T']

async function load() {
  loading.value = true
  error.value = ''
  detail.value = null
  selectedReg.value = ''
  try {
    data.value = await api.quarterly(props.periodo)
    // mostra consolidado
    const total = data.value.series[0]
    if (total) detail.value = total
    else if (data.value.series.length) detail.value = data.value.series[0]
  } catch (e) {
    error.value = `Erro ao carregar análise trimestral: ${e.message}`
  } finally { loading.value = false }
}
watch(() => props.periodo, load, { immediate: true })

async function loadDetail() {
  if (!selectedReg.value) {
    detail.value = data.value?.series?.[0] || null
    return
  }
  try {
    const d = await api.quarterly(props.periodo, selectedReg.value)
    detail.value = d.series[0] || null
  } catch (e) { console.error(e) }
}

const seriesList = computed(() => (data.value?.series || []).slice(0, 20))
const hasData = computed(() => (data.value?.series || []).length > 0)

// Gráfico agrupado Top 5 operadoras x trimestres
const groupedData = computed(() => {
  const top = (data.value?.series || [])
    .filter(s => s.registro_ans !== 'TOTAL')
    .sort((a, b) => b.total - a.total)
    .slice(0, 5)
  if (!top.length) return { labels: [], datasets: [] }
  return {
    labels: top.map(s => (s.razao_social || '').split(' ').slice(0, 3).join(' ')),
    datasets: QKEYS.map((q, i) => ({
      label: q,
      data: top.map(s => Number(((s.trimestres[q] || 0) / 1e6).toFixed(1))),
      backgroundColor: QCOLORS[i],
      borderRadius: 3,
    })),
  }
})
const groupedOptions = {
  plugins: { tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: R$ ${ctx.parsed.y} Mi` } } },
  scales: { y: { beginAtZero: true, stacked: false, title: { display: true, text: 'R$ Milhões' } } },
}

const pieData = computed(() => {
  if (!detail.value) return { labels: [], datasets: [] }
  return {
    labels: QKEYS,
    datasets: [{
      data: QKEYS.map(q => detail.value.trimestres[q] || 0),
      backgroundColor: QCOLORS,
    }],
  }
})
const pieOptions = {
  plugins: {
    legend: { position: 'right' },
    tooltip: { callbacks: { label: ctx => `${ctx.label}: ${fmtCompact(ctx.parsed)}` } },
  },
}
</script>

<style scoped>
.alert { background: #fef2f2; color: #b91c1c; padding: 10px 14px; border-radius: 8px; }
.num { text-align: right; font-family: monospace; }
select { padding: 6px 10px; border-radius: 8px; border: 1px solid #cbd5e1; min-width: 260px; }
.row { display: flex; align-items: center; gap: 10px; }
</style>
