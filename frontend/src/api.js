import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
})

export async function sendQuery(text) {
  const { data } = await api.post('/query', { text, verbose: false })
  return data
}

export async function getInventory() {
  const { data } = await api.get('/inventory')
  return data.items || []
}

export async function getHealth() {
  const { data } = await api.get('/health')
  return data
}
