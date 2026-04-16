import { useState, useEffect } from 'react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { getAllTrends, exportTrendsPDF, exportTrendsJSON, getCurrentWeather } from '../api'

export default function TrendsPanel({ language = 'hinglish' }) {
  const [trends, setTrends] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedTrend, setSelectedTrend] = useState(null)
  const [liveWeather, setLiveWeather] = useState(null)

  const iconMap = {
    sales: '📊',
    hourly: '🕐',
    product: '📦',
    seasonal: '🌦️',
    stock: '⚠️',
    reorder: '🛒',
    dead: '💀',
    profit: '💰',
    festival: '🎉',
    market: '🧺',
    customer: '👥',
    subscription: '🔄',
    weather: '🌤️',
  }

  const trendLabel = (type) => {
    const text = (type || '')
      .split('_')
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ')
    const icon = Object.entries(iconMap).find(([k]) => type?.includes(k))?.[1] || '📈'
    return `${icon} ${text}`
  }

  const trendNarrative = (type) => {
    if (!type) return 'Trend intelligence'
    if (type.includes('sales')) return 'Revenue pulse'
    if (type.includes('hourly')) return 'Rush window'
    if (type.includes('product')) return 'Top mover spotlight'
    if (type.includes('seasonal')) return 'Seasonal pattern'
    if (type.includes('stock')) return 'Stock risk monitor'
    if (type.includes('reorder')) return 'Reorder command'
    if (type.includes('dead')) return 'Dead stock cleanup'
    if (type.includes('profit')) return 'Margin heatmap'
    if (type.includes('festival')) return 'Festival spike radar'
    if (type.includes('market')) return 'Bundle discovery'
    if (type.includes('customer')) return 'Customer behavior'
    if (type.includes('subscription')) return 'Repeat-buy signal'
    if (type.includes('weather')) return 'Weather demand signal'
    return 'Trend intelligence'
  }

  const trendTone = (type) => {
    if (type?.includes('stock') || type?.includes('dead')) return 'warn'
    if (type?.includes('profit') || type?.includes('sales') || type?.includes('reorder')) return 'ok'
    if (type?.includes('weather') || type?.includes('festival') || type?.includes('seasonal')) return 'accent'
    return 'neutral'
  }

  const trendPalette = (type) => {
    if (type?.includes('sales')) return 'linear-gradient(135deg, rgba(0,196,159,0.22), rgba(0,136,254,0.18))'
    if (type?.includes('hourly')) return 'linear-gradient(135deg, rgba(255,187,40,0.22), rgba(255,124,124,0.14))'
    if (type?.includes('product')) return 'linear-gradient(135deg, rgba(136,132,216,0.20), rgba(0,196,159,0.14))'
    if (type?.includes('stock')) return 'linear-gradient(135deg, rgba(245,158,11,0.22), rgba(239,68,68,0.14))'
    if (type?.includes('profit')) return 'linear-gradient(135deg, rgba(34,197,94,0.20), rgba(16,185,129,0.16))'
    if (type?.includes('festival')) return 'linear-gradient(135deg, rgba(255,187,40,0.22), rgba(168,85,247,0.14))'
    if (type?.includes('weather')) return 'linear-gradient(135deg, rgba(0,136,254,0.22), rgba(0,196,159,0.16))'
    return 'linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03))'
  }

  const sumNumeric = (items, key) => items.reduce((acc, item) => acc + (Number(item?.[key]) || 0), 0)

  const getTrendMetrics = (trend) => {
    if (!trend) return []
    const data = Array.isArray(trend?.raw?.data) ? trend.raw.data : []
    const count = data.length
    const first = data[0] || {}
    const last = data[data.length - 1] || {}
    const topItem = data.reduce((best, item) => {
      const bestScore = Number(best?.revenue ?? best?.profit ?? best?.qty_sold ?? best?.total_qty ?? best?.current_stock ?? best?.count ?? 0)
      const score = Number(item?.revenue ?? item?.profit ?? item?.qty_sold ?? item?.total_qty ?? item?.current_stock ?? item?.count ?? 0)
      return score > bestScore ? item : best
    }, data[0])

    if (trend.type === 'sales_trend') {
      return [
        { label: 'Days', value: count || trend.raw?.days || '--' },
        { label: 'Peak day', value: trend.raw?.peak_day || first.day || '--' },
        { label: 'Peak revenue', value: trend.raw?.peak_revenue ? `₹${Number(trend.raw.peak_revenue).toLocaleString()}` : '—' },
        { label: 'Total revenue', value: data.length ? `₹${sumNumeric(data, 'revenue').toLocaleString()}` : '—' },
      ]
    }

    if (trend.type === 'hourly_rush') {
      return [
        { label: 'Rush hours', value: count || '--' },
        { label: 'Peak slot', value: trend.raw?.peak_hour !== undefined ? `${trend.raw.peak_hour}:00` : '--' },
        { label: 'Peak orders', value: trend.raw?.peak_orders ?? '--' },
        { label: 'Busiest label', value: trend.raw?.peak_hour !== undefined ? `${trend.raw.peak_hour}:00–${Number(trend.raw.peak_hour) + 1}:00` : '--' },
      ]
    }

    if (trend.type === 'product_demand') {
      return [
        { label: 'Products tracked', value: count || '--' },
        { label: 'Top SKU', value: trend.raw?.top_item || topItem?.item || '--' },
        { label: 'Top qty', value: trend.raw?.top_qty ?? topItem?.qty_sold ?? '--' },
        { label: 'Total qty', value: data.length ? sumNumeric(data, 'qty_sold').toLocaleString() : '--' },
      ]
    }

    if (trend.type === 'seasonal_trend') {
      return [
        { label: 'Months', value: count || '--' },
        { label: 'Peak month', value: trend.raw?.peak_month || first.month || '--' },
        { label: 'Scope', value: trend.raw?.label || 'Overall' },
        { label: 'Peak qty', value: topItem?.qty ?? '--' },
      ]
    }

    if (trend.type === 'stock_depletion') {
      const critical = data.filter((item) => (item.days_until_stockout ?? 9999) <= 3).length
      return [
        { label: 'Items flagged', value: count || '--' },
        { label: 'Critical', value: critical },
        { label: 'Next stockout', value: topItem?.item || '--' },
        { label: 'Days left', value: topItem?.days_until_stockout ?? '--' },
      ]
    }

    if (trend.type === 'smart_reorder') {
      return [
        { label: 'Reorder lines', value: count || '--' },
        { label: 'Urgent item', value: topItem?.item || '--' },
        { label: 'Order qty', value: topItem?.reorder_qty ?? '--' },
        { label: 'Reason', value: topItem?.reason ? 'Auto-calculated' : '—' },
      ]
    }

    if (trend.type === 'dead_stock') {
      return [
        { label: 'Dead items', value: count || '--' },
        { label: 'Worst item', value: topItem?.item || '--' },
        { label: 'Idle days', value: topItem?.days_idle ?? '--' },
        { label: 'Inventory held', value: data.length ? sumNumeric(data, 'stock_qty').toLocaleString() : '--' },
      ]
    }

    if (trend.type === 'profit_trend') {
      return [
        { label: 'Profit items', value: count || '--' },
        { label: 'Top item', value: trend.raw?.top_item || topItem?.item || '--' },
        { label: 'Top profit', value: trend.raw?.top_profit !== undefined ? `₹${Number(trend.raw.top_profit).toLocaleString()}` : '—' },
        { label: 'Margin leader', value: topItem?.margin_pct !== undefined ? `${topItem.margin_pct}%` : '--' },
      ]
    }

    if (trend.type === 'festival_trend') {
      return [
        { label: 'Years tracked', value: count || '--' },
        { label: 'Festival', value: trend.raw?.festival || '--' },
        { label: 'Best year', value: trend.raw?.best_year || '--' },
        { label: 'Top revenue', value: topItem?.revenue !== undefined ? `₹${Number(topItem.revenue).toLocaleString()}` : '--' },
      ]
    }

    if (trend.type === 'market_basket') {
      return [
        { label: 'Pairs', value: count || '--' },
        { label: 'Top combo', value: topItem?.pair || '--' },
        { label: 'Co-buys', value: topItem?.count ?? '--' },
        { label: 'Signal', value: trend.raw?.product || 'Bundle discovery' },
      ]
    }

    if (trend.type === 'customer_pattern') {
      const customers = trend.raw?.top_customers || []
      return [
        { label: 'Customers', value: customers.length || count || '--' },
        { label: 'Top customer', value: customers[0]?.customer || '--' },
        { label: 'Orders', value: customers[0]?.orders ?? '--' },
        { label: 'Basket size', value: customers[0]?.unique_items ?? '--' },
      ]
    }

    if (trend.type === 'auto_subscription') {
      return [
        { label: 'Subscriptions', value: count || '--' },
        { label: 'Next item', value: topItem?.item || '--' },
        { label: 'Gap days', value: topItem?.avg_days_between ?? '--' },
        { label: 'Next order', value: topItem?.predicted_next || '--' },
      ]
    }

    if (trend.type === 'weather_trend') {
      return [
        { label: 'Temp', value: liveWeather?.weather?.temperature !== undefined ? `${Math.round(liveWeather.weather.temperature)}°C` : '--' },
        { label: 'Humidity', value: liveWeather?.weather?.humidity !== undefined ? `${liveWeather.weather.humidity}%` : '--' },
        { label: 'Wind', value: liveWeather?.weather?.wind_speed !== undefined ? `${liveWeather.weather.wind_speed} km/h` : '--' },
        { label: 'Condition', value: liveWeather?.weather?.condition || '--' },
      ]
    }

    return [
      { label: 'Signals', value: count || '--' },
      { label: 'Lead insight', value: trend.insight ? 'Available' : 'Pending' },
      { label: 'Preview', value: topItem?.pair || topItem?.item || topItem?.name || '--' },
      { label: 'Source', value: trend.raw ? 'Live data' : 'Generated' },
    ]
  }

  const ui = language === 'tamil'
    ? {
        title: '📈 Kirana Trends & Reports - Viral Kavai',
        refresh: '🔄 Pudhu Data',
        pdf: '📄 PDF',
        json: '📊 JSON',
        loading: '⏳ Trends load aagudhu...',
        empty: 'Sidebar la oru trend select pannunga',
        weatherHero: 'Live Weather Intelligence',
        humidity: 'Eerappadham',
        wind: 'Kaatru',
        condition: 'Nilamai',
        playbook: 'Playbook',
        tip: 'Tip',
        rawData: '📋 Raw Data',
        insight: '💡 Insight',
        actions: '⚡ What To Do Now',
      }
    : {
        title: '📈 Kirana Trends & Reports',
        refresh: '🔄 Refresh',
        pdf: '📄 PDF',
        json: '📊 JSON',
        loading: '⏳ Loading trends...',
        empty: 'Select a trend from the sidebar to view details',
        weatherHero: 'Live Weather Intelligence',
        humidity: 'Humidity',
        wind: 'Wind',
        condition: 'Condition',
        playbook: 'Playbook',
        tip: 'Tip',
        rawData: '📋 Raw Data',
        insight: '💡 Insight',
        actions: '⚡ What To Do Now',
      }

  const actionPlaybook = {
    hinglish: {
      sales_trend: ['Top-selling SKU pe stock buffer 20% badhao', 'Slow SKU pe combo offer test karo'],
      hourly_rush: ['Peak hour ke pehle counter prep karo', 'Fast-moving items front rack pe rakho'],
      stock_depletion: ['Critical items ka reorder aaj hi place karo', 'Safety stock threshold set karo'],
      smart_reorder: ['Suggested reorder list ko supplier ke saath lock karo', 'High margin items ko priority do'],
      dead_stock: ['Dead stock pe discount bundle launch karo', 'Shelf space ko fast movers ko do'],
      market_basket: ['Top pairs pe combo pricing do', 'Co-purchase items ko paas-pass display karo'],
      weather_trend: ['Weather-led top items ka display front pe rakho', '2-day demand spike ke liye quick reorder karo'],
    },
    tamil: {
      sales_trend: ['Top selling items-ku 20% stock buffer vainga', 'Slow moving items-ku combo offer podunga'],
      hourly_rush: ['Peak hour-ku munna counter prep pannunga', 'Fast movers front rack la vainga'],
      stock_depletion: ['Critical items reorder innaikke podunga', 'Safety stock limit set pannunga'],
      smart_reorder: ['Suggested reorder list supplier-oda confirm pannunga', 'High margin items-ku munnadi priority kudunga'],
      dead_stock: ['Dead stock-ku discount bundle podunga', 'Shelf space fast movers-ku maathunga'],
      market_basket: ['Top pairs-ku combo price kudunga', 'Saathaa vangara items side-by-side display pannunga'],
      weather_trend: ['Weather-led top items front display la podunga', '2-naal spike-ku quick reorder pannunga'],
    },
  }

  const getSeries = (trend) => {
    const d = trend?.raw?.data
    if (!Array.isArray(d) || d.length === 0) return []
    return d.slice(0, 8).map((x) => (
      x.revenue ?? x.orders ?? x.total_qty ?? x.current_stock ?? x.count ?? x.qty ?? 0
    )).filter(v => typeof v === 'number' && !Number.isNaN(v))
  }

  const trendMeta = (trend) => {
    if (trend?.error) return { status: 'issue', confidence: 'Low' }
    const points = getSeries(trend).length
    if (points >= 6) return { status: 'active', confidence: 'High' }
    if (points >= 3) return { status: 'warming', confidence: 'Medium' }
    return { status: 'new', confidence: 'Low' }
  }

  useEffect(() => {
    loadAllTrends()
    loadWeather()
  }, [])

  const loadWeather = async () => {
    try {
      const data = await getCurrentWeather(language)
      if (data?.success) setLiveWeather(data)
    } catch (e) {
      console.error('Weather fetch error:', e)
    }
  }

  const loadAllTrends = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getAllTrends()
      const fetched = data.trends || []
      setTrends(fetched)
      if (fetched.length > 0) {
        setSelectedTrend(prev => {
          if (!prev) return fetched[0]
          return fetched.find(t => t.type === prev.type) || fetched[0]
        })
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
      width: '260px',
      borderRight: '1px solid var(--border)',
      overflowY: 'auto',
      background: 'var(--bg-card)',
      padding: '10px 10px 14px',
    },
    trendItem: {
      padding: '10px 12px',
      border: '1px solid var(--border)',
      borderRadius: 10,
      marginBottom: 10,
      cursor: 'pointer',
      transition: 'all 0.2s',
      fontSize: 12,
      fontWeight: 500,
      background: 'linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0))',
    },
    trendItemActive: {
      background: 'linear-gradient(135deg, rgba(0,196,159,0.2), rgba(0,136,254,0.18))',
      color: 'var(--text)',
      borderColor: 'rgba(0,196,159,0.6)',
      boxShadow: '0 8px 20px rgba(0,0,0,0.2)',
    },
    trendItemTop: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      gap: 8,
      marginBottom: 8,
    },
    trendItemTitle: {
      fontSize: 13,
      fontWeight: 600,
      lineHeight: 1.3,
    },
    trendSub: {
      fontSize: 11,
      color: 'var(--text-muted)',
      fontFamily: 'var(--font-mono)',
      marginBottom: 8,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    },
    badgeRow: {
      display: 'flex',
      gap: 6,
      marginBottom: 8,
      flexWrap: 'wrap',
    },
    badge: (tone) => ({
      fontSize: 10,
      fontFamily: 'var(--font-mono)',
      padding: '3px 8px',
      borderRadius: 999,
      border: '1px solid ' + (tone === 'ok' ? 'rgba(0,196,159,0.5)' : tone === 'warn' ? 'rgba(245,158,11,0.5)' : 'rgba(239,68,68,0.5)'),
      color: tone === 'ok' ? 'var(--teal)' : tone === 'warn' ? '#f59e0b' : '#ef4444',
      background: tone === 'ok' ? 'rgba(0,196,159,0.12)' : tone === 'warn' ? 'rgba(245,158,11,0.12)' : 'rgba(239,68,68,0.12)',
    }),
    sparkline: {
      display: 'flex',
      alignItems: 'flex-end',
      gap: 3,
      height: 26,
    },
    sparkBar: (h) => ({
      width: 6,
      height: `${Math.max(4, h)}px`,
      borderRadius: 999,
      background: 'linear-gradient(180deg, rgba(0,196,159,0.85), rgba(0,136,254,0.65))',
    }),
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
    weatherHero: {
      marginBottom: 16,
      borderRadius: 16,
      border: '1px solid rgba(0, 196, 159, 0.35)',
      background: 'linear-gradient(135deg, rgba(0,196,159,0.18) 0%, rgba(0,136,254,0.16) 50%, rgba(255,187,40,0.14) 100%)',
      boxShadow: '0 20px 40px rgba(0,0,0,0.24)',
      padding: 18,
      overflow: 'hidden',
      position: 'relative',
    },
    weatherHeroTop: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      gap: 12,
      marginBottom: 12,
    },
    weatherHeadline: {
      fontSize: 22,
      fontWeight: 700,
      letterSpacing: '-0.3px',
      marginBottom: 4,
    },
    weatherSub: {
      fontSize: 12,
      color: 'var(--text-muted)',
      fontFamily: 'var(--font-mono)',
    },
    weatherTemp: {
      fontSize: 42,
      fontWeight: 800,
      lineHeight: 1,
      color: 'var(--teal)',
      textShadow: '0 0 24px rgba(0,196,159,0.35)',
    },
    weatherStats: {
      display: 'grid',
      gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
      gap: 10,
      marginBottom: 14,
    },
    weatherStatCard: {
      background: 'rgba(0,0,0,0.22)',
      border: '1px solid rgba(255,255,255,0.12)',
      borderRadius: 10,
      padding: '10px 12px',
    },
    weatherStatLabel: {
      fontSize: 10,
      color: 'var(--text-muted)',
      fontFamily: 'var(--font-mono)',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
      marginBottom: 6,
    },
    weatherStatValue: {
      fontSize: 18,
      fontWeight: 700,
    },
    chipWrap: {
      display: 'flex',
      gap: 8,
      flexWrap: 'wrap',
      marginTop: 10,
    },
    chip: {
      padding: '6px 10px',
      borderRadius: 999,
      border: '1px solid rgba(0,196,159,0.45)',
      background: 'rgba(0,196,159,0.12)',
      fontSize: 11,
      fontFamily: 'var(--font-mono)',
      color: 'var(--teal)',
    },
    actionCard: {
      marginTop: 16,
      border: '1px solid rgba(255,187,40,0.35)',
      borderRadius: 12,
      background: 'linear-gradient(135deg, rgba(255,187,40,0.10), rgba(0,196,159,0.08))',
      padding: 14,
    },
    actionTitle: {
      fontSize: 12,
      fontFamily: 'var(--font-mono)',
      color: '#ffcc66',
      marginBottom: 10,
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
    },
    actionItem: {
      fontSize: 13,
      marginBottom: 7,
      color: 'var(--text)',
    },
    trendHero: {
      border: '1px solid rgba(255,255,255,0.10)',
      borderRadius: 18,
      padding: 18,
      marginBottom: 16,
      boxShadow: '0 18px 36px rgba(0,0,0,0.18)',
      overflow: 'hidden',
      position: 'relative',
    },
    trendHeroTop: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      gap: 16,
      marginBottom: 14,
    },
    trendHeroIcon: {
      width: 54,
      height: 54,
      borderRadius: 16,
      display: 'grid',
      placeItems: 'center',
      fontSize: 26,
      background: 'rgba(255,255,255,0.10)',
      border: '1px solid rgba(255,255,255,0.12)',
      flexShrink: 0,
    },
    trendHeroHeadline: {
      fontSize: 26,
      fontWeight: 800,
      letterSpacing: '-0.4px',
      lineHeight: 1.05,
      marginBottom: 6,
    },
    trendHeroSub: {
      fontSize: 13,
      color: 'var(--text-muted)',
      maxWidth: 680,
      lineHeight: 1.5,
    },
    trendHeroMeta: {
      display: 'flex',
      gap: 8,
      flexWrap: 'wrap',
      justifyContent: 'flex-end',
    },
    trendHeroPill: {
      padding: '6px 10px',
      borderRadius: 999,
      border: '1px solid rgba(255,255,255,0.14)',
      background: 'rgba(255,255,255,0.08)',
      fontSize: 11,
      fontFamily: 'var(--font-mono)',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
    },
    metricGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
      gap: 10,
      marginTop: 14,
    },
    metricCard: {
      background: 'rgba(0,0,0,0.18)',
      border: '1px solid rgba(255,255,255,0.10)',
      borderRadius: 14,
      padding: '12px 12px 10px',
    },
    metricLabel: {
      fontSize: 10,
      color: 'var(--text-muted)',
      textTransform: 'uppercase',
      letterSpacing: '0.6px',
      fontFamily: 'var(--font-mono)',
      marginBottom: 8,
    },
    metricValue: {
      fontSize: 16,
      fontWeight: 700,
      lineHeight: 1.25,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    },
  }

  const weatherEmoji = (condition = '') => {
    const c = condition.toLowerCase()
    if (c.includes('thunder')) return '⛈️'
    if (c.includes('rain')) return '🌧️'
    if (c.includes('snow')) return '❄️'
    if (c.includes('fog')) return '🌫️'
    if (c.includes('overcast') || c.includes('cloud')) return '☁️'
    return '☀️'
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
        <h1 style={styles.title}>{ui.title}</h1>
        <div style={styles.buttonGroup}>
          <button
            style={styles.button}
            onClick={loadAllTrends}
            onMouseEnter={(e) => e.target.style.background = 'var(--accent)'}
            onMouseLeave={(e) => e.target.style.background = 'var(--bg-card)'}
          >
            {ui.refresh}
          </button>
          <button
            style={styles.button}
            onClick={exportPDF}
            onMouseEnter={(e) => e.target.style.background = 'var(--accent)'}
            onMouseLeave={(e) => e.target.style.background = 'var(--bg-card)'}
          >
            {ui.pdf}
          </button>
          <button
            style={styles.button}
            onClick={exportJSON}
            onMouseEnter={(e) => e.target.style.background = 'var(--accent)'}
            onMouseLeave={(e) => e.target.style.background = 'var(--bg-card)'}
          >
            {ui.json}
          </button>
        </div>
      </div>

      {/* Content */}
      <div style={styles.content}>
        {/* Sidebar - Trend List */}
        <div style={styles.sidebar}>
          {trends.map((trend) => (
            <div
              key={trend.type}
              style={{
                ...styles.trendItem,
                ...(selectedTrend?.type === trend.type ? styles.trendItemActive : {}),
              }}
              onClick={() => setSelectedTrend(trend)}
            >
              <div style={styles.trendItemTop}>
                <div style={styles.trendItemTitle}>{trendLabel(trend.type)}</div>
              </div>
              <div style={styles.trendSub}>{trend.insight || trend.formatted?.split('\n')[0] || 'No summary yet'}</div>
              <div style={styles.badgeRow}>
                {(() => {
                  const meta = trendMeta(trend)
                  const statusTone = meta.status === 'active' ? 'ok' : meta.status === 'warming' ? 'warn' : 'danger'
                  const statusText = meta.status === 'active' ? 'ACTIVE' : meta.status === 'warming' ? 'WARMING' : meta.status === 'issue' ? 'ISSUE' : 'NEW'
                  return (
                    <>
                      <span style={styles.badge(statusTone)}>{statusText}</span>
                      <span style={styles.badge('ok')}>{meta.confidence}</span>
                    </>
                  )
                })()}
              </div>
              <div style={styles.sparkline}>
                {(() => {
                  const series = getSeries(trend)
                  const max = Math.max(...series, 1)
                  return series.length
                    ? series.map((v, i) => <span key={i} style={styles.sparkBar((v / max) * 24)} />)
                    : <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>no sparkline</span>
                })()}
              </div>
            </div>
          ))}
        </div>

        {/* Main - Trend Details */}
        <div style={styles.main}>
          {loading && <div style={styles.loading}>{ui.loading}</div>}

          {error && <div style={styles.error}>❌ Error: {error}</div>}

          {!loading && !error && !selectedTrend && (
            <div style={styles.emptyState}>
              <p>{ui.empty}</p>
            </div>
          )}

          {selectedTrend && (
            <div style={styles.trendSection}>
              <div style={{ ...styles.trendHero, background: trendPalette(selectedTrend.type) }}>
                <div style={styles.trendHeroTop}>
                  <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start', minWidth: 0 }}>
                    <div style={styles.trendHeroIcon}>
                      {Object.entries(iconMap).find(([k]) => selectedTrend.type?.includes(k))?.[1] || '📈'}
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={styles.trendHeroHeadline}>{trendLabel(selectedTrend.type)}</div>
                      <div style={styles.trendHeroSub}>
                        {trendNarrative(selectedTrend.type)} · {selectedTrend.insight || selectedTrend.formatted?.split('\n')[0] || 'Fresh analytical signal from your shop data.'}
                      </div>
                    </div>
                  </div>
                  <div style={styles.trendHeroMeta}>
                    <span style={styles.trendHeroPill}>{trendTone(selectedTrend.type).toUpperCase()}</span>
                    <span style={styles.trendHeroPill}>{selectedTrend.raw?.data?.length || 0} signal points</span>
                    <span style={styles.trendHeroPill}>{selectedTrend.raw?.trend || selectedTrend.type}</span>
                  </div>
                </div>

                <div style={styles.metricGrid}>
                  {getTrendMetrics(selectedTrend).map((metric) => (
                    <div key={`${metric.label}-${metric.value}`} style={styles.metricCard}>
                      <div style={styles.metricLabel}>{metric.label}</div>
                      <div style={styles.metricValue}>{metric.value}</div>
                    </div>
                  ))}
                </div>
              </div>

              {selectedTrend.type === 'weather_trend' && liveWeather?.weather && (
                <div style={styles.weatherHero}>
                  <div style={styles.weatherHeroTop}>
                    <div>
                      <div style={styles.weatherHeadline}>
                        {weatherEmoji(liveWeather.weather.condition)} {ui.weatherHero}
                      </div>
                      <div style={styles.weatherSub}>
                        {liveWeather.weather.description} • {liveWeather.weather.timestamp || 'now'}
                      </div>
                    </div>
                    <div style={styles.weatherTemp}>{Math.round(liveWeather.weather.temperature ?? 0)}°C</div>
                  </div>

                  <div style={styles.weatherStats}>
                    <div style={styles.weatherStatCard}>
                      <div style={styles.weatherStatLabel}>{ui.humidity}</div>
                      <div style={styles.weatherStatValue}>{liveWeather.weather.humidity ?? '--'}%</div>
                    </div>
                    <div style={styles.weatherStatCard}>
                      <div style={styles.weatherStatLabel}>{ui.wind}</div>
                      <div style={styles.weatherStatValue}>{liveWeather.weather.wind_speed ?? '--'} km/h</div>
                    </div>
                    <div style={styles.weatherStatCard}>
                      <div style={styles.weatherStatLabel}>{ui.condition}</div>
                      <div style={styles.weatherStatValue}>{liveWeather.weather.condition || 'unknown'}</div>
                    </div>
                  </div>

                  <div style={styles.insight}>
                    <strong>🎯 {ui.playbook}:</strong> {liveWeather.playbook?.headline}
                    <div style={styles.chipWrap}>
                      {(liveWeather.playbook?.products || []).slice(0, 8).map((p) => (
                        <span key={p} style={styles.chip}>{p}</span>
                      ))}
                    </div>
                    {liveWeather.playbook?.weather_tip && (
                      <div style={{ marginTop: 10 }}><strong>{ui.tip}:</strong> {liveWeather.playbook.weather_tip}</div>
                    )}
                  </div>
                </div>
              )}
              
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
                      {ui.rawData}
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
                  <strong>{ui.insight}:</strong> {selectedTrend.insight}
                </div>
              )}

              <div style={styles.actionCard}>
                <div style={styles.actionTitle}>{ui.actions}</div>
                {(actionPlaybook[language]?.[selectedTrend.type] || actionPlaybook.hinglish[selectedTrend.type] || [
                  language === 'tamil' ? 'Data-a base panni next action decide pannunga' : 'Use this trend to decide next operational action',
                ]).map((a, i) => (
                  <div key={i} style={styles.actionItem}>• {a}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
