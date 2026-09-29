<template>
  <button @click="toggleTheme">{{ isDark ? '☀️ Light' : '🌙 Dark' }}</button>
</template>
<script setup>
import { ref } from 'vue';
const isDark = ref(true)
const toggleTheme = () => {
  isDark.value = !isDark.value
  document.body.classList.toggle('dark', isDark.value)
  document.body.classList.toggle('light', !isDark.value)
}
</script>
