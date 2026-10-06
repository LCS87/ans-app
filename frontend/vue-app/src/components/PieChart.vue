<template>
  <div class="pie-chart-wrapper">
    <canvas ref="chartRef"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const props = defineProps({
  data: { type: Object, required: true },
  options: { type: Object, default: () => ({}) }
})

const chartRef = ref(null)
let chartInstance = null

const defaultOptions = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: {
      position: 'right',
      labels: {
        font: { size: 11 },
        padding: 12,
        boxWidth: 15,
        usePointStyle: true,
        pointStyle: 'circle'
      }
    },
    tooltip: {
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      padding: 12,
      callbacks: {
        label: (context) => {
          const value = context.parsed
          return `${context.label}: ${value}%`
        }
      }
    }
  }
}

function renderChart() {
  if (!chartRef.value) return
  
  if (chartInstance) {
    chartInstance.destroy()
  }
  
  const mergedOptions = {
    ...defaultOptions,
    ...props.options,
    plugins: {
      ...defaultOptions.plugins,
      ...(props.options.plugins || {})
    }
  }
  
  chartInstance = new Chart(chartRef.value, {
    type: 'pie',
    data: props.data,
    options: mergedOptions
  })
}

onMounted(() => { renderChart() })

watch(() => props.data, () => { renderChart() }, { deep: true })

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
})
</script>

<style scoped>
.pie-chart-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

canvas {
  max-width: 100%;
  max-height: 100%;
}
</style>