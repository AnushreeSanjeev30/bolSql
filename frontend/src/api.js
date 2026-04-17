import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
})

export async function sendQuery(text, language = 'hinglish') {
  const { data } = await api.post('/query', { text, verbose: false, language })
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

export async function getAllTrends(festival = 'general') {
  const { data } = await api.get('/trends/all', { params: { festival } })
  return data
}

export async function exportTrendsJSON(festival = 'general') {
  const { data } = await api.get('/trends/export-json', { params: { festival } })
  return data
}

export async function exportTrendsPDF() {
  const response = await api.get('/trends/export-pdf', { responseType: 'blob' })
  return response.data
}

export async function getCustomerTrends() {
  const { data } = await api.get('/customer-trends')
  return data
}

export async function getCurrentWeather(language = 'hinglish') {
  const { data } = await api.get('/weather/current', { params: { language } })
  return data
}

export async function getTrendsMetadata(language = 'hinglish') {
  const { data } = await api.get('/trends/metadata', { params: { language } })
  return data
}

export async function uploadBill(bill) {
  const { data } = await api.post('/api/upload-bill', bill)
  return data
}

export async function importSalesCsv(csvText, mode = 'transaction') {
  const { data } = await api.post('/api/import-sales-csv', { csv_text: csvText, mode })
  return data
}

export async function clearInventory() {
  const { data } = await api.post('/api/inventory/clear')
  return data
}

export async function synthesizeVoice(text, language = 'hinglish') {
  const response = await api.post('/tts', { text, language }, { responseType: 'blob' })
  return response.data
}

