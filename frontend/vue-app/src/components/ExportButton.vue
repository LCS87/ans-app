<template>
  <button @click="exportCSV" class="btn-export" :disabled="!data || data.length === 0">
    📥 Exportar CSV
  </button>
</template>

<script setup>
const props = defineProps({
  data: { type: Array, default: () => [] },
  filename: { type: String, default: 'operadoras.csv' }
})

function exportCSV() {
  if (!props.data?.length) return

  const cols = Object.keys(props.data[0]).filter(k => k !== 'score')
  const header = cols.join(';')
  
  const rows = props.data.map(row => 
    cols.map(col => {
      const val = row[col] ?? ''
      const str = String(val).replace(/"/g, '""')
      return str.includes(';') || str.includes('"') ? `"${str}"` : str
    }).join(';')
  )
  
  const csv = '\uFEFF' + [header, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = props.filename
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.btn-export {
  padding: 10px 16px;
  background: #22c55e;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.2s;
}
.btn-export:hover:not(:disabled) {
  background: #16a34a;
  transform: translateY(-1px);
}
.btn-export:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>