import { useState, useEffect } from 'react'
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
      marginBottom: 12,
      borderBottom: '2px solid var(--accent)',
      paddingBottom: 8,
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
  }

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
              
              {selectedTrend.formatted && (
                <div style={styles.trendData}>
                  {selectedTrend.formatted}
                </div>
              )}

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

              {selectedTrend.insight && (
                <div style={{ marginTop: 16, padding: 12, background: 'var(--bg-card)', borderRadius: 4 }}>
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
