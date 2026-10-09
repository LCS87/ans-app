<template>
  <Teleport to="body">
    <div class="modal-backdrop" @click.self="$emit('close')">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <h3>📜 Timeline Histórica — {{ operadora.razao_social }}</h3>
            <p class="muted small">
              Registro ANS {{ operadora.registro_ans }}
              <span v-if="info.u"> · UF {{ info.u }}</span>
              <span v-if="info.modalidade"> · {{ info.modalidade }}</span>
            </p>
          </div>
          <button class="btn-close" @click="$emit('close')">✕</button>
        </div>

        <div v-if="loading" class="muted" style="padding:24px">Carregando histórico…</div>
        <div v-else-if="error" class="alert">⚠️ {{ error }}</div>
        <template v-else-if="info.history && info.history.length">
          <BarChart :data="chartData" :options="chartOptions" />
          <table class="table" style="margin-top:16px">
            <thead>
              <tr>
                <th>Período</th><th style="text-align:right">Gastos (R$)</th>
                <th style="text-align:right">Receita</th><th style="text-align:right">Lucro</th>
                <th style="text-align:right">Patrimônio</th><th style="text-align:right">Caixa</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="h in info.history" :key="h.periodo">
                <td><b>{{ h.periodo }}</b></td>
                <td class="num">{{ fmtCompact(h.gasto_total) }}</td>
                <td class="num">{{ fmtCompact(h.receita) }}</td>
                <td class="num">{{ fmtCompact(h.lucro) }}</td>
                <td class="num">{{ fmtCompact(h.patrimonio) }}</td>
                <td class="num">{{ fmtCompact(h.caixa) }}</td>
              </tr>
            </tbody>
          </table>
        </template>
        <p v-else class="muted" style="padding:16px">Sem histórico disponível para esta operadora.</p>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import BarChart from './BarChart.vue'
import { api, fmtCompact } from '../api'

const props = defineProps({ operadora: { type: Object, required: true } })
defineEmits(['close'])

const info = ref({})
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    info.value = await api.operadoraHistory(props.operadora.registro_ans)
  } catch (e) {
    error.value = e.message === 'HTTP 404' ? 'Sem histórico para esta operadora.' : e.message
  } finally { loading.value = false }
})

const chartData = computed(() => {
  const h = info.value.history || []
  return {
    labels: h.map(x => x.periodo),
    datasets: [
      { label: 'Gastos', data: h.map(x => +(x.gasto_total / 1e6).toFixed(1)), backgroundColor: '#3b82f6' },
      { label: 'Receita', data: h.map(x => +(x.receita / 1e6).toFixed(1)), backgroundColor: '#10b981' },
      { label: 'Lucro', data: h.map(x => +(x.lucro / 1e6).toFixed(1)), backgroundColor: '#f59e0b' },
    ],
  }
})
const chartOptions = {
  plugins: { tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: R$ ${ctx.parsed.y} Mi` } } },
  scales: { y: { beginAtZero: true, title: { display: true, text: 'R$ Milhões' } } },
}
</script>

<style scoped>
.modal-backdrop { position: fixed; inset: 0; background: rgba(15, 23, 42, .55); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px; }
.modal-card { background: #fff; border-radius: 16px; max-width: 860px; width: 100%; max-height: 85vh; overflow-y: auto; padding: 24px; box-shadow: 0 20px 60px rgba(0,0,0,.3); }
.modal-header { display: flex; justify-content: space-between; align-items: start; margin-bottom: 16px; }
.btn-close { background: #f1f5f9; border: none; border-radius: 8px; width: 34px; height: 34px; cursor: pointer; font-size: 15px; }
.alert { background: #fef2f2; color: #b91c1c; padding: 10px 14px; border-radius: 8px; }
.num { text-align: right; font-family: monospace; }
.small { font-size: 12px; }
</style>
