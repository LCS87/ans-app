<template>
  <div class="top20-view">
    <SkeletonChart v-if="loading" />
    <div v-else-if="error" class="alert">⚠️ {{ error }}</div>
    <template v-else-if="data">
      <!-- Abas internas por métrica (F3.1) -->
      <div class="metric-tabs">
        <button
          v-for="(rank, metric) in (data.rankings || {})"
          :key="metric"
          :class="{ active: activeMetric === metric }"
          @click="activeMetric = metric"
        >
          {{ METRIC_LABELS[metric] || metric }}
        </button>
      </div>

      <div class="chart-card chart-card-wide">
        <h3>🏆 Top {{ current.length }} — {{ METRIC_LABELS[activeMetric] || activeMetric }}</h3>
        <BarChart v-if="current.length" :data="barData" :options="barOptions" />
        <p v-else class="muted">Sem dados para esta métrica no período {{ periodo }}.</p>
      </div>

      <table class="table" v-if="current.length">
        <thead>
          <tr>
            <th>#</th><th>Registro ANS</th><th>Operadora</th>
            <th style="text-align:right">{{ METRIC_LABELS[activeMetric] || activeMetric }} (R$)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in current" :key="row.registro_ans" class="clickable" @click="$emit('detail', row)">
            <td>{{ i + 1 }}</td>
            <td class="mono">{{ row.registro_ans }}</td>
            <td>{{ row.razao_social }}</td>
            <td class="num">{{ fmtCompact(row.valor) }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import BarChart from './BarChart.vue'
import SkeletonChart from './SkeletonChart.vue'
import { api, fmtCompact } from '../api'

const props = defineProps({ periodo: { type: String, required: true } })
defineEmits(['detail'])

const data = ref(null)
const loading = ref(false)
const error = ref('')
const activeMetric = ref('sinistro')

const METRIC_LABELS = {
  sinistro: 'Sinistros Assistenciais', receita: 'Receita', patrimonio: 'Patrimônio Líquido',
  caixa: 'Caixa', lucro: 'Lucro',
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.topRankings(props.periodo, 20)
    const r = data.value?.rankings || {}
    if (!r[activeMetric.value] || !r[activeMetric.value].length) {
      const firstWithData = Object.keys(r).find(k => r[k]?.length > 0)
      if (firstWithData) activeMetric.value = firstWithData
    }
  } catch (e) {
    error.value = `Erro ao carregar Top 20: ${e.message}`
  } finally { loading.value = false }
}
watch(() => props.periodo, load, { immediate: true })

const current = computed(() => data.value?.rankings?.[activeMetric.value] || [])

const barData = computed(() => ({
  labels: current.value.map(r => (r.razao_social || '').split(' ').slice(0, 3).join(' ')),
  datasets: [{
    label: METRIC_LABELS[activeMetric.value],
    data: current.value.map(r => Number(((r.valor || 0) / 1e6).toFixed(1))),
    backgroundColor: '#7c3aed',
    borderRadius: 4,
  }],
}))
const barOptions = computed(() => ({
  indexAxis: 'y',
  plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => `R$ ${ctx.parsed.x} Mi` } } },
  scales: { x: { beginAtZero: true, title: { display: true, text: 'R$ Milhões' } } },
}))
</script>

<style scoped>
.metric-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
.metric-tabs button { padding: 8px 16px; border-radius: 999px; border: 1px solid #cbd5e1; background: #fff; cursor: pointer; font-weight: 500; }
.metric-tabs button.active { background: #7c3aed; color: #fff; border-color: #7c3aed; }
.alert { background: #fef2f2; color: #b91c1c; padding: 10px 14px; border-radius: 8px; }
.num { text-align: right; font-family: monospace; font-weight: 600; }
.mono { font-family: monospace; }
.clickable { cursor: pointer; }
.clickable:hover { background: rgba(124, 58, 237, .06); }
</style>
