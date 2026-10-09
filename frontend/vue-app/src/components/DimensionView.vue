<template>
  <div class="dimension-view">
    <!-- Filtros avançados (F3.4) -->
    <div class="filters row">
      <label>Modalidade
        <select v-model="filters.modalidade">
          <option value="">Todas</option>
          <option v-for="m in modalidades" :key="m" :value="m">{{ m }}</option>
        </select>
      </label>
      <label>UF
        <select v-model="filters.uf">
          <option value="">Todas</option>
          <option v-for="u in ufs" :key="u" :value="u">{{ u }}</option>
        </select>
      </label>
      <label>Região
        <select v-model="filters.regiao">
          <option value="">Todas</option>
          <option v-for="r in regioes" :key="r" :value="r">{{ r }}</option>
        </select>
      </label>
      <button class="btn-ghost" @click="clearFilters" v-if="hasFilters">✕ Limpar</button>
      <span class="spacer"></span>
      <button class="btn-export" @click="$emit('export', 'pdf')">📥 PDF</button>
      <button class="btn-export" @click="$emit('export', 'excel')">📥 Excel</button>
    </div>

    <div v-if="error" class="alert">⚠️ {{ error }}</div>
    <SkeletonChart v-if="loading" />

    <template v-else-if="data">
      <!-- KPIs da dimensão -->
      <div class="stats-grid">
        <div class="stat-card" v-for="(v, col) in data.totais" :key="col">
          <div class="stat-value">{{ fmtCompact(v) }}</div>
          <div class="stat-label">{{ labelFor(col) }}</div>
        </div>
      </div>

      <!-- Gráfico principal: Top 10 pela métrica de ordenação -->
      <div class="chart-card chart-card-wide">
        <h3>{{ data.icon }} Top 10 — {{ primaryLabel }} ({{ data.periodo }})</h3>
        <BarChart v-if="data.ranking.length" :data="barData" :options="barOptions" />
        <p v-else class="muted">Sem dados para este período/filtro.</p>
      </div>

      <!-- Tabela detalhada com badges de outlier (F3.3) e drill-down (F4.4) -->
      <table class="table">
        <thead>
          <tr>
            <th>#</th>
            <th>Operadora</th>
            <th>UF</th>
            <th v-for="col in columns" :key="col" style="text-align:right">{{ labelFor(col) }}</th>
            <th v-for="agg in aggregateNames" :key="agg" style="text-align:right">{{ agg }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in data.ranking" :key="row.registro_ans" @click="$emit('detail', row)" class="clickable">
            <td>{{ row.posicao }}</td>
            <td>
              <div class="op-name">
                {{ row.razao_social }}
                <span v-if="row.outlier" class="badge-outlier" title="Outlier IQR por porte">⚠️ Outlier</span>
              </div>
              <div class="muted small">{{ row.registro_ans }} · {{ row.modalidade || '—' }}</div>
            </td>
            <td>{{ row.u || row.uf || '—' }}</td>
            <td v-for="col in columns" :key="col" class="num">{{ fmtCompact(row.valores[col]) }}</td>
            <td v-for="agg in aggregateNames" :key="agg" class="num pct">{{ fmtPercent(row.agregados[agg]) }}</td>
          </tr>
        </tbody>
      </table>
      <p class="muted small">Clique em uma operadora para ver a timeline histórica (3 anos).</p>
    </template>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import BarChart from './BarChart.vue'
import SkeletonChart from './SkeletonChart.vue'
import { api, fmtCompact, fmtPercent } from '../api'

const props = defineProps({
  dim: { type: String, required: true },       // financeira | operacional | estrutura
  periodo: { type: String, required: true },
})
defineEmits(['export', 'detail'])

const data = ref(null)
const loading = ref(false)
const error = ref('')
const filters = reactive({ modalidade: '', uf: '', regiao: '' })

const hasFilters = computed(() => Object.values(filters).some(Boolean))
const columns = computed(() => {
  if (!data.value) return []
  const first = data.value.ranking[0]
  return first ? Object.keys(first.valores || {}) : Object.keys(data.value.totais || {})
})
const aggregateNames = computed(() => {
  const first = data.value?.ranking?.[0]
  return first ? Object.keys(first.agregados || {}) : []
})
const primaryCol = computed(() => columns.value[0])
const primaryLabel = computed(() => labelFor(primaryCol.value))

const LABELS = {
  receita: 'Receita (31)', lucro: 'Lucro (25)', patrimonio: 'Patrimônio Líquido (256)',
  caixa: 'Caixa (12)', obrigacoes_trabalhistas: 'Obrigações (21)', fornecedores: 'Fornecedores (23)',
  sinistros: 'Sinistros (41)', dividas: 'Dívidas (21+23)',
  despesas_administrativas: 'Despesas Adm. (46)', pessoal: 'Pessoal (461)',
  judiciais: 'Judiciais (468)', provisoes: 'Provisões (44)', glosas: 'Glosas',
  investimentos: 'Investimentos (132)', imobilizado: 'Imobilizado (133)',
  intangivel: 'Intangível (134)', goodwill: 'Goodwill', it_softwares: 'TI/Softwares',
  gasto_total: 'Gastos Assistenciais (41)',
}
function labelFor(col) { return LABELS[col] || col }

const modalidades = ['Medicina de Grupo', 'Cooperativa Médica', 'Odontologia de Grupo', 'Autogestão', 'Filantropia', 'Empresa Comercial de Planos de Assistência à Saúde']
const ufs = ['SP', 'RJ', 'MG', 'RS', 'PR', 'SC', 'BA', 'DF', 'ES', 'GO', 'PE', 'CE', 'PA', 'AM', 'PB', 'RN', 'AL', 'MA', 'MT', 'MS', 'SE', 'PI', 'TO', 'RO', 'AC', 'AP', 'RR']
const regioes = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']

function clearFilters() { filters.modalidade = ''; filters.uf = ''; filters.regiao = '' }

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.dimension(props.dim, props.periodo, {
      top: 20, ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
    })
  } catch (e) {
    error.value = `Erro ao carregar ${props.dim}: ${e.message}`
    data.value = null
  } finally { loading.value = false }
}

watch(() => [props.dim, props.periodo], load, { immediate: true })
watch(filters, load)

// Gráfico horizontal Top 10
const barData = computed(() => {
  if (!data.value) return { labels: [], datasets: [] }
  const top = data.value.ranking.slice(0, 10)
  return {
    labels: top.map(r => r.razao_social.split(' ').slice(0, 3).join(' ')),
    datasets: [{
      label: primaryLabel.value,
      data: top.map(r => Number(((r.valores[primaryCol.value] || 0) / 1e6).toFixed(1))),
      backgroundColor: top.map(r => (r.outlier ? '#f87171' : '#3b82f6')),
      borderRadius: 4,
    }],
  }
})
const barOptions = computed(() => ({
  indexAxis: 'y',
  plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => `R$ ${ctx.parsed.x} Mi` } } },
  scales: { x: { title: { display: true, text: 'R$ Milhões' }, beginAtZero: true } },
}))
</script>

<style scoped>
.filters { display: flex; gap: 12px; align-items: end; flex-wrap: wrap; margin-bottom: 16px; }
.filters label { display: flex; flex-direction: column; font-size: 12px; color: var(--text-muted, #64748b); gap: 4px; }
.filters select { padding: 6px 10px; border-radius: 8px; border: 1px solid #cbd5e1; background: #fff; min-width: 140px; }
.spacer { flex: 1; }
.btn-export { background: #1f4d3a; color: #fff; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-export:hover { opacity: .9; }
.btn-ghost { background: transparent; border: 1px solid #cbd5e1; padding: 8px 12px; border-radius: 8px; cursor: pointer; }
.alert { background: #fef2f2; color: #b91c1c; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; }
.badge-outlier { background: #fef3c7; color: #92400e; font-size: 11px; padding: 2px 8px; border-radius: 999px; margin-left: 8px; font-weight: 600; }
.clickable { cursor: pointer; }
.clickable:hover { background: rgba(59, 130, 246, .06); }
.op-name { font-weight: 600; }
.num { text-align: right; font-family: monospace; }
.pct { color: #2563eb; }
.small { font-size: 12px; }
</style>
