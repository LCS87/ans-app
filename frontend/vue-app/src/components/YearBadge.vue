<template>
  <span :class="['year-badge', statusClass]">
    <span class="badge-icon">{{ icon }}</span>
    <span class="badge-text">{{ year }}</span>
    <span v-if="showQuarter" class="badge-quarter">{{ quarters }}/4T</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  year: { type: [String, Number], required: true },
  quarters: { type: Number, default: 4 },
  hasAnsgap: { type: Boolean, default: false }
})

const statusClass = computed(() => {
  if (props.quarters === 4 && !props.hasAnsgap) return 'badge-complete'
  if (props.hasAnsgap) return 'badge-gap'
  if (props.quarters >= 2 && props.quarters < 4) return 'badge-partial'
  return 'badge-incomplete'
})

const icon = computed(() => {
  if (props.quarters === 4 && !props.hasAnsgap) return '✅'
  if (props.hasAnsgap) return '⚠️'
  return '🕒'
})

const showQuarter = computed(() => props.quarters < 4 && !props.hasAnsgap)
</script>

<style scoped>
.year-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid var(--border, #e2e8f0);
  transition: all 0.2s;
  font-variant-numeric: tabular-nums;
}
.badge-complete { background: rgba(79, 174, 134, 0.15); color: #22c55e; border-color: #22c55e; }
.badge-partial  { background: rgba(212, 169, 74, 0.15); color: #eab308; border-color: #eab308; }
.badge-gap      { background: rgba(217, 113, 94, 0.15); color: #ef4444; border-color: #ef4444; }
.badge-incomplete { background: rgba(167, 176, 163, 0.15); color: #94a3b8; }
.badge-icon { font-size: 12px; }
.badge-quarter {
  font-size: 11px; opacity: 0.8;
  padding-left: 6px; border-left: 1px solid currentColor;
}
</style>