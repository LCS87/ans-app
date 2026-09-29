<template>
  <div class="skeleton-chart" aria-label="Carregando gráfico">
    <div class="bar" v-for="i in 5" :key="i" />
  </div>
</template>
<style scoped>
.skeleton-chart { display: flex; gap: 8px; height: 120px; align-items: flex-end; }
.bar { width: 24px; background: #e0e0e0; border-radius: 4px; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
