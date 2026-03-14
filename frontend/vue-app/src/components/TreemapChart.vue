<template>
  <div class="treemap-container">
    <div 
      v-for="(item, idx) in sortedData" 
      :key="idx"
      class="treemap-item"
      :style="getItemStyle(item)"
      :title="`${item.label}: ${formatCurrency(item.value)} (${item.percentage}%)`"
    >
      <div class="treemap-label" :class="{ 'dark-bg': isDarkBackground(item) }">
        <div class="treemap-name">{{ item.shortLabel }}</div>
        <div class="treemap-value">{{ item.percentage }}%</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: {
    type: Array,
    required: true
  }
})

const sortedData = computed(() => {
  return [...props.data].sort((a, b) => b.value - a.value)
})

const getItemStyle = (item) => {
  const percentage = item.percentage
  
  return {
    flex: `${percentage} 1 0%`,
    backgroundColor: item.color,
    minWidth: percentage > 5 ? '80px' : '40px',
    minHeight: '60px'
  }
}

// Determina se o fundo é escuro para ajustar contraste do texto
const isDarkBackground = (item) => {
  // Cores escuras que precisam de texto branco
  const darkColors = ['#2C5282', '#4A5568', '#2B6CB0', '#2D3748']
  return darkColors.includes(item.color)
}

const formatCurrency = (value) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value)
}
</script>

<style scoped>
.treemap-container {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  height: 100%;
  align-content: flex-start;
}

.treemap-item {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid rgba(255, 255, 255, 0.1);
}

.treemap-item:hover {
  transform: scale(1.05);
  border-color: rgba(255, 255, 255, 0.6);
  z-index: 10;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.treemap-label {
  text-align: center;
  font-size: 11px;
  line-height: 1.3;
  color: rgba(0, 0, 0, 0.8);
  text-shadow: 0 1px 2px rgba(255, 255, 255, 0.3);
}

.treemap-label.dark-bg {
  color: rgba(255, 255, 255, 0.95);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.treemap-name {
  font-weight: bold;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.treemap-value {
  font-size: 14px;
  font-weight: bold;
}

.treemap-label.dark-bg .treemap-value {
  color: rgba(255, 255, 255, 1);
}
</style>
