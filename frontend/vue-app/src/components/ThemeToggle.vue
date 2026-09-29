<template>
  <button @click="toggleTheme" class="theme-toggle">
    {{ isDark ? '☀️ Modo Claro' : '🌙 Modo Escuro' }}
  </button>
</template>

<script setup>
import { onMounted, ref } from 'vue'

const isDark = ref(true)

function toggleTheme() {
  isDark.value = !isDark.value
  const theme = isDark.value ? 'dark' : 'light'
  
  // Usa data-theme no HTML (não body.light)
  document.documentElement.setAttribute('data-theme', theme)
  localStorage.setItem('theme', theme)
}

onMounted(() => {
  const saved = localStorage.getItem('theme') || 'dark'
  isDark.value = saved === 'dark'
  document.documentElement.setAttribute('data-theme', saved)
})
</script>

<style scoped>
.theme-toggle {
  padding: 8px 16px;
  background: var(--bg-surface, #1a2a4e);
  color: var(--text-primary, #e7eefc);
  border: 1px solid var(--border, #2a3b63);
  border-radius: 8px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.3s;
  margin-bottom: 16px;
}
.theme-toggle:hover {
  transform: translateY(-1px);
}
</style>