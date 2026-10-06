<template>
  <div class="theme-selector">
    <label class="theme-label">🎨 Tema:</label>
    <div class="theme-buttons">
      <button
        v-for="theme in themes"
        :key="theme.id"
        :class="{ active: currentTheme === theme.id }"
        @click="setTheme(theme.id)"
        :title="theme.name"
        class="theme-btn"
      >
        <span class="theme-icon">{{ theme.icon }}</span>
        <span class="theme-name">{{ theme.shortName }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const emit = defineEmits(['theme-change'])

const themes = [
  { id: 'light-blue', name: 'Claro (Azul)', shortName: 'Claro', icon: '☀️' },
  { id: 'dark-blue', name: 'Escuro (Azul)', shortName: 'Escuro', icon: '🌙' },
  { id: 'light-gold', name: 'Institucional Claro', shortName: 'Gold', icon: '🏛️' },
  { id: 'dark-gold', name: 'Institucional Escuro', shortName: 'Night', icon: '🌑' },
]

const currentTheme = ref('light-blue')

function setTheme(themeId) {
  currentTheme.value = themeId
  localStorage.setItem('theme', themeId)
  document.documentElement.setAttribute('data-theme', themeId)
  emit('theme-change', themeId)
}

onMounted(() => {
  const saved = localStorage.getItem('theme') || 'light-blue'
  setTheme(saved)
})
</script>

<style scoped>
.theme-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.theme-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.theme-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.theme-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.2s;
}

.theme-btn:hover {
  border-color: var(--accent);
  transform: translateY(-1px);
}

.theme-btn.active {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.theme-icon {
  font-size: 14px;
}

.theme-name {
  font-size: 12px;
}
</style>