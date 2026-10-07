<template>
  <div class="timeline">
    <div
      v-for="year in years"
      :key="year.year"
      :class="['timeline-item', { active: year.year === activeYear }]"
      @click="$emit('select', year.year)"
    >
      <div class="timeline-bar">
        <div
          class="timeline-bar-fill"
          :style="{ height: year.heightPct + '%', background: year.color }"
        ></div>
      </div>
      <div class="timeline-value">{{ formatCompact(year.total) }}</div>
      <YearBadge
        :year="year.year"
        :quarters="year.quarters"
        :hasAnsgap="year.hasAnsgap"
      />
    </div>
  </div>
</template>

<script setup>
import YearBadge from './YearBadge.vue'

defineProps({
  years: { type: Array, required: true },
  activeYear: { type: [String, Number], required: true }
})

defineEmits(['select'])

function formatCompact(value) {
  if (!value) return 'R$ 0'
  if (value >= 1e9) return `R$ ${(value / 1e9).toFixed(1)} Bi`
  if (value >= 1e6) return `R$ ${(value / 1e6).toFixed(0)} Mi`
  return `R$ ${value.toLocaleString('pt-BR')}`
}
</script>

<style scoped>
.timeline {
  display: flex; gap: 16px; justify-content: space-around;
  align-items: flex-end;
  padding: 20px 10px 10px;
  background: var(--bg-surface, #fff);
  border-radius: 12px;
  border: 1px solid var(--border, #e2e8f0);
  margin-bottom: 24px;
}
.timeline-item {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  cursor: pointer; transition: all 0.2s;
  flex: 1; max-width: 140px; padding: 8px; border-radius: 8px;
}
.timeline-item:hover { background: rgba(0,0,0,0.04); }
.timeline-item.active { background: rgba(0,0,0,0.06); box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.timeline-bar {
  width: 60px; height: 100px;
  background: var(--bg-primary, #f7f7f7);
  border-radius: 8px 8px 0 0;
  position: relative; display: flex; align-items: flex-end;
  overflow: hidden;
  border: 1px solid var(--border, #e2e8f0); border-bottom: none;
}
.timeline-bar-fill {
  width: 100%; transition: height 0.5s ease;
  border-radius: 6px 6px 0 0;
}
.timeline-value {
  font-size: 13px; font-weight: 700;
  color: var(--text-primary, #0f172a);
  font-variant-numeric: tabular-nums;
}
</style>