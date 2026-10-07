<template>
  <div v-if="show" :class="['disclaimer', disclaimerClass]">
    <span class="disclaimer-icon">{{ icon }}</span>
    <div class="disclaimer-text">
      <strong>{{ title }}</strong>
      <p>{{ message }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  year: { type: [String, Number], required: true },
  quarters: { type: Number, default: 4 },
  hasAnsgap: { type: Boolean, default: false }
})

const show = computed(() => props.hasAnsgap || props.quarters < 4)

const disclaimerClass = computed(() => props.hasAnsgap ? 'disclaimer-danger' : 'disclaimer-warning')

const icon = computed(() => props.hasAnsgap ? '⚠️' : '🕒')

const title = computed(() => {
  if (props.hasAnsgap && String(props.year) === '2024')
    return 'Lacuna estrutural na publicação ANS (2024)'
  return `Dados parciais de ${props.year}`
})

const message = computed(() => {
  if (props.hasAnsgap && String(props.year) === '2024')
    return 'A ANS não publicou as contas 411 completas das grandes operadoras (AMIL, Bradesco, etc.) em 2024. ' +
           'Os totais representam apenas o subset reportado. Para análise completa de mercado, prefira 2025.'
  if (props.quarters < 4)
    return `Apenas ${props.quarters} de 4 trimestres disponíveis. Os dados ainda não foram publicados integralmente pela ANS. ` +
           'Os valores representam o acumulado parcial do exercício.'
  return ''
})
</script>

<style scoped>
.disclaimer {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 14px 18px; border-radius: 10px;
  margin-bottom: 20px; border-left: 4px solid;
  font-size: 13px; line-height: 1.5;
}
.disclaimer-warning { background: rgba(212, 169, 74, 0.08); border-color: #eab308; }
.disclaimer-danger  { background: rgba(217, 113, 94, 0.08); border-color: #ef4444; }
.disclaimer-icon { font-size: 18px; flex-shrink: 0; margin-top: 2px; }
.disclaimer-text { flex: 1; }
.disclaimer-text strong { display: block; margin-bottom: 4px; font-size: 14px; }
.disclaimer-text p { margin: 0; opacity: 0.9; }
</style>