import { useState, useEffect, useRef } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { getInventory, sendQuery } from '../api'

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
  },
  tableHeader: {
    display: 'grid',
    gridTemplateColumns: '1fr 120px 80px 100px 80px',
    padding: '10px 20px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg-surface)',
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

function CSVModal({ onClose, onImported }) {
  const [dragging, setDragging] = useState(false)
  const [parsed, setParsed] = useState(null)
  const [headers, setHeaders] = useState([])
  const [mapping, setMapping] = useState({ name: '', quantity: '', unit: '', price: '' })
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
        const { headers, rows } = parseCSV(e.target.result)
        setHeaders(headers)
        setParsed(rows)
        setError(null)
        // Auto-map obvious column names
        const autoMap = { name: '', quantity: '', unit: '', price: '' }
        headers.forEach(h => {
          if (['name', 'item', 'product', 'item_name', 'product_name', 'naam'].includes(h)) autoMap.name = h
          if (['quantity', 'qty', 'stock', 'amount', 'matra'].includes(h)) autoMap.quantity = h
          if (['unit', 'units', 'uom', 'ikai'].includes(h)) autoMap.unit = h
          if (['price', 'cost', 'rate', 'mrp', 'daam'].includes(h)) autoMap.price = h
        })
        setMapping(autoMap)
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
    const blob = new Blob([SAMPLE_CSV], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'sample_inventory.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  async function doImport() {
    if (!parsed || !mapping.name || !mapping.quantity) {
      setError('Name aur Quantity columns select karo')
      return
    }
    setImporting(true)
    setError(null)

    let successCount = 0
    let failCount = 0

    for (const row of parsed) {
      const name = row[mapping.name]?.trim()
      const quantity = parseFloat(row[mapping.quantity])
      const unit = mapping.unit ? (row[mapping.unit]?.trim() || 'piece') : 'piece'
      const price = mapping.price ? (parseFloat(row[mapping.price]) || 0) : 0

      if (!name || isNaN(quantity)) { failCount++; continue }

      try {
        const data = await sendQuery(`${quantity} ${unit} ${name} add karo`)
        if (data.success) successCount++
        else failCount++
      } catch {
        failCount++
      }
    }

    setImporting(false)
    setResult({ successCount, failCount })
    if (successCount > 0) onImported()
  }

  return (
    <div style={s.overlay} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={s.modal}>
        <div style={s.modalHeader}>
          <div style={s.modalTitle}>📥 CSV Import</div>
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
                <div style={s.dropText}>CSV file yahan drop karo ya click karke select karo</div>
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
                <div style={s.sampleLabel}>Expected CSV format</div>
                <div style={s.sampleCode}>{SAMPLE_CSV}</div>
              </div>

              <button
                style={{ ...s.importConfirmBtn, background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                onClick={downloadSample}
              >
                ↓ Sample CSV Download Karo
              </button>

              {error && <div style={s.errorBanner}>❌ {error}</div>}
            </>
          ) : result ? (
            <>
              <div style={s.successBanner}>
                ✅ Import complete! {result.successCount} items add hue, {result.failCount} skip hue.
              </div>
              <button style={s.importConfirmBtn} onClick={onClose}>
                Done → Inventory Dekho
              </button>
            </>
          ) : (
            <>
              {/* Column mapping */}
              <div>
                <div style={{ ...s.sampleLabel, marginBottom: 12 }}>
                  Column Mapping — CSV ke columns select karo
                </div>
                {[
                  { field: 'name',     label: 'Item Name *', required: true },
                  { field: 'quantity', label: 'Quantity *',  required: true },
                  { field: 'unit',     label: 'Unit',        required: false },
                  { field: 'price',    label: 'Price',       required: false },
                ].map(({ field, label, required }) => (
                  <div key={field} style={s.mapRow}>
                    <div style={s.mapLabel}>{label}</div>
                    <div style={s.mapArrow}>→</div>
                    <select
                      style={s.select}
                      value={mapping[field]}
                      onChange={e => setMapping(m => ({ ...m, [field]: e.target.value }))}
                    >
                      <option value="">-- select column --</option>
                      {headers.map(h => <option key={h} value={h}>{h}</option>)}
                    </select>
                  </div>
                ))}
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
                  Total {parsed.length} rows milein
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
                {importing ? `⏳ Importing... (${parsed.length} items)` : `✓ ${parsed.length} Items Import Karo`}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default function InventoryPanel() {
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
          onImported={() => { setShowCSV(false); load() }}
        />
      )}

      <div style={s.header}>
        <div style={s.title}>
          Inventory <span style={{ color: 'var(--teal)' }}>📦</span>
        </div>
        <div style={s.headerBtns}>
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

        {loading ? (
          <div style={s.spinner}><div style={s.spinnerInner} /></div>
        ) : error ? (
          <div style={s.empty}>{error}</div>
        ) : items.length === 0 ? (
          <div style={s.empty}>
            Inventory khaali hai —{' '}
            <span style={{ color: 'var(--teal)', cursor: 'pointer' }} onClick={() => setShowCSV(true)}>
              CSV import karo
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
  )
}
