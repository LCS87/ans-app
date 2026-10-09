<template>
  <Teleport to="body">
    <div class="modal-backdrop" @click.self="$emit('close')">
      <div class="modal-card">
        <h3>📤 Upload Manual de CSV (F4.3)</h3>
        <p class="muted small">Importe bases históricas custom no formato do ETL (colunas: REG_ANS, RAZAO_SOCIAL, …).</p>

        <div class="row">
          <label>Dimensão:
            <select v-model="dimensao">
              <option value="gastos">Gastos Assistenciais</option>
              <option value="financeira">Financeira</option>
              <option value="operacional">Operacional</option>
              <option value="estrutura">Estrutura</option>
            </select>
          </label>
          <label>Período:
            <input type="text" v-model="periodo" placeholder="2024" maxlength="6" />
          </label>
        </div>

        <div class="dropzone" :class="{ hover: dragging }"
             @dragover.prevent="dragging = true" @dragleave="dragging = false"
             @drop.prevent="onDrop" @click="$refs.file.click()">
          <input ref="file" type="file" accept=".csv" hidden @change="onPick" />
          <div v-if="!fileObj">Arraste um .csv aqui ou clique para selecionar</div>
          <div v-else><b>{{ fileObj.name }}</b> ({{ (fileObj.size / 1024).toFixed(1) }} KB)</div>
        </div>

        <div v-if="result" class="ok">✅ {{ result }}</div>
        <div v-if="error" class="alert">⚠️ {{ error }}</div>

        <div class="actions">
          <button class="btn-primary" :disabled="!fileObj || busy" @click="upload">
            {{ busy ? 'Enviando…' : 'Enviar e carregar' }}
          </button>
          <button class="btn-ghost" @click="$emit('close')">Fechar</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api'

defineEmits(['close'])

const dimensao = ref('gastos')
const periodo = ref('2024')
const fileObj = ref(null)
const dragging = ref(false)
const busy = ref(false)
const result = ref('')
const error = ref('')

function onPick(e) { fileObj.value = e.target.files[0] || null }
function onDrop(e) {
  dragging.value = false
  const f = e.dataTransfer.files?.[0]
  if (f && f.name.toLowerCase().endsWith('.csv')) fileObj.value = f
}

async function upload() {
  if (!fileObj.value) return
  busy.value = true
  result.value = ''
  error.value = ''
  try {
    const res = await api.uploadCsv(fileObj.value)
    result.value = res.message || `Importados ${res.linhas ?? '?'} registros.`
  } catch (e) {
    error.value = e.message
  } finally { busy.value = false }
}
</script>

<style scoped>
.modal-backdrop { position: fixed; inset: 0; background: rgba(15,23,42,.55); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px; }
.modal-card { background: #fff; border-radius: 16px; max-width: 520px; width: 100%; padding: 24px; box-shadow: 0 20px 60px rgba(0,0,0,.3); }
.row { display: flex; gap: 14px; margin: 14px 0; }
.row label { display: flex; flex-direction: column; font-size: 12px; gap: 4px; color: #64748b; }
select, input[type=text] { padding: 7px 10px; border-radius: 8px; border: 1px solid #cbd5e1; }
.dropzone { border: 2px dashed #94a3b8; border-radius: 12px; padding: 32px; text-align: center; cursor: pointer; color: #475569; }
.dropzone.hover { border-color: #2563eb; background: #eff6ff; }
.ok { background: #f0fdf4; color: #166534; padding: 10px 14px; border-radius: 8px; margin-top: 12px; }
.alert { background: #fef2f2; color: #b91c1c; padding: 10px 14px; border-radius: 8px; margin-top: 12px; }
.actions { display: flex; gap: 10px; margin-top: 18px; }
.btn-primary { background: #1f4d3a; color: #fff; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-primary:disabled { opacity: .5; cursor: not-allowed; }
.btn-ghost { background: transparent; border: 1px solid #cbd5e1; padding: 10px 18px; border-radius: 8px; cursor: pointer; }
.small { font-size: 12px; }
</style>
