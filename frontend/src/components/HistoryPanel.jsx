import { useState } from 'react'
import { sendQuery } from '../api'

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
  title: {
    fontFamily: 'var(--font-display)',
    fontWeight: 700,
    fontSize: 26,
    letterSpacing: '-0.5px',
  },
  queryRow: {
    display: 'flex',
    gap: 10,
  },
  input: {
    flex: 1,
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: '10px 14px',
    color: 'var(--text-primary)',
    fontSize: 13,
    fontFamily: 'var(--font-mono)',
    outline: 'none',
    transition: 'border-color 0.2s',
  },
  runBtn: {
    padding: '10px 20px',
    background: 'var(--teal-dim)',
    border: '1px solid var(--border-glow)',
    borderRadius: 'var(--radius)',
    color: 'var(--teal)',
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
    fontWeight: 600,
    transition: 'all 0.15s',
  },
  resultCard: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    overflow: 'hidden',
  },
  resultHeader: {
    padding: '12px 18px',
    background: 'var(--bg-surface)',
    borderBottom: '1px solid var(--border)',
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  resultHeaderText: {
    fontFamily: 'var(--font-mono)',
    fontSize: 11,
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  resultBody: {
    padding: '16px 18px',
    fontFamily: 'var(--font-body)',
    fontSize: 14,
    color: 'var(--text-primary)',
    lineHeight: 1.6,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
  },
  tableHead: {
    background: 'var(--bg-surface)',
  },
  thCell: {
    padding: '8px 12px',
    textAlign: 'left',
    color: 'var(--text-muted)',
    fontSize: 10,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    borderBottom: '1px solid var(--border)',
  },
  tdCell: {
    padding: '10px 12px',
    color: 'var(--text-primary)',
    borderBottom: '1px solid var(--border)',
    fontSize: 12,
  },
  badge: (type) => ({
    padding: '2px 8px',
    borderRadius: 20,
    fontSize: 10,
    background: type === 'ADD' ? 'var(--teal-dim)' : type === 'SELL' ? '#ef444415' : '#f59e0b15',
    color: type === 'ADD' ? 'var(--teal)' : type === 'SELL' ? '#ef4444' : '#f59e0b',
    border: `1px solid ${type === 'ADD' ? 'var(--border-glow)' : type === 'SELL' ? '#ef444430' : '#f59e0b30'}`,
    fontFamily: 'var(--font-mono)',
  }),
  hint: {
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
    padding: '40px 20px',
    textAlign: 'center',
  },
  quickList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  quickItem: {
    padding: '10px 16px',
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    transition: 'all 0.15s',
    textAlign: 'left',
  },
  sectionLabel: {
    fontSize: 11,
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
}

const PRESETS = [
  'show all items',
  'which items are running low',
  'how much rice is left',
  'check wheat stock',
]

export default function HistoryPanel({ language = 'hinglish' }) {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [focused, setFocused] = useState(false)

  async function run(q) {
    const text = q || query
    if (!text.trim() || loading) return
    setLoading(true)
    setResult(null)
    try {
      const res = await sendQuery(text, language)
      setResult(res)
    } catch {
      setResult({ success: false, response: 'API error. Is the backend running?' })
    }
    setLoading(false)
  }

  const rows = result?.rows || []

  return (
    <div style={s.root}>
      <div style={s.title}>
        {language === 'tamil' ? 'Query History - Varalaru' : 'Query History'} <span style={{ color: 'var(--teal)' }}>🕒</span>
      </div>

      {/* Query input */}
      <div style={s.queryRow}>
        <input
          style={{ ...s.input, borderColor: focused ? 'var(--teal)' : 'var(--border)' }}
          placeholder={language === 'tamil' ? 'Type query here...' : 'Enter any query...'}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={e => e.key === 'Enter' && run()}
        />
        <button
          style={s.runBtn}
          onClick={() => run()}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--teal)'; e.currentTarget.style.color = '#050c0c' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'var(--teal-dim)'; e.currentTarget.style.color = 'var(--teal)' }}
        >
          {loading ? '...' : '▶ Run'}
        </button>
      </div>

      {/* Preset queries */}
      <div>
        <div style={{ ...s.sectionLabel, marginBottom: 10 }}>Quick queries</div>
        <div style={s.quickList}>
          {PRESETS.map(p => (
            <button
              key={p}
              style={s.quickItem}
              onClick={() => { setQuery(p); run(p) }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--teal)'; e.currentTarget.style.color = 'var(--teal)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
            >
              → {p}
            </button>
          ))}
        </div>
      </div>

      {/* Result */}
      {result && (
        <div style={{ ...s.resultCard, animation: 'fadeUp 0.25s ease' }}>
          <div style={s.resultHeader}>
            <span style={s.badge(result.intent)}>{result.intent || 'RESULT'}</span>
            <span style={s.resultHeaderText}>
              {result.sql || 'no sql'}
            </span>
          </div>

          <div style={s.resultBody}>
            <div style={{
              marginBottom: rows.length > 0 ? 16 : 0,
              color: result.success ? 'var(--text-primary)' : '#ef4444',
            }}>
              {result.response}
            </div>

            {rows.length > 1 && (
              <table style={s.table}>
                <thead style={s.tableHead}>
                  <tr>
                    {Object.keys(rows[0]).map(k => (
                      <th key={k} style={s.thCell}>{k}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'var(--bg-surface)' }}>
                      {Object.values(row).map((v, j) => (
                        <td key={j} style={s.tdCell}>{String(v)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {!result && !loading && (
        <div style={s.hint}>
          Run a query or select a preset above
        </div>
      )}
    </div>
  )
}
