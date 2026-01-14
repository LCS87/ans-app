<template>
  <div class="container">
    <h1>ANS - Inteligência de Dados</h1>
    
    <div class="tabs">
      <button @click="view = 'search'" :class="{ active: view === 'search' }">Busca de Operadoras</button>
      <button @click="loadRanking" :class="{ active: view === 'ranking' }">Ranking de Gastos (Top 10)</button>
    </div>

    <div v-if="view === 'search'" class="card">
      <div class="row">
        <input type="text" v-model="query" placeholder="Ex.: Bradesco ou 005711" @keydown.enter.prevent="doSearch" />
        <button :disabled="loadingSearch || !query.trim()" @click="doSearch">Buscar</button>
      </div>

      <div v-if="results.length > 0" style="margin-top: 20px;">
        <table class="table">
          <thead>
            <tr>
              <th>Registro ANS</th>
              <th>CNPJ</th>
              <th>Nome Fantasia</th>
              <th>Razão Social</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, idx) in results" :key="idx">
              <td>{{ r.registro_ans }}</td>
              <td>{{ r.cnpj }}</td>
              <td>{{ r.nome_fantasia }}</td>
              <td>{{ r.razao_social }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="view === 'ranking'" class="card">
      <h2>Top 10 Maiores Gastos Assistenciais (2024)</h2>
      <p class="muted">Análise baseada no desacumulado de sinistros médico-hospitalares.</p>
      
      <div v-if="loadingRank" class="loading">Processando dados financeiros...</div>
      
      <table v-else class="table">
        <thead>
          <tr>
            <th>Posição</th>
            <th>Operadora</th>
            <th style="text-align: right;">Gasto Total (R$)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in ranking" :key="idx">
            <td>{{ idx + 1 }}º</td>
            <td>
              <div>{{ item['Razao Social'] }}</div>
              <div class="progress-bar" :style="{ width: (item.valor_real / ranking[0].valor_real * 100) + '%' }"></div>
            </td>
            <td style="text-align: right; font-family: monospace; font-weight: bold; color: #4ade80;">
              {{ formatCurrency(item.valor_real) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const view = ref('search')
const query = ref('')
const results = ref([])
const ranking = ref([])
const loadingSearch = ref(false)
const loadingRank = ref(false)

async function doSearch() {
  loadingSearch.value = true
  try {
    const res = await fetch(`http://127.0.0.1:8000/search?query=${encodeURIComponent(query.value)}`)
    const data = await res.json()
    results.value = data.results || []
  } catch (e) { alert("Erro na API de busca") }
  finally { loadingSearch.value = false }
}

async function loadRanking() {
  view.value = 'ranking'
  loadingRank.value = true
  try {
    const res = await fetch('http://127.0.0.1:8000/analytics/top-10')
    const data = await res.json()
    ranking.value = Array.isArray(data) ? data : []
  } catch (e) { console.error(e) }
  finally { loadingRank.value = false }
}

const formatCurrency = (val) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val)
</script>