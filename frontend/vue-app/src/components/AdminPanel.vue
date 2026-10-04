<template>
  <div class="admin-panel">
    <h2>⚙️ Painel de Administração</h2>
    <p class="muted">Gerenciamento do pipeline ETL e status do sistema</p>

    <!-- Status do Scheduler -->
    <div class="admin-section">
      <h3>📅 Scheduler Mensal</h3>
      <div v-if="schedulerStatus" class="status-card">
        <div class="status-row">
          <span class="status-label">Status:</span>
          <span class="status-value" :class="{ active: schedulerStatus.running }">
            {{ schedulerStatus.running ? '✅ Ativo' : '❌ Inativo' }}
          </span>
        </div>
        <div class="status-row">
          <span class="status-label">Próxima execução:</span>
          <span class="status-value highlight">
            {{ formatDateTime(schedulerStatus.next_run) }}
          </span>
        </div>
        <div class="status-row">
          <span class="status-label">Cron:</span>
          <span class="status-value">{{ schedulerStatus.cron }}</span>
        </div>
        <div class="status-row">
          <span class="status-label">Pipeline em execução:</span>
          <span class="status-value" :class="{ warning: schedulerStatus.pipeline_running }">
            {{ schedulerStatus.pipeline_running ? '⏳ Sim' : 'Não' }}
          </span>
        </div>
      </div>
      <div v-else class="loading">Carregando status...</div>
    </div>

    <!-- Controle Manual -->
    <div class="admin-section">
      <h3>🚀 Execução Manual</h3>
      <div class="control-row">
        <select v-model="selectedYear" class="year-select">
          <option value="2023">2023</option>
          <option value="2024">2024</option>
          <option value="2025">2025</option>
        </select>
        <button @click="runPipeline" :disabled="running || schedulerStatus?.pipeline_running">
          {{ running ? '⏳ Executando...' : '▶️ Executar Pipeline' }}
        </button>
        <button @click="loadHistory" :disabled="loading">
          🔄 Atualizar Histórico
        </button>
      </div>
      <p v-if="runMessage" class="run-message">{{ runMessage }}</p>
    </div>

    <!-- Histórico de Execuções -->
    <div class="admin-section">
      <h3>📋 Histórico de Execuções</h3>
      <div v-if="history.length === 0" class="empty">
        Nenhuma execução registrada ainda.
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Período</th>
            <th>Status</th>
            <th>Início</th>
            <th>Duração</th>
            <th>Registros</th>
            <th>Total Gastos</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="exec in history" :key="exec.id" :class="{ failed: exec.status === 'failed' }">
            <td>{{ exec.id }}</td>
            <td>{{ exec.periodo }}</td>
            <td>
              <span :class="'status-' + exec.status">
                {{ exec.status === 'success' ? '✅ Sucesso' : exec.status === 'failed' ? '❌ Falha' : '⏳ Rodando' }}
              </span>
            </td>
            <td>{{ formatDateTime(exec.started_at) }}</td>
            <td>{{ exec.duration_seconds ? exec.duration_seconds.toFixed(1) + 's' : '-' }}</td>
            <td>{{ exec.records_processed?.toLocaleString('pt-BR') || '-' }}</td>
            <td class="money">{{ formatCurrency(exec.total_gastos) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Uso de Disco -->
    <div class="admin-section">
      <h3>💾 Uso de Disco</h3>
      <div v-if="diskUsage" class="disk-info">
        <div class="disk-bar">
          <div class="disk-bar-fill" :style="{ width: diskUsage.used_percent + '%' }"></div>
        </div>
        <div class="disk-stats">
          <span>{{ diskUsage.used_gb }} GB / {{ diskUsage.total_gb }} GB</span>
          <span>{{ diskUsage.used_percent }}% usado</span>
        </div>
        <div class="disk-breakdown">
          <div>📦 Raw data: {{ diskUsage.breakdown.raw_data }} GB</div>
          <div>💾 Backups: {{ diskUsage.breakdown.backups }} GB</div>
          <div>📄 Logs: {{ diskUsage.breakdown.logs }} GB</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const schedulerStatus = ref(null)
const history = ref([])
const diskUsage = ref(null)
const selectedYear = ref('2024')
const running = ref(false)
const loading = ref(false)
const runMessage = ref('')

function formatDateTime(isoStr) {
  if (!isoStr) return '-'
  try {
    const d = new Date(isoStr)
    return d.toLocaleString('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    })
  } catch {
    return isoStr
  }
}

function formatCurrency(val) {
  if (!val) return '-'
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0
  }).format(val)
}

async function loadSchedulerStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/admin/scheduler-status`)
    if (res.ok) {
      schedulerStatus.value = await res.json()
    }
  } catch (e) {
    console.error('Erro ao carregar scheduler:', e)
  }
}

async function loadHistory() {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/v1/admin/pipeline-history?limit=20`)
    if (res.ok) {
      const data = await res.json()
      history.value = data.history || []
    }
  } catch (e) {
    console.error('Erro ao carregar histórico:', e)
  } finally {
    loading.value = false
  }
}

async function loadDiskUsage() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/admin/disk-usage`)
    if (res.ok) {
      diskUsage.value = await res.json()
    }
  } catch (e) {
    console.error('Erro ao carregar disco:', e)
  }
}

async function runPipeline() {
  running.value = true
  runMessage.value = ''
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/admin/run-pipeline?ano=${selectedYear.value}`,
      { method: 'POST' }
    )
    if (res.ok) {
      const data = await res.json()
      runMessage.value = `✅ ${data.message}`
      // Recarregar histórico após 12 segundos (tempo do pipeline)
      setTimeout(loadHistory, 12000)
      setTimeout(loadHistory, 3000)
    } else {
      const err = await res.json()
      runMessage.value = `❌ ${err.detail || 'Erro ao executar'}`
    }
  } catch (e) {
    runMessage.value = `❌ Erro de conexão: ${e.message}`
  } finally {
    running.value = false
  }
}

onMounted(() => {
  loadSchedulerStatus()
  loadHistory()
  loadDiskUsage()
})
</script>

<style scoped>
.admin-panel h2 { margin-top: 0; }
.admin-section {
  margin-top: 24px;
  padding: 16px;
  background: var(--bg-surface, #1a2a4e);
  border-radius: 8px;
  border: 1px solid var(--border, #2a3b63);
}
.admin-section h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: var(--text-primary, #e7eefc);
}
.status-card { display: flex; flex-direction: column; gap: 8px; }
.status-row { display: flex; justify-content: space-between; }
.status-label { color: var(--text-secondary, #a8b7d8); }
.status-value { font-weight: 600; }
.status-value.active { color: #4ade80; }
.status-value.warning { color: #fbbf24; }
.status-value.highlight { color: #60a5fa; }
.control-row { display: flex; gap: 12px; align-items: center; }
.year-select {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--border, #2a3b63);
  background: var(--bg-card, #0f1b33);
  color: var(--text-primary, #e7eefc);
}
.run-message {
  margin-top: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  background: rgba(59, 130, 246, 0.1);
  color: var(--text-primary);
}
.empty {
  text-align: center;
  padding: 24px;
  color: var(--text-secondary, #a8b7d8);
  font-style: italic;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.table th, .table td {
  padding: 8px;
  text-align: left;
  border-bottom: 1px solid var(--border, #2a3b63);
}
.table th { font-weight: 600; color: var(--text-secondary); }
.status-success { color: #4ade80; }
.status-failed { color: #f87171; }
.status-running { color: #fbbf24; }
tr.failed { background: rgba(248, 113, 113, 0.05); }
.money { font-family: monospace; text-align: right; color: #4ade80; }
.disk-bar {
  width: 100%;
  height: 24px;
  background: var(--bg-card, #0f1b33);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}
.disk-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #4ade80, #fbbf24, #f87171);
  transition: width 0.5s;
}
.disk-stats {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-family: monospace;
  font-size: 13px;
}
.disk-breakdown {
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 8px;
}
.loading { color: var(--text-secondary); font-style: italic; }
</style>