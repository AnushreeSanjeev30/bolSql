import { useState, useEffect, useRef } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { getInventory, importSalesCsv, clearInventory } from '../api'

const s = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    padding: '32px 40px',
    gap: 28,
    animation: 'fadeIn 0.3s ease',
    overflowY: 'auto',
  },
  header: {
    display: 'flex',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
  },
  title: {
    fontFamily: 'var(--font-display)',
    fontWeight: 700,
    fontSize: 26,
    letterSpacing: '-0.5px',
  },
  headerBtns: {
    display: 'flex',
    gap: 10,
    alignItems: 'center',
  },
  refreshBtn: {
    padding: '8px 16px',
    borderRadius: 'var(--radius)',
    border: '1px solid var(--border)',
    color: 'var(--text-secondary)',
    fontSize: 12,
    fontFamily: 'var(--font-mono)',
    transition: 'all 0.15s',
    background: 'transparent',
    cursor: 'pointer',
  },
  importBtn: {
    padding: '8px 16px',
    borderRadius: 'var(--radius)',
    border: '1px solid var(--border-glow)',
    color: 'var(--teal)',
    fontSize: 12,
    fontFamily: 'var(--font-mono)',
    transition: 'all 0.15s',
    background: 'var(--teal-dim)',
    cursor: 'pointer',
  },
  exportBtn: {
    padding: '8px 16px',
    borderRadius: 'var(--radius)',
    border: '1px solid var(--border)',
    color: 'var(--text-secondary)',
    fontSize: 12,
    fontFamily: 'var(--font-mono)',
    transition: 'all 0.15s',
    background: 'var(--bg-card)',
    cursor: 'pointer',
  },
  clearBtn: {
    padding: '8px 16px',
    borderRadius: 'var(--radius)',
    border: '1px solid #ef444460',
    color: '#ef4444',
    fontSize: 12,
    fontFamily: 'var(--font-mono)',
    transition: 'all 0.15s',
    background: 'rgba(239,68,68,0.10)',
    cursor: 'pointer',
  },
  statsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 16,
  },
  statCard: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: '18px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  statLabel: {
    fontSize: 11,
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  statValue: {
    fontSize: 28,
    fontFamily: 'var(--font-display)',
    fontWeight: 700,
    color: 'var(--teal)',
    lineHeight: 1.1,
  },
  statSub: {
    fontSize: 11,
    color: 'var(--text-secondary)',
  },
  chartCard: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: '20px',
  },
  chartTitle: {
    fontSize: 12,
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-secondary)',
    marginBottom: 14,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  table: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    maxHeight: 'calc(100vh - 550px)',
  },
  tableHeader: {
    display: 'grid',
    gridTemplateColumns: '1fr 120px 80px 100px 80px',
    padding: '10px 20px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg-surface)',
    position: 'sticky',
    top: 0,
    zIndex: 10,
    flexShrink: 0,
  },
  tableBody: {
    overflowY: 'auto',
    flex: 1,
  },
  th: {
    fontSize: 10,
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  tableRow: (low) => ({
    display: 'grid',
    gridTemplateColumns: '1fr 120px 80px 100px 80px',
    padding: '13px 20px',
    borderBottom: '1px solid var(--border)',
    alignItems: 'center',
    transition: 'background 0.1s',
    background: low ? '#f59e0b08' : 'transparent',
    cursor: 'default',
  }),
  td: {
    fontSize: 13,
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-body)',
  },
  tdMono: {
    fontSize: 13,
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-primary)',
  },
  badge: (low) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: '2px 8px',
    borderRadius: 20,
    fontSize: 10,
    fontFamily: 'var(--font-mono)',
    background: low ? '#f59e0b20' : 'var(--teal-dim)',
    color: low ? 'var(--warning)' : 'var(--teal)',
    border: `1px solid ${low ? '#f59e0b40' : 'var(--border-glow)'}`,
  }),
  empty: {
    padding: '60px 20px',
    textAlign: 'center',
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
  },
  spinner: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 60,
  },
  spinnerInner: {
    width: 28,
    height: 28,
    border: '2px solid var(--border)',
    borderTopColor: 'var(--teal)',
    borderRadius: '50%',
    animation: 'spin 0.7s linear infinite',
  },

  // CSV Modal
  overlay: {
    position: 'fixed',
    inset: 0,
    background: '#00000090',
    backdropFilter: 'blur(4px)',
    zIndex: 100,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    animation: 'fadeIn 0.2s ease',
  },
  modal: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    width: 560,
    maxHeight: '80vh',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    animation: 'fadeUp 0.25s ease',
  },
  modalHeader: {
    padding: '20px 24px',
    borderBottom: '1px solid var(--border)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  modalTitle: {
    fontFamily: 'var(--font-display)',
    fontWeight: 700,
    fontSize: 18,
  },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    color: 'var(--text-muted)',
    fontSize: 20,
    cursor: 'pointer',
    lineHeight: 1,
    padding: 4,
  },
  modalBody: {
    padding: '24px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
  },
  dropZone: (dragging) => ({
    border: `2px dashed ${dragging ? 'var(--teal)' : 'var(--border)'}`,
    borderRadius: 'var(--radius-lg)',
    padding: '36px 24px',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    background: dragging ? 'var(--teal-dim)' : 'var(--bg-surface)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 10,
  }),
  dropIcon: { fontSize: 36 },
  dropText: {
    color: 'var(--text-secondary)',
    fontSize: 13,
    fontFamily: 'var(--font-body)',
  },
  dropHint: {
    color: 'var(--text-muted)',
    fontSize: 11,
    fontFamily: 'var(--font-mono)',
  },
  sampleBox: {
    background: 'var(--bg-base)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: '14px 16px',
  },
  sampleLabel: {
    fontSize: 10,
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: 8,
  },
  sampleCode: {
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
    color: 'var(--teal)',
    lineHeight: 1.8,
    whiteSpace: 'pre',
  },
  previewTable: {
    width: '100%',
    borderCollapse: 'collapse',
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
  },
  previewTh: {
    padding: '6px 10px',
    textAlign: 'left',
    color: 'var(--text-muted)',
    fontSize: 10,
    textTransform: 'uppercase',
    borderBottom: '1px solid var(--border)',
  },
  previewTd: {
    padding: '8px 10px',
    color: 'var(--text-primary)',
    borderBottom: '1px solid var(--border)',
    fontSize: 12,
  },
  importConfirmBtn: {
    padding: '12px 24px',
    background: 'var(--teal)',
    color: '#050c0c',
    border: 'none',
    borderRadius: 'var(--radius)',
    fontFamily: 'var(--font-display)',
    fontWeight: 700,
    fontSize: 14,
    cursor: 'pointer',
    transition: 'background 0.15s',
    width: '100%',
  },
  successBanner: {
    background: 'var(--teal-dim)',
    border: '1px solid var(--border-glow)',
    borderRadius: 'var(--radius)',
    padding: '12px 16px',
    color: 'var(--teal)',
    fontFamily: 'var(--font-mono)',
    fontSize: 13,
    textAlign: 'center',
  },
  errorBanner: {
    background: '#ef444415',
    border: '1px solid #ef444430',
    borderRadius: 'var(--radius)',
    padding: '12px 16px',
    color: '#ef4444',
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
  },
  mapRow: {
    display: 'grid',
    gridTemplateColumns: '1fr auto 1fr',
    alignItems: 'center',
    gap: 12,
    marginBottom: 8,
  },
  mapLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
    color: 'var(--text-secondary)',
  },
  mapArrow: {
    color: 'var(--teal)',
    fontFamily: 'var(--font-mono)',
    fontSize: 14,
  },
  select: {
    background: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: '6px 10px',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
    outline: 'none',
    width: '100%',
  },
}

const SAMPLE_CSV = `name,quantity,unit,price
atta,50,kg,35
chawal,30,kg,60
dal,20,kg,90
tel,15,litre,130
chini,25,kg,45`

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '8px 12px',
      fontFamily: 'var(--font-mono)',
      fontSize: 12,
      color: 'var(--text-primary)',
    }}>
      <div style={{ color: 'var(--teal)' }}>{payload[0].payload.name}</div>
      <div>{payload[0].value} {payload[0].payload.unit}</div>
    </div>
  )
}

function parseCSV(text) {
  const lines = text.trim().split('\n').filter(Boolean)
  if (lines.length < 2) throw new Error('CSV must have header + at least 1 row')
  const headers = lines[0].split(',').map(h => h.trim().toLowerCase())
  const rows = lines.slice(1).map(line => {
    const vals = line.split(',').map(v => v.trim())
    const obj = {}
    headers.forEach((h, i) => { obj[h] = vals[i] || '' })
    return obj
  })
  return { headers, rows }
}

function normalizeHeader(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[()]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

function autoDetectColumns(headers) {
  const mapping = { name: '', quantity: '', unit: '', price: '', date: '', time: '' }

  headers.forEach(header => {
    const key = normalizeHeader(header)
    if (['name', 'item', 'product', 'item_name', 'product_name', 'productname', 'naam'].includes(key)) mapping.name = header
    if (['quantity', 'qty', 'stock', 'amount', 'matra'].includes(key)) mapping.quantity = header
    if (['unit', 'units', 'uom', 'ikai'].includes(key)) mapping.unit = header
    if (['price', 'cost', 'rate', 'mrp', 'daam', 'price_usd', 'selling_price'].includes(key)) mapping.price = header
    if (['date', 'order_date', 'timestamp', 'datetime', 'sold_at'].includes(key)) mapping.date = header
    if (['time', 'clock', 'time_of_day'].includes(key)) mapping.time = header
  })

  return mapping
}

function buildCsvCapabilities(headers, rows) {
  const normalizedHeaders = headers.map(normalizeHeader)
  const hasName = normalizedHeaders.some(key => ['name', 'item', 'product', 'item_name', 'product_name', 'productname'].includes(key))
  const hasQuantity = normalizedHeaders.some(key => ['quantity', 'qty', 'stock', 'amount'].includes(key))
  const hasDate = normalizedHeaders.some(key => ['date', 'order_date', 'timestamp', 'datetime', 'sold_at'].includes(key))
  const hasTime = normalizedHeaders.some(key => ['time', 'clock', 'time_of_day'].includes(key))
  const distinctMonths = new Set()

  rows.forEach((row) => {
    const rawDate = String(row.date || row.order_date || row.timestamp || row.datetime || row.sold_at || '').trim()
    if (!rawDate) return
    const monthMatch = rawDate.match(/\b(\d{4}-\d{2}|\d{2}[-/]\d{4}|\d{4}\/\d{2})\b/)
    if (monthMatch) distinctMonths.add(monthMatch[1])
  })

  return [
    {
      title: 'Sales Trend',
      description: 'Monthly/weekly revenue over time',
      available: hasDate && hasQuantity,
    },
    {
      title: 'Hourly Rush',
      description: 'Busiest hours of the day for sales',
      available: hasDate && hasTime,
    },
    {
      title: 'Product Demand',
      description: 'Top-selling products by volume or revenue',
      available: hasName && hasQuantity,
    },
    {
      title: 'Dead Stock',
      description: 'Products with very low or no sales',
      available: hasName && hasQuantity,
    },
    {
      title: 'Seasonal Trend',
      description: 'Which products sell more in which months',
      available: hasDate && (distinctMonths.size >= 1),
    },
    {
      title: 'Festival Trend',
      description: 'Sales spikes around known festival dates',
      available: hasDate,
    },
  ]
}

function countUniqueProducts(rows) {
  const unique = new Set()

  rows.forEach((row) => {
    const name = String(row.product_name || row.item_name || row.name || row.product || row.item || row.sku || '').trim().toLowerCase()
    if (name) unique.add(name)
  })

  return unique.size
}

function CSVModal({ onClose, onImported }) {
  const [dragging, setDragging] = useState(false)
  const [parsed, setParsed] = useState(null)
  const [headers, setHeaders] = useState([])
  const [rawCsv, setRawCsv] = useState('')
  const [importing, setImporting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const fileRef = useRef()

  function handleFile(file) {
    if (!file) return
    if (!file.name.endsWith('.csv') && file.type !== 'text/csv') {
      setError('Sirf CSV file upload karo')
      return
    }
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const csvText = String(e.target.result || '')
        const { headers, rows } = parseCSV(csvText)
        setHeaders(headers)
        setParsed(rows)
        setRawCsv(csvText)
        setError(null)
      } catch (err) {
        setError(err.message)
      }
    }
    reader.readAsText(file)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  function downloadSample() {
    const blob = new Blob([
      'name,quantity,unit,price,category,expiry_date\nAloo,50,kg,32,vegetable,2026-04-30\nAtta,20,kg,45,grains,2026-12-31\nChini,15,kg,55,groceries,2027-01-15'
    ], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'inventory_sample.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const csvCapabilities = parsed ? buildCsvCapabilities(headers, parsed) : []

  async function doImport() {
    if (!parsed || !rawCsv) {
      setError('Pehle CSV file upload karo')
      return
    }
    setImporting(true)
    setError(null)

    try {
      const response = await importSalesCsv(rawCsv, 'snapshot')
      setResult({
        success: response.success,
        message: response.message,
        rowsProcessed: response.rows_processed,
        rowsSucceeded: response.rows_succeeded,
        rowsFailed: response.rows_failed,
        inventoryUpdated: response.inventory_updated,
        trendsRefreshed: response.trends_refreshed,
        warnings: response.warnings || [],
        error: response.error,
      })

      if (response.success) {
        onImported()
      }
    } catch (err) {
      setResult(null)
      setError(err.message || 'CSV import failed')
    } finally {
      setImporting(false)
    }
  }

  return (
    <div style={s.overlay} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={s.modal}>
        <div style={s.modalHeader}>
          <div style={s.modalTitle}>📥 Inventory CSV Import</div>
          <button style={s.closeBtn} onClick={onClose}>×</button>
        </div>

        <div style={s.modalBody}>
          {!parsed ? (
            <>
              {/* Drop zone */}
              <div
                style={s.dropZone(dragging)}
                onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileRef.current.click()}
              >
                <div style={s.dropIcon}>📂</div>
                <div style={s.dropText}>Inventory CSV yahan drop karo ya click karke select karo</div>
                <div style={s.dropHint}>Supported: .csv files only</div>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".csv"
                  style={{ display: 'none' }}
                  onChange={(e) => handleFile(e.target.files[0])}
                />
              </div>

              {/* Sample format */}
              <div style={s.sampleBox}>
                <div style={s.sampleLabel}>Expected inventory CSV format</div>
                <div style={s.sampleCode}>{'name,quantity,unit,price,category,expiry_date\nAloo,50,kg,32,vegetable,2026-04-30'}</div>
              </div>

              <button
                style={{ ...s.importConfirmBtn, background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                onClick={downloadSample}
              >
                ↓ Inventory CSV Sample Download Karo
              </button>

              {error && <div style={s.errorBanner}>❌ {error}</div>}
            </>
          ) : result ? (
            <>
              <div style={s.successBanner}>
                {result.success ? '✅ ' : '❌ '}{result.message}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
                <div>Rows processed: {result.rowsProcessed ?? 0}</div>
                <div>Rows imported: {result.rowsSucceeded ?? 0}</div>
                <div>Rows failed: {result.rowsFailed ?? 0}</div>
                <div>Inventory updated: {result.inventoryUpdated ? 'yes' : 'no'}</div>
                <div>Trends refreshed: {result.trendsRefreshed ? 'yes' : 'no'}</div>
                {Array.isArray(result.warnings) && result.warnings.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    {result.warnings.slice(0, 5).map((warning, index) => (
                      <div key={index}>⚠️ {warning}</div>
                    ))}
                  </div>
                )}
                {result.error && <div style={{ color: 'var(--warning)', marginTop: 8 }}>Error: {result.error}</div>}
              </div>
              <button style={s.importConfirmBtn} onClick={onClose}>
                Done → Inventory Dekho
              </button>
            </>
          ) : (
            <>
              {/* Auto-detected columns */}
              <div>
                <div style={{ ...s.sampleLabel, marginBottom: 12 }}>
                  Auto-detected columns
                </div>
                {(() => {
                  const autoMap = autoDetectColumns(headers)
                  const rows = [
                    ['Product Name', autoMap.name || 'not found'],
                    ['Quantity', autoMap.quantity || 'not found'],
                    ['Unit', autoMap.unit || 'optional / not found'],
                    ['Price', autoMap.price || 'optional / not found'],
                    ['Date', autoMap.date || 'optional / not found'],
                    ['Time', autoMap.time || 'optional / not found'],
                  ]
                  return rows.map(([label, value]) => (
                    <div key={label} style={s.mapRow}>
                      <div style={s.mapLabel}>{label}</div>
                      <div style={s.mapArrow}>→</div>
                      <div style={{ ...s.select, display: 'flex', alignItems: 'center' }}>{value}</div>
                    </div>
                  ))
                })()}
              </div>

              {/* CSV-powered analytics coverage */}
              <div>
                <div style={{ ...s.sampleLabel, marginBottom: 12 }}>
                  Analytics available from this CSV
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
                  {csvCapabilities.map((item) => (
                    <div
                      key={item.title}
                      style={{
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius)',
                        padding: '12px 14px',
                        background: item.available ? 'rgba(0,196,159,0.08)' : 'rgba(255,255,255,0.03)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginBottom: 4 }}>
                        <div style={{ fontWeight: 700, fontSize: 13 }}>{item.title}</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: item.available ? 'var(--teal)' : 'var(--text-muted)' }}>
                          {item.available ? 'Yes' : 'No'}
                        </div>
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                        {item.description}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Preview */}
              <div>
                <div style={{ ...s.sampleLabel, marginBottom: 8 }}>
                  Preview (first 5 rows)
                </div>
                <div style={{ overflowX: 'auto', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}>
                  <table style={s.previewTable}>
                    <thead>
                      <tr style={{ background: 'var(--bg-surface)' }}>
                        {headers.map(h => <th key={h} style={s.previewTh}>{h}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {parsed.slice(0, 5).map((row, i) => (
                        <tr key={i}>
                          {headers.map(h => <td key={h} style={s.previewTd}>{row[h]}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 6 }}>
                  Total {parsed.length} rows milein · {countUniqueProducts(parsed)} unique products
                </div>
              </div>

              {error && <div style={s.errorBanner}>❌ {error}</div>}

              <button
                style={{ ...s.importConfirmBtn, opacity: importing ? 0.7 : 1 }}
                onClick={doImport}
                disabled={importing}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--teal-mid)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'var(--teal)' }}
              >
                {importing ? `⏳ Importing... (${parsed.length} rows)` : `✓ ${parsed.length} Rows Import Karo`}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default function InventoryPanel({ language = 'hinglish', onDataUpdated }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCSV, setShowCSV] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await getInventory()
      setItems(data)
    } catch {
      setError('API se data nahi mila. Backend chal raha hai?')
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  function csvEscape(value) {
    if (value === null || value === undefined) return ''
    const str = String(value)
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`
    }
    return str
  }

  function downloadInventoryCSV() {
    const headers = ['name', 'quantity', 'unit', 'price', 'category', 'expiry_date']
    const rows = items.map(item => [
      item.name,
      item.quantity,
      item.unit,
      item.price ?? '',
      item.category ?? '',
      item.expiry_date ?? '',
    ])

    const lines = [
      headers.join(','),
      ...rows.map(row => row.map(csvEscape).join(',')),
    ]

    const csv = lines.join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)

    const now = new Date()
    const stamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`
    const a = document.createElement('a')
    a.href = url
    a.download = `inventory_export_${stamp}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function handleClearInventory() {
    const ok = window.confirm('Clear inventory completely? This will delete all items from inventory table.')
    if (!ok) return

    try {
      const result = await clearInventory()
      if (!result?.success) throw new Error(result?.error || result?.message || 'Failed to clear inventory')
      await load()
      if (typeof onDataUpdated === 'function') onDataUpdated()
      window.alert(`Inventory cleared. Deleted ${result.items_deleted || 0} items.`)
    } catch (err) {
      window.alert(err?.message || 'Inventory clear failed')
    }
  }

  const lowStock = items.filter(i => i.quantity < 5)
  const totalItems = items.length
  const chartData = items
    .slice()
    .sort((a, b) => b.quantity - a.quantity)
    .slice(0, 8)

  return (
    <div style={s.root}>
      {showCSV && (
        <CSVModal
          onClose={() => setShowCSV(false)}
          onImported={() => {
            setShowCSV(false)
            load()
            if (typeof onDataUpdated === 'function') onDataUpdated()
          }}
        />
      )}

      <div style={s.header}>
        <div style={s.title}>
          {language === 'tamil' ? 'Inventory - Samanukkam' : 'Inventory'} <span style={{ color: 'var(--teal)' }}>📦</span>
        </div>
        <div style={s.headerBtns}>
          <button
            style={s.exportBtn}
            onClick={downloadInventoryCSV}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--teal)'; e.currentTarget.style.color = 'var(--teal)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
          >
            ↓ CSV Download
          </button>
          <button
            style={s.importBtn}
            onClick={() => setShowCSV(true)}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--teal)'; e.currentTarget.style.color = '#050c0c' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'var(--teal-dim)'; e.currentTarget.style.color = 'var(--teal)' }}
          >
            ↑ CSV Import
          </button>
          <button
            style={s.refreshBtn}
            onClick={load}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--teal)'; e.currentTarget.style.color = 'var(--teal)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
          >
            ↺ Refresh
          </button>
          <button
            style={s.clearBtn}
            onClick={handleClearInventory}
            onMouseEnter={e => { e.currentTarget.style.background = '#ef4444'; e.currentTarget.style.color = '#fff' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.10)'; e.currentTarget.style.color = '#ef4444' }}
          >
            🗑 Clear Inventory
          </button>
        </div>
      </div>

      {/* Stats */}
      <div style={s.statsRow}>
        <div style={s.statCard}>
          <div style={s.statLabel}>Total Items</div>
          <div style={s.statValue}>{totalItems}</div>
          <div style={s.statSub}>products in inventory</div>
        </div>
        <div style={{ ...s.statCard, borderColor: lowStock.length > 0 ? '#f59e0b40' : 'var(--border)' }}>
          <div style={s.statLabel}>Low Stock</div>
          <div style={{ ...s.statValue, color: lowStock.length > 0 ? 'var(--warning)' : 'var(--teal)' }}>
            {lowStock.length}
          </div>
          <div style={s.statSub}>items below 5 units</div>
        </div>
        <div style={s.statCard}>
          <div style={s.statLabel}>Top Item</div>
          <div style={{ ...s.statValue, fontSize: 20 }}>
            {items[0]?.name || '—'}
          </div>
          <div style={s.statSub}>{items[0] ? `${items[0].quantity} ${items[0].unit}` : 'no data'}</div>
        </div>
      </div>

      {/* Chart */}
      {!loading && chartData.length > 0 && (
        <div style={s.chartCard}>
          <div style={s.chartTitle}>Stock Levels</div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={chartData} barSize={28} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <XAxis
                dataKey="name"
                tick={{ fill: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--bg-hover)' }} />
              <Bar dataKey="quantity" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={entry.quantity < 5 ? '#f59e0b' : 'var(--teal)'}
                    opacity={0.85}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Table */}
      <div style={s.table}>
        <div style={s.tableHeader}>
          <div style={s.th}>Item</div>
          <div style={s.th}>Quantity</div>
          <div style={s.th}>Unit</div>
          <div style={s.th}>Price</div>
          <div style={s.th}>Status</div>
        </div>

        <div style={s.tableBody}>
          {loading ? (
            <div style={s.spinner}><div style={s.spinnerInner} /></div>
          ) : error ? (
            <div style={s.empty}>{error}</div>
          ) : items.length === 0 ? (
            <div style={s.empty}>
                  Inventory khaali hai —{' '}
              <span style={{ color: 'var(--teal)', cursor: 'pointer' }} onClick={() => setShowCSV(true)}>
                    inventory CSV import karo
              </span>
              {' '}ya voice se add karo
            </div>
          ) : (
            items.map((item) => {
              const low = item.quantity < 5
              return (
                <div
                  key={item.id}
                  style={s.tableRow(low)}
                  onMouseEnter={e => { e.currentTarget.style.background = low ? '#f59e0b10' : 'var(--bg-hover)' }}
                  onMouseLeave={e => { e.currentTarget.style.background = low ? '#f59e0b08' : 'transparent' }}
                >
                  <div style={s.td}>{item.name}</div>
                  <div style={{ ...s.tdMono, color: low ? 'var(--warning)' : 'var(--teal)' }}>{item.quantity}</div>
                  <div style={{ ...s.tdMono, color: 'var(--text-secondary)', fontSize: 11 }}>{item.unit}</div>
                  <div style={{ ...s.tdMono, color: 'var(--text-secondary)' }}>{item.price ? `₹${item.price}` : '—'}</div>
                  <div><span style={s.badge(low)}>{low ? '⚠ Low' : '● OK'}</span></div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
