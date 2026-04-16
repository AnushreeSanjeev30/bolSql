import { useState, useEffect } from 'react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { getAllTrends, exportTrendsPDF, exportTrendsJSON, getCurrentWeather } from '../api'

export default function TrendsPanel({ language = 'hinglish', refreshKey = 0 }) {
  const [trends, setTrends] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedTrend, setSelectedTrend] = useState(null)
  const [liveWeather, setLiveWeather] = useState(null)
  const [showAIReasoning, setShowAIReasoning] = useState(false)
  const [aiQuestion, setAIQuestion] = useState('')
  const [aiReply, setAIReply] = useState('')

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

  const getTrendDataRows = (trend) => {
    if (Array.isArray(trend?.raw?.data)) return trend.raw.data
    if (Array.isArray(trend?.raw)) return trend.raw
    return []
  }

  const getSeasonalSeries = (trend) => {
    const raw = Array.isArray(trend?.raw?.data) ? trend.raw.data : []
    const mapped = raw
      .map((row) => ({
        month: row.month || row.period || '--',
        qty: Number(row.qty ?? row.units ?? row.total_qty ?? 0),
      }))
      .filter((row) => row.month && !Number.isNaN(row.qty))
    return mapped
  }

  const getSeasonalAI = (trend) => {
    const series = getSeasonalSeries(trend)
    if (!series.length) return null
    const isTanglishLike = language === 'tanglish' || language === 'tamil'

    const peak = series.reduce((best, row) => (row.qty > best.qty ? row : best), series[0])
    const first = series[0].qty
    const last = series[series.length - 1].qty
    const growthPct = first > 0 ? ((last - first) / first) * 100 : 0
    const recent3 = series.slice(-3)
    const movingAvg = recent3.length ? recent3.reduce((a, b) => a + b.qty, 0) / recent3.length : last
    const nextQty = Math.round((movingAvg * 0.7) + (last * 0.3))
    const confidence = Math.max(58, Math.min(94, Math.round(62 + Math.min(series.length, 8) * 3 + (Math.abs(growthPct) <= 20 ? 10 : 2))))

    const monthToken = String(peak.month).slice(5, 7)
    const whyMap = {
      '03': isTanglishLike ? 'Summer prep start aagudhu, beverages demand rise aagum.' : 'Summer prep starts, beverages begin to rise.',
      '04': isTanglishLike ? 'Peak summer effect nala cool items demand increase aagudhu.' : 'Peak summer effect pushes cool-item demand up.',
      '05': isTanglishLike ? 'Summer continuation nala cold products fast move aagudhu.' : 'Summer continuation keeps cold products moving fast.',
      '10': isTanglishLike ? 'Festival season start nala snack and gifting pull varudhu.' : 'Festival season start boosts snack and gifting pull.',
      '11': isTanglishLike ? 'Festival buying window nala footfall and basket size both improve aagudhu.' : 'Festival buying window lifts footfall and basket size.',
      '12': isTanglishLike ? 'Year-end purchase cycle nala pantry refill activity increase aagudhu.' : 'Year-end purchase cycle increases pantry refills.',
    }

    const monthReason = whyMap[monthToken] || (isTanglishLike
      ? 'Seasonal buying behavior and local demand cycle pattern match aagudhu.'
      : 'Seasonal buying behavior and local demand cycle align here.')

    return {
      series,
      peak,
      growthPct,
      nextQty,
      confidence,
      monthReason,
    }
  }

  const seasonalActions = (trend) => {
    const ai = getSeasonalAI(trend)
    if (!ai) return []
    const plus = Math.max(1, Math.round(ai.nextQty * 0.25))
    const reduce = Math.max(1, Math.round(ai.nextQty * 0.1))
    if (language === 'tanglish') {
      return [
        `Next cycle-ku fast movers stock ~25% increase pannunga (+${plus} units).`,
        `Slow movers stock 10% reduce pannunga (~${reduce} units).`,
        'Peak-ku 5 naal munnadi bulk purchase lock pannunga.',
        'High-demand items counter pakkam display pannunga.',
      ]
    }
    if (language === 'tamil') {
      return [
        `Adutha cycle-ku fast movers stock ~25% increase pannunga (+${plus} units).`,
        `Slow movers stock 10% reduce pannunga (~${reduce} units).`,
        'Peak-ku 5 naal munnadi bulk purchase lock pannunga.',
        'High-demand items counter pakkathula display pannunga.',
      ]
    }
    return [
      `Increase fast-mover stock by ~25% before next cycle (+${plus} units).`,
      `Reduce slow movers by ~10% (~${reduce} units) to free cash.`,
      'Place bulk purchase order 5 days before expected peak.',
      'Keep high-demand items near checkout for quicker conversion.',
    ]
  }

  const roundToStep = (value, step = 5) => Math.max(0, Math.ceil(value / step) * step)

  const getStockAI = (trend) => {
    const raw = getTrendDataRows(trend)
    const formatted = typeof trend?.formatted === 'string' ? trend.formatted : ''

    const parsedFromFormatted = !raw.length && formatted
      ? formatted
          .split('\n')
          .map((line) => {
            const m = line.match(/(LOW|OK|HIGH)\s+(.+?):\s*([\d.]+)\s*units.*?([\d.]+)\s*days/i)
            if (!m) return null
            return {
              item_name: m[2]?.trim(),
              current_stock: Number(m[3]),
              days_until_stockout: Number(m[4]),
              risk_label: m[1]?.toUpperCase(),
            }
          })
          .filter(Boolean)
      : []

    const sourceRows = raw.length ? raw : parsedFromFormatted
    const today = new Date()
    const items = sourceRows.map((row) => {
      const item = row.item_name || row.item || row.name || 'Item'
      const currentStock = Number(row.current_stock ?? row.stock_qty ?? row.stock ?? 0)
      const avgDaily = Number(row.avg_daily_sales ?? row.daily_sales ?? row.avg_qty ?? 0)
      const daysLeftGiven = Number(row.days_until_stockout)
      const inferredDays = avgDaily > 0 ? currentStock / avgDaily : 9999
      const daysLeft = Number.isFinite(daysLeftGiven) && daysLeftGiven > 0 ? daysLeftGiven : inferredDays
      const leadTime = Number(row.lead_time_days ?? 5)
      const safetyStock = Math.max(10, Math.round(avgDaily * 2.5))
      const reorderQtyRaw = (avgDaily * leadTime) + safetyStock - currentStock
      const reorderQty = roundToStep(Math.max(0, reorderQtyRaw), 5)
      const threshold = Math.max(safetyStock, Math.round(avgDaily * 7))
      const riskByDays = daysLeft <= 7 ? 'HIGH' : daysLeft <= 14 ? 'MEDIUM' : 'LOW'
      const risk = row.risk_label || riskByDays
      const stockoutDate = new Date(today)
      stockoutDate.setDate(stockoutDate.getDate() + Math.max(0, Math.floor(daysLeft)))
      const price = Number(row.unit_price ?? row.price ?? (row.revenue && row.qty ? row.revenue / row.qty : 40))
      const lostUnits7d = Math.max(0, Math.round((avgDaily * 7) - currentStock))
      const lostValue7d = Math.round(lostUnits7d * (Number.isFinite(price) && price > 0 ? price : 40))
      return {
        item,
        currentStock,
        avgDaily,
        daysLeft,
        leadTime,
        safetyStock,
        reorderQty,
        threshold,
        risk,
        stockoutDate,
        lostUnits7d,
        lostValue7d,
      }
    }).filter((x) => x.item)

    const sortedByRisk = [...items].sort((a, b) => a.daysLeft - b.daysLeft)
    const nextStockout = sortedByRisk[0] || null
    const criticalCount = items.filter((x) => x.daysLeft <= 3).length
    const highRiskCount = items.filter((x) => x.risk === 'HIGH').length
    const totalLostValue7d = items.reduce((acc, x) => acc + x.lostValue7d, 0)
    return { items, nextStockout, criticalCount, highRiskCount, totalLostValue7d }
  }

  const stockActions = (trend) => {
    const ai = getStockAI(trend)
    if (!ai?.items?.length) return []
    const top = ai.nextStockout
    if (!top) return []
    if (language === 'tamil' || language === 'tanglish') {
      return [
        `${top.item} reorder ${top.reorderQty} units within 48 hours.`,
        `${top.item} minimum threshold ${top.threshold} units set pannunga.`,
        'Fast-moving items-ku 20% buffer maintain pannunga.',
      ]
    }
    return [
      `Reorder ${top.item}: ${top.reorderQty} units within 48 hours.`,
      `Set minimum threshold for ${top.item}: ${top.threshold} units.`,
      'Increase safety buffer for fast-moving items by 20%.',
    ]
  }

  const askStockAI = (trend, question) => {
    const ai = getStockAI(trend)
    if (!ai?.items?.length || !question?.trim()) return ''
    const q = question.toLowerCase()
    const top = ai.nextStockout
    const isTanglishLike = language === 'tanglish' || language === 'tamil'
    if (!top) return isTanglishLike ? 'Stock data insufficient.' : 'Insufficient stock data.'

    if (q.includes('run out') || q.includes('first') || q.includes('stockout') || q.includes('mudu') || q.includes('theer')) {
      return isTanglishLike
        ? `${top.item} first stockout risk. Approx ${top.daysLeft.toFixed(1)} days left, expected date ${top.stockoutDate.toLocaleDateString('en-GB')}.`
        : `${top.item} will run out first. About ${top.daysLeft.toFixed(1)} days left, expected stockout date ${top.stockoutDate.toLocaleDateString('en-GB')}.`
    }
    if (q.includes('reorder') || q.includes('order') || q.includes('how much') || q.includes('qty')) {
      return isTanglishLike
        ? `${top.item} ku reorder ${top.reorderQty} units suggest pannrom. Formula: (avg daily ${top.avgDaily.toFixed(1)} x lead ${top.leadTime}) + safety ${top.safetyStock} - current ${top.currentStock}.`
        : `Recommended reorder for ${top.item}: ${top.reorderQty} units. Formula: (avg daily ${top.avgDaily.toFixed(1)} x lead ${top.leadTime}) + safety ${top.safetyStock} - current ${top.currentStock}.`
    }
    if (q.includes('7 day') || q.includes('simulate') || q.includes('loss')) {
      return isTanglishLike
        ? `Next 7 days no action-na approx lost sales ₹${ai.totalLostValue7d.toLocaleString()}.`
        : `If no action is taken in next 7 days, estimated lost sales are ₹${ai.totalLostValue7d.toLocaleString()}.`
    }
    return isTanglishLike
      ? `High risk items ${ai.highRiskCount}, critical ${ai.criticalCount}. Next stockout: ${top.item} (${top.daysLeft.toFixed(1)} days).`
      : `High-risk items: ${ai.highRiskCount}, critical: ${ai.criticalCount}. Next stockout: ${top.item} (${top.daysLeft.toFixed(1)} days).`
  }

  const askSeasonalAI = (trend, question) => {
    const ai = getSeasonalAI(trend)
    if (!ai || !question?.trim()) return ''
    const q = question.toLowerCase()
    const isTanglishLike = language === 'tanglish' || language === 'tamil'
    const whyIntent = ['why', 'ky', 'kyu', 'kyo', 'kyun', 'kisliye', 'kaaran', 'enna', 'epdi', 'edhuku', 'ethu nala'].some((k) => q.includes(k))
    const stockIntent = ['stock', 'order', 'reorder', 'buy', 'vang', 'purchase', 'add'].some((k) => q.includes(k))
    const forecastIntent = ['next', 'predict', 'forecast', 'adutha', 'next month', 'coming month'].some((k) => q.includes(k))

    const monthAliases = {
      '01': ['jan', 'january'],
      '02': ['feb', 'february'],
      '03': ['mar', 'march'],
      '04': ['apr', 'april'],
      '05': ['may'],
      '06': ['jun', 'june'],
      '07': ['jul', 'july'],
      '08': ['aug', 'august'],
      '09': ['sep', 'sept', 'september'],
      '10': ['oct', 'october'],
      '11': ['nov', 'november'],
      '12': ['dec', 'december'],
    }

    const monthReasonByToken = {
      '03': isTanglishLike ? 'Summer prep start aagudhu, beverages demand rise aagum.' : 'Summer prep starts, beverages begin to rise.',
      '04': isTanglishLike ? 'Peak summer effect nala cool items demand increase aagudhu.' : 'Peak summer effect pushes cool-item demand up.',
      '05': isTanglishLike ? 'Summer continuation nala cold products fast move aagudhu.' : 'Summer continuation keeps cold products moving fast.',
      '10': isTanglishLike ? 'Festival season start nala snack and gifting pull varudhu.' : 'Festival season start boosts snack and gifting pull.',
      '11': isTanglishLike ? 'Festival buying window nala footfall and basket size both improve aagudhu.' : 'Festival buying window lifts footfall and basket size.',
      '12': isTanglishLike ? 'Year-end purchase cycle nala pantry refill activity increase aagudhu.' : 'Year-end purchase cycle increases pantry refills.',
    }

    let requestedMonthToken = null
    const explicitIso = q.match(/(20\d{2}-\d{2})/)
    if (explicitIso) {
      requestedMonthToken = explicitIso[1].slice(5, 7)
    } else {
      Object.entries(monthAliases).forEach(([token, aliases]) => {
        if (!requestedMonthToken && aliases.some((m) => q.includes(m))) requestedMonthToken = token
      })
    }

    const requestedMonthPoint = requestedMonthToken
      ? [...ai.series].reverse().find((x) => String(x.month).slice(5, 7) === requestedMonthToken)
      : null
    const latestPoint = ai.series[ai.series.length - 1]
    const monthDemandIntent = Boolean(requestedMonthToken) && q.includes('demand')

    if (whyIntent || monthDemandIntent) {
      if (requestedMonthPoint) {
        const reason = monthReasonByToken[requestedMonthToken] || (isTanglishLike
          ? 'Seasonal buying behavior and local demand cycle pattern match aagudhu.'
          : 'Seasonal buying behavior and local demand cycle align here.')
        return isTanglishLike
          ? `${requestedMonthPoint.month} la demand ${requestedMonthPoint.qty.toLocaleString()} units. Reason: ${reason}`
          : `${requestedMonthPoint.month} had demand of ${requestedMonthPoint.qty.toLocaleString()} units. Reason: ${reason}`
      }
      if (requestedMonthToken && !requestedMonthPoint) {
        return isTanglishLike
          ? `Andha month-ku direct data illa. Latest month ${latestPoint.month} la ${latestPoint.qty.toLocaleString()} units irukku. Next cycle forecast ~${ai.nextQty} units (${ai.confidence}% confidence).`
          : `No direct data is available for that month. Latest month ${latestPoint.month} has ${latestPoint.qty.toLocaleString()} units. Next-cycle forecast is ~${ai.nextQty} units (${ai.confidence}% confidence).`
      }
      return isTanglishLike
        ? `Peak month ${ai.peak.month} high irundhadhukku reason: ${ai.monthReason}`
        : `Peak month ${ai.peak.month} was high because: ${ai.monthReason}`
    }
    if (stockIntent) {
      const add = Math.max(1, Math.round(ai.nextQty * 0.25))
      return isTanglishLike
        ? `Recommendation: fast movers-ku +${add} units add pannunga. Peak-ku 5 naal munnadi order podunga.`
        : `Recommendation: add +${add} units for fast movers and place order 5 days before peak.`
    }
    if (forecastIntent) {
      return isTanglishLike
        ? `Next cycle forecast ~${ai.nextQty} units, confidence ${ai.confidence}%.`
        : `Next cycle forecast is ~${ai.nextQty} units with ${ai.confidence}% confidence.`
    }
    return isTanglishLike
      ? `Pattern: growth ${ai.growthPct.toFixed(1)}%, peak ${ai.peak.month}, forecast ${ai.nextQty} units.`
      : `Pattern summary: growth ${ai.growthPct.toFixed(1)}%, peak ${ai.peak.month}, forecast ${ai.nextQty} units.`
  }

  const getTrendMetrics = (trend) => {
    if (!trend) return []
    const data = getTrendDataRows(trend)
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
      const stockAI = getStockAI(trend)
      const next = stockAI?.nextStockout
      return [
        { label: 'Items flagged', value: stockAI?.items?.length ?? count ?? '--' },
        { label: 'Critical', value: stockAI?.criticalCount ?? '--' },
        { label: 'Next stockout', value: next ? `${next.item}` : '--' },
        { label: 'Days left (min)', value: next ? `${next.daysLeft.toFixed(1)}` : '--' },
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
        { label: 'Festival', value: trend.raw?.top_festival || trend.raw?.festival || '--' },
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
        nextPrediction: '🔮 Next Month Prediction',
        confidence: 'Confidence Score',
        why: '📊 Why This Happened',
        aiReasoning: '🤖 AI Reasoning',
        askAi: '💬 Ask AI About This Trend',
      }
    : language === 'tanglish'
    ? {
        title: '📈 Kirana Trends & Reports',
        refresh: '🔄 Refresh',
        pdf: '📄 PDF',
        json: '📊 JSON',
        loading: '⏳ Loading trends...',
        empty: 'Sidebar la oru trend select pannunga',
        weatherHero: 'Live Weather Intelligence',
        humidity: 'Humidity',
        wind: 'Wind',
        condition: 'Condition',
        playbook: 'Playbook',
        tip: 'Tip',
        rawData: '📋 Raw Data',
        insight: '💡 Insight',
        actions: '⚡ What To Do Now',
        nextPrediction: '🔮 Next Month Forecast',
        confidence: 'Confidence Score',
        why: '📊 Why This Happened',
        aiReasoning: '🤖 AI Reasoning',
        askAi: '💬 Ask AI About This Trend',
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
        nextPrediction: '🔮 Next Month Prediction',
        confidence: 'Confidence Score',
        why: '📊 Why This Happened',
        aiReasoning: '🤖 AI Reasoning',
        askAi: '💬 Ask AI About This Trend',
      }

  const actionPlaybook = {
    hinglish: {
      sales_trend: ['Top-selling SKU pe stock buffer 20% badhao', 'Slow SKU pe combo offer test karo'],
      hourly_rush: ['Peak hour ke pehle counter prep karo', 'Fast-moving items front rack pe rakho'],
      seasonal_trend: ['Next cycle demand ke liye inventory proactively plan karo', 'Peak month se pehle supplier order lock karo'],
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
    tanglish: {
      sales_trend: ['Top SKU-ku buffer stock increase pannunga', 'Slow SKU-ku combo offer test pannunga'],
      hourly_rush: ['Peak hour-ku munnadi counter prep pannunga', 'Fast-moving items front rack-la vainga'],
      seasonal_trend: ['Next cycle demand-ku stock early-a plan pannunga', 'Peak month munnadi supplier order lock pannunga'],
      stock_depletion: ['Critical items reorder same day podunga', 'Safety stock threshold set pannunga'],
      smart_reorder: ['Suggested reorder list supplier-oda confirm pannunga', 'High margin items-ku priority kudunga'],
      dead_stock: ['Dead stock-ku discount bundle launch pannunga', 'Shelf space fast movers-ku maathunga'],
      market_basket: ['Top pairs-ku combo pricing podunga', 'Co-buy items side by side display pannunga'],
      weather_trend: ['Weather-demand items front display la vainga', '2-day spike-ku quick reorder pannunga'],
    },
  }

  const getSeries = (trend) => {
    const d = getTrendDataRows(trend)
    if (!Array.isArray(d) || d.length === 0) return []
    return d.slice(0, 8).map((x) => (
      x.revenue ?? x.orders ?? x.total_qty ?? x.current_stock ?? x.count ?? x.qty ?? 0
    )).filter(v => typeof v === 'number' && !Number.isNaN(v))
  }

  const formatAvgDaily = (value) => {
    const n = Number(value)
    if (!Number.isFinite(n) || n <= 0) return '0'
    if (n < 0.1) return '<0.1'
    return n.toFixed(1)
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
  }, [refreshKey, language])

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
    if (!trend?.raw) return null

    const { type, raw } = trend
    const data = getTrendDataRows(trend)

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
      const chartData = data.map((d) => ({
        item: d.item || d.item_name || d.name || 'item',
        qty: Number(d.qty_sold ?? d.total_qty ?? d.qty ?? 0),
      }))
      return (
        <div style={styles.chartContainer}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" stroke="var(--text-muted)" />
              <YAxis dataKey="item" type="category" stroke="var(--text-muted)" width={100} />
              <Tooltip 
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
                labelStyle={{ color: 'var(--text)' }}
              />
              <Legend />
              <Bar dataKey="qty" fill="#8884D8" name="Quantity" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )
    }

    // Seasonal Trend - Line Chart with highlighted peak
    if (type === 'seasonal_trend' && data.length > 0) {
      const chartData = data.map((d) => ({
        month: d.month,
        qty: Number(d.qty ?? d.units ?? d.total_qty ?? 0),
      }))
      const ai = getSeasonalAI(trend)
      const peakMonth = ai?.peak?.month
      return (
        <div style={styles.chartContainer}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="month" stroke="var(--text-muted)" />
              <YAxis stroke="var(--text-muted)" />
              <Tooltip
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
                labelStyle={{ color: 'var(--text)' }}
                formatter={(value) => [`${Number(value).toLocaleString()} units`, 'Demand']}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="qty"
                stroke="#00C49F"
                strokeWidth={2}
                name="Units"
                dot={(props) => {
                  const { cx, cy, payload } = props
                  if (payload.month === peakMonth) return <circle cx={cx} cy={cy} r={6} fill="#ffbb28" stroke="#fff" strokeWidth={1.5} />
                  return <circle cx={cx} cy={cy} r={3.5} fill="#00C49F" />
                }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )
    }

    // Stock Depletion - Bar Chart
    if (type === 'stock_depletion' && data.length > 0) {
      const ai = getStockAI(trend)
      const chartData = (ai?.items || []).slice(0, 8).map((x) => ({
        item: x.item,
        current_stock: x.currentStock,
        threshold: x.threshold,
      }))
      return (
        <div style={styles.chartContainer}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="item" stroke="var(--text-muted)" angle={-45} textAnchor="end" height={80} />
              <YAxis stroke="var(--text-muted)" />
              <Tooltip 
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
                labelStyle={{ color: 'var(--text)' }}
              />
              <Legend />
              <Bar dataKey="current_stock" fill="#FF8042" name="Current Stock" />
              <Bar dataKey="threshold" fill="#ffbb28" name="Min Threshold" />
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
                    <span style={styles.trendHeroPill}>{getTrendDataRows(selectedTrend).length || 0} signal points</span>
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

              {selectedTrend.type === 'seasonal_trend' && (() => {
                const ai = getSeasonalAI(selectedTrend)
                if (!ai) return null
                return (
                  <>
                    <div style={{ ...styles.actionCard, borderColor: 'rgba(0,196,159,0.35)', background: 'linear-gradient(135deg, rgba(0,136,254,0.10), rgba(0,196,159,0.08))' }}>
                      <div style={styles.actionTitle}>{ui.nextPrediction}</div>
                      <div style={styles.actionItem}>{language === 'tanglish' ? `Next cycle expected demand: ~${ai.nextQty} units` : `Predicted demand (next cycle): ~${ai.nextQty} units`}</div>
                      <div style={styles.actionItem}>{language === 'tanglish' ? `Growth trend: ${ai.growthPct.toFixed(1)}%` : `Growth trend: ${ai.growthPct.toFixed(1)}%`}</div>
                      <div style={styles.actionItem}><strong>{ui.confidence}:</strong> {ai.confidence}%</div>
                    </div>

                    <div style={{ ...styles.insight, marginTop: 12 }}>
                      <strong>{ui.why}:</strong>
                      <div style={{ marginTop: 8 }}>• {ai.monthReason}</div>
                      <div style={{ marginTop: 4 }}>• {language === 'tanglish' ? `Peak month ${ai.peak.month} la demand ${ai.peak.qty.toLocaleString()} units reach aayiduchu.` : `Peak month ${ai.peak.month} reached ${ai.peak.qty.toLocaleString()} units.`}</div>
                    </div>

                    <div style={styles.chart}>
                      <details open={showAIReasoning}>
                        <summary
                          style={{ cursor: 'pointer', fontWeight: 600, marginTop: 14 }}
                          onClick={(e) => {
                            e.preventDefault()
                            setShowAIReasoning((prev) => !prev)
                          }}
                        >
                          {ui.aiReasoning}
                        </summary>
                        {showAIReasoning && (
                          <div style={styles.trendData}>
                            <div>Input: last {ai.series.length} month sales series + seasonal behavior</div>
                            <div>Processing: moving average + peak detection + heuristic scoring</div>
                            <div>Output: peak month, next-cycle forecast, confidence score, action plan</div>
                          </div>
                        )}
                      </details>
                    </div>

                    <div style={{ ...styles.actionCard, marginTop: 12 }}>
                      <div style={styles.actionTitle}>{ui.askAi}</div>
                      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                        <input
                          value={aiQuestion}
                          onChange={(e) => setAIQuestion(e.target.value)}
                          placeholder={language === 'tanglish' ? 'Example: why April high?' : 'Example: why April demand high?'}
                          style={{
                            flex: 1,
                            padding: '8px 10px',
                            background: 'var(--bg-card)',
                            border: '1px solid var(--border)',
                            borderRadius: 8,
                            color: 'var(--text)',
                          }}
                        />
                        <button
                          style={styles.button}
                          onClick={() => setAIReply(askSeasonalAI(selectedTrend, aiQuestion))}
                        >
                          Ask
                        </button>
                      </div>
                      {aiReply && <div style={styles.trendData}>{aiReply}</div>}
                    </div>
                  </>
                )
              })()}

              {selectedTrend.type === 'stock_depletion' && (() => {
                const ai = getStockAI(selectedTrend)
                if (!ai?.items?.length) return null
                const topItems = ai.items.slice(0, 3)
                return (
                  <>
                    <div style={{ ...styles.actionCard, borderColor: 'rgba(239,68,68,0.35)', background: 'linear-gradient(135deg, rgba(239,68,68,0.12), rgba(245,158,11,0.10))' }}>
                      <div style={styles.actionTitle}>Reorder Decision Engine</div>
                      {topItems.map((x) => (
                        <div key={x.item} style={{ ...styles.trendData, marginBottom: 10 }}>
                          <div><strong>{x.item}</strong></div>
                          <div>Current stock: {x.currentStock} units</div>
                          <div>Days left: {x.daysLeft.toFixed(1)} days</div>
                          <div>Avg daily sales: {formatAvgDaily(x.avgDaily)} units</div>
                          <div>Recommended: Reorder <strong>{x.reorderQty} units</strong> within 48 hours</div>
                        </div>
                      ))}
                    </div>

                    <div style={{ ...styles.insight, marginTop: 12 }}>
                      <strong>Risk Prediction</strong>
                      {ai.items.slice(0, 5).map((x) => (
                        <div key={`${x.item}-risk`} style={{ marginTop: 6 }}>
                          • {x.item} → <strong>{x.risk}</strong> risk, expected stockout: {x.stockoutDate.toLocaleDateString('en-GB')}
                        </div>
                      ))}
                    </div>

                    <div style={styles.chart}>
                      <details>
                        <summary style={{ cursor: 'pointer', fontWeight: 600, marginTop: 14 }}>🤖 AI Logic</summary>
                        <div style={styles.trendData}>
                          reorder_qty = (avg_daily_sales × lead_time) + safety_stock − current_stock
                          {ai.nextStockout && (
                            <>
                              {'\n'}
                              Example ({ai.nextStockout.item}): ({ai.nextStockout.avgDaily.toFixed(1)} × {ai.nextStockout.leadTime}) + {ai.nextStockout.safetyStock} − {ai.nextStockout.currentStock} = {ai.nextStockout.reorderQty}
                            </>
                          )}
                        </div>
                      </details>
                    </div>

                    <div style={{ ...styles.actionCard, marginTop: 12 }}>
                      <div style={styles.actionTitle}>💬 Ask AI - Stock Depletion</div>
                      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                        <input
                          value={aiQuestion}
                          onChange={(e) => setAIQuestion(e.target.value)}
                          placeholder="Example: which item will run out first?"
                          style={{
                            flex: 1,
                            padding: '8px 10px',
                            background: 'var(--bg-card)',
                            border: '1px solid var(--border)',
                            borderRadius: 8,
                            color: 'var(--text)',
                          }}
                        />
                        <button style={styles.button} onClick={() => setAIReply(askStockAI(selectedTrend, aiQuestion))}>Ask</button>
                        <button
                          style={styles.button}
                          onClick={() => setAIReply(`If no action in next 7 days: expected lost sales ₹${ai.totalLostValue7d.toLocaleString()}. Next stockout: ${ai.nextStockout?.item || '--'} (${ai.nextStockout ? ai.nextStockout.daysLeft.toFixed(1) : '--'} days).`)}
                        >
                          Simulate 7 Days
                        </button>
                      </div>
                      {aiReply && <div style={styles.trendData}>{aiReply}</div>}
                    </div>

                    <div style={{ ...styles.insight, marginTop: 12 }}>
                      <strong>AI Insight:</strong>
                      <div style={{ marginTop: 6 }}>
                        Fast-moving category depletion is increasing. Cross-signal suggests rush-hour demand may be accelerating stock burn rate for snack items.
                      </div>
                    </div>
                  </>
                )
              })()}

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
                {(selectedTrend.type === 'seasonal_trend'
                  ? seasonalActions(selectedTrend)
                  : selectedTrend.type === 'stock_depletion'
                  ? stockActions(selectedTrend)
                  : (actionPlaybook[language]?.[selectedTrend.type] || actionPlaybook.hinglish[selectedTrend.type] || [
                      language === 'tamil' || language === 'tanglish'
                        ? 'Data-a base panni next action decide pannunga'
                        : 'Use this trend to decide next operational action',
                    ])
                ).map((a, i) => (
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
