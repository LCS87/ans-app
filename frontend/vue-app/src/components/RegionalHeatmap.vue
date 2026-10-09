<template>
  <div class="regional-view">
    <SkeletonChart v-if="loading" />
    <div v-else-if="error" class="alert">⚠️ {{ error }}</div>
    <template v-else-if="data && data.ufs.length">
      <div class="row" style="margin-bottom:12px">
        <label style="font-weight:600">Métrica:
          <select v-model="metric" @change="load">
            <option value="gasto_total">Gastos Assistenciais</option>
            <option value="receita">Receita</option>
            <option value="lucro">Lucro</option>
            <option value="caixa">Caixa</option>
            <option value="patrimonio">Patrimônio</option>
            <option value="despesas_administrativas">Despesas Adm.</option>
          </select>
        </label>
      </div>

      <!-- Heat map "Brasil" — grade por região, cor pela intensidade do valor -->
      <h3>🗺️ Heat Map por UF — {{ data.periodo }}</h3>
      <div class="heatmap-grid">
        <div v-for="reg in REGIOES" :key="reg.name" class="region-block">
          <div class="region-title">{{ reg.name }}</div>
          <div class="uf-cells">
            <div
              v-for="uf in reg.ufs"
              :key="uf"
              class="uf-cell"
              :style="cellStyle(uf)"
              :title="tipFor(uf)"
            >
              <span class="uf-label">{{ uf }}</span>
              <span class="uf-value" v-if="byUf[uf]">{{ fmtCompact(byUf[uf].valor) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="legend">
        <span>Baixo</span>
        <div class="legend-bar"></div>
        <span>Alto</span>
      </div>

      <!-- Ranking de UFs -->
      <table class="table" style="margin-top:20px">
        <thead>
          <tr><th>#</th><th>UF</th><th>Região</th><th style="text-align:right">Operadoras</th><th style="text-align:right">Valor (R$)</th></tr>
        </thead>
        <tbody>
          <tr v-for="(u, i) in data.ufs.slice(0, 15)" :key="u.uf">
            <td>{{ i + 1 }}</td>
            <td><b>{{ u.uf }}</b></td>
            <td>{{ u.regiao || '—' }}</td>
            <td class="num">{{ u.operadoras }}</td>
            <td class="num">{{ fmtCompact(u.valor) }}</td>
          </tr>
        </tbody>
      </table>
    </template>
    <p v-else-if="data" class="muted">Sem dados regionais — o metadata CADOP pode não estar carregado no backend.</p>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import SkeletonChart from './SkeletonChart.vue'
import { api, fmtCompact } from '../api'

const props = defineProps({ periodo: { type: String, required: true } })

const data = ref(null)
const loading = ref(false)
const error = ref('')
const metric = ref('gasto_total')

const REGIOES = [
  { name: 'Norte', ufs: ['AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO'] },
  { name: 'Nordeste', ufs: ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'] },
  { name: 'Centro-Oeste', ufs: ['DF', 'GO', 'MT', 'MS'] },
  { name: 'Sudeste', ufs: ['ES', 'MG', 'RJ', 'SP'] },
  { name: 'Sul', ufs: ['PR', 'RS', 'SC'] },
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.regional(props.periodo, metric.value)
  } catch (e) {
    error.value = `Erro ao carregar dados regionais: ${e.message}`
  } finally { loading.value = false }
}
watch(() => props.periodo, load, { immediate: true })

const byUf = computed(() => {
  const m = {}
  ;(data.value?.ufs || []).forEach(u => { m[u.uf] = u })
  return m
})
const maxVal = computed(() => Math.max(1, ...(data.value?.ufs || []).map(u => u.valor)))

function cellStyle(uf) {
  const e = byUf.value[uf]
  if (!e || !e.valor) return { background: '#f1f5f9', color: '#94a3b8' }
  const t = Math.min(1, e.valor / maxVal.value)
  // azul escalonado
  const alpha = 0.12 + t * 0.85
  return {
    background: `rgba(37, 99, 235, ${alpha.toFixed(2)})`,
    color: t > 0.5 ? '#fff' : '#1e3a8a',
  }
}
function tipFor(uf) {
  const e = byUf.value[uf]
  return e ? `${uf}: ${fmtCompact(e.valor)} (${e.operadoras} operadoras)` : `${uf}: sem dados`
}
</script>

<style scoped>
.alert { background: #fef2f2; color: #b91c1c; padding: 10px 14px; border-radius: 8px; }
.heatmap-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-top: 12px; }
.region-block { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; }
.region-title { font-weight: 700; margin-bottom: 8px; font-size: 13px; text-transform: uppercase; letter-spacing: .04em; color: #475569; }
.uf-cells { display: grid; grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); gap: 6px; }
.uf-cell { border-radius: 8px; padding: 8px 6px; text-align: center; min-height: 52px; display: flex; flex-direction: column; justify-content: center; transition: transform .1s; cursor: default; }
.uf-cell:hover { transform: scale(1.05); }
.uf-label { font-weight: 800; font-size: 13px; display: block; }
.uf-value { font-size: 10px; opacity: .9; }
.legend { display: flex; align-items: center; gap: 8px; margin-top: 14px; font-size: 12px; color: #64748b; }
.legend-bar { flex: 1; height: 8px; border-radius: 4px; background: linear-gradient(to right, rgba(37,99,235,.12), rgba(37,99,235,.97)); }
.num { text-align: right; font-family: monospace; }
.row { display: flex; align-items: center; gap: 10px; }
select { padding: 6px 10px; border-radius: 8px; border: 1px solid #cbd5e1; }
</style>
