import { useState, useEffect } from 'react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { getAllTrends, exportTrendsPDF, exportTrendsJSON } from '../api'

export default function TrendsPanel() {
  const [trends, setTrends] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedTrend, setSelectedTrend] = useState(null)

  const trendTypes = [
    'sales_trend',
    'hourly_rush',
    'product_demand',
    'seasonal_trend',
    'stock_depletion',
    'smart_reorder',
    'dead_stock',
    'profit_trend',
    'festival_trend',
    'market_basket',
    'customer_pattern',
    'auto_subscription',
    'weather_trend',
  ]

  const trendLabels = {
    sales_trend: '📊 Sales Trend',
    hourly_rush: '🕐 Hourly Rush',
    product_demand: '📦 Product Demand',
    seasonal_trend: '🌦️ Seasonal Trends',
    stock_depletion: '⚠️ Stock Depletion',
    smart_reorder: '🛒 Smart Reorder',
    dead_stock: '💀 Dead Stock',
    profit_trend: '💰 Profit Trend',
    festival_trend: '🎉 Festival Trends',
    market_basket: '🧺 Market Basket',
    customer_pattern: '👥 Customer Patterns',
    auto_subscription: '🔄 Auto Subscription',
    weather_trend: '🌤️ Weather Impact',
  }

  useEffect(() => {
    loadAllTrends()
  }, [])

  const loadAllTrends = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getAllTrends()
      setTrends(data.trends || [])
      if (data.trends && data.trends.length > 0) {
        setSelectedTrend(data.trends[0])
      }
    } catch (e) {
      setError(e.message)
      console.error('Trends error:', e)
    } finally {
      setLoading(false)
    }
  }

  const exportPDF = async () => {
    try {
      const blob = await exportTrendsPDF()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `trends-report-${new Date().toISOString().split('T')[0]}.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (e) {
      console.error('PDF export error:', e)
      setError('Failed to export PDF')
    }
  }

  const exportJSON = async () => {
    try {
      const data = await exportTrendsJSON()
      const dataStr = JSON.stringify(data, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `trends-report-${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (e) {
      console.error('JSON export error:', e)
      setError('Failed to export JSON')
    }
  }

  const styles = {
    container: {
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: 'var(--bg)',
      color: 'var(--text)',
    },
    header: {
      padding: '20px',
      borderBottom: '1px solid var(--border)',
      background: 'var(--bg-surface)',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    title: {
      fontSize: 18,
      fontWeight: 600,
      margin: 0,
    },
    buttonGroup: {
      display: 'flex',
      gap: 10,
    },
    button: {
      padding: '8px 16px',
      borderRadius: 4,
      border: '1px solid var(--border)',
      background: 'var(--bg-card)',
      color: 'var(--text)',
      cursor: 'pointer',
      fontSize: 12,
      fontWeight: 500,
      transition: 'all 0.2s',
    },
    buttonHover: {
      background: 'var(--accent)',
      borderColor: 'var(--accent)',
    },
    content: {
      display: 'flex',
      flex: 1,
      overflow: 'hidden',
    },
    sidebar: {
      width: '200px',
      borderRight: '1px solid var(--border)',
      overflowY: 'auto',
      background: 'var(--bg-card)',
    },
    trendItem: {
      padding: '12px 16px',
      borderBottom: '1px solid var(--border)',
      cursor: 'pointer',
      transition: 'background 0.2s',
      fontSize: 13,
      fontWeight: 500,
    },
    trendItemActive: {
      background: 'var(--accent)',
      color: '#fff',
    },
    main: {
      flex: 1,
      overflowY: 'auto',
      padding: '20px',
    },
    loading: {
      textAlign: 'center',
      padding: '40px',
      color: 'var(--text-muted)',
    },
    error: {
      background: '#fee',
      border: '1px solid #fcc',
      borderRadius: 4,
      padding: 12,
      color: '#c33',
      marginBottom: 16,
      fontSize: 12,
    },
    trendSection: {
      marginBottom: 24,
    },
    trendTitle: {
      fontSize: 16,
      fontWeight: 600,
      marginBottom: 16,
      borderBottom: '2px solid var(--accent)',
      paddingBottom: 8,
    },
    chartContainer: {
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 4,
      padding: 16,
      marginBottom: 16,
      width: '100%',
      height: 300,
    },
    trendData: {
      fontSize: 13,
      lineHeight: '1.6',
      whiteSpace: 'pre-wrap',
      fontFamily: 'var(--font-mono)',
      background: 'var(--bg-card)',
      padding: 12,
      borderRadius: 4,
      border: '1px solid var(--border)',
      color: 'var(--text-muted)',
    },
    chart: {
      marginTop: 12,
      fontSize: 13,
    },
    emptyState: {
      textAlign: 'center',
      padding: '60px 20px',
      color: 'var(--text-muted)',
    },
    insight: {
      marginTop: 16,
      padding: 12,
      background: 'var(--bg-card)',
      borderRadius: 4,
      border: '1px solid var(--border)',
      color: 'var(--text)',
    },
  }

  // Parse seasonal trend data for chart
  const parseSeasonalTrendData = (formatted) => {
    if (!formatted) return []
    const lines = formatted.split('\n')
    const data = []
    const regex = /(\d{4}-\d{2}):\s*([\d,]+\.[\d]+)\s*units\s*\(\s*(₹[\d,]+)\s*\)/
    
    lines.forEach((line) => {
      const match = line.match(regex)
      if (match) {
        data.push({
          month: match[1],
          units: parseFloat(match[2].replace(/,/g, '')),
          amount: match[3],
        })
      }
    })
    return data
  }

  // Render appropriate chart based on trend type and data structure
  const renderChart = (trend) => {
    if (!trend.raw || !trend.raw.data) return null

    const { type, raw } = trend
    const data = raw.data || []

    // Sales Trend - Line Chart
    if (type === 'sales_trend' && data.length > 0) {
      return (
        <div style={styles.chartContainer}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="day" stroke="var(--text-muted)" />
              <YAxis stroke="var(--text-muted)" />
              <Tooltip 
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
                labelStyle={{ color: 'var(--text)' }}
                formatter={(value) => `₹${value.toLocaleString()}`}
              />
              <Legend />
              <Line type="monotone" dataKey="revenue" stroke="#00C49F" strokeWidth={2} dot={{ r: 4 }} name="Revenue" />
              <Line type="monotone" dataKey="orders" stroke="#0088FE" strokeWidth={2} dot={{ r: 4 }} name="Orders" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )
    }

    // Hourly Rush - Bar Chart
    if (type === 'hourly_rush' && data.length > 0) {
      const chartData = data.map(d => ({
        ...d,
        hour: `${d.hour}:00`
      }))
      return (
        <div style={styles.chartContainer}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="hour" stroke="var(--text-muted)" />
              <YAxis stroke="var(--text-muted)" />
              <Tooltip 
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
                labelStyle={{ color: 'var(--text)' }}
              />
              <Legend />
              <Bar dataKey="orders" fill="#FFBB28" name="Orders" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )
    }

    // Product Demand - Bar Chart (Top products)
    if (type === 'product_demand' && data.length > 0) {
      return (
        <div style={styles.chartContainer}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" stroke="var(--text-muted)" />
              <YAxis dataKey="item_name" type="category" stroke="var(--text-muted)" width={100} />
              <Tooltip 
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
                labelStyle={{ color: 'var(--text)' }}
              />
              <Legend />
              <Bar dataKey="total_qty" fill="#8884D8" name="Quantity" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )
    }

    // Stock Depletion - Bar Chart
    if (type === 'stock_depletion' && data.length > 0) {
      return (
        <div style={styles.chartContainer}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="item_name" stroke="var(--text-muted)" angle={-45} textAnchor="end" height={80} />
              <YAxis stroke="var(--text-muted)" />
              <Tooltip 
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
                labelStyle={{ color: 'var(--text)' }}
              />
              <Legend />
              <Bar dataKey="current_stock" fill="#FF8042" name="Current Stock" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )
    }

    // Market Basket - Pie Chart
    if (type === 'market_basket' && data.length > 0) {
      return (
        <div style={styles.chartContainer}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="count" nameKey="pair" cx="50%" cy="50%" outerRadius={80} label>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
                labelStyle={{ color: 'var(--text)' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )
    }

    return null
  }

  // Chart colors
  const COLORS = ['#00C49F', '#0088FE', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#FFC658', '#FF7C7C']

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>📈 Kirana Trends & Reports</h1>
        <div style={styles.buttonGroup}>
          <button
            style={styles.button}
            onClick={loadAllTrends}
            onMouseEnter={(e) => e.target.style.background = 'var(--accent)'}
            onMouseLeave={(e) => e.target.style.background = 'var(--bg-card)'}
          >
            🔄 Refresh
          </button>
          <button
            style={styles.button}
            onClick={exportPDF}
            onMouseEnter={(e) => e.target.style.background = 'var(--accent)'}
            onMouseLeave={(e) => e.target.style.background = 'var(--bg-card)'}
          >
            📄 PDF
          </button>
          <button
            style={styles.button}
            onClick={exportJSON}
            onMouseEnter={(e) => e.target.style.background = 'var(--accent)'}
            onMouseLeave={(e) => e.target.style.background = 'var(--bg-card)'}
          >
            📊 JSON
          </button>
        </div>
      </div>

      {/* Content */}
      <div style={styles.content}>
        {/* Sidebar - Trend List */}
        <div style={styles.sidebar}>
          {trendTypes.map((type) => (
            <div
              key={type}
              style={{
                ...styles.trendItem,
                ...(selectedTrend?.type === type ? styles.trendItemActive : {}),
              }}
              onClick={() => {
                const trend = trends.find((t) => t.type === type)
                if (trend) setSelectedTrend(trend)
              }}
            >
              {trendLabels[type] || type}
            </div>
          ))}
        </div>

        {/* Main - Trend Details */}
        <div style={styles.main}>
          {loading && <div style={styles.loading}>⏳ Loading trends...</div>}

          {error && <div style={styles.error}>❌ Error: {error}</div>}

          {!loading && !error && !selectedTrend && (
            <div style={styles.emptyState}>
              <p>Select a trend from the sidebar to view details</p>
            </div>
          )}

          {selectedTrend && (
            <div style={styles.trendSection}>
              <h2 style={styles.trendTitle}>{trendLabels[selectedTrend.type] || selectedTrend.type}</h2>
              
              {/* Render chart based on trend type */}
              {renderChart(selectedTrend)}

              {/* Display formatted text */}
              {selectedTrend.formatted && (
                <div style={styles.trendData}>
                  {selectedTrend.formatted}
                </div>
              )}

              {/* Raw data collapsible */}
              {selectedTrend.raw && (
                <div style={styles.chart}>
                  <details>
                    <summary style={{ cursor: 'pointer', fontWeight: 600, marginTop: 16 }}>
                      📋 Raw Data
                    </summary>
                    <pre style={styles.trendData}>
                      {JSON.stringify(selectedTrend.raw, null, 2)}
                    </pre>
                  </details>
                </div>
              )}

              {/* Insight box */}
              {selectedTrend.insight && (
                <div style={styles.insight}>
                  <strong>💡 Insight:</strong> {selectedTrend.insight}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
