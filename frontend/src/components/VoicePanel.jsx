import { useState, useRef, useEffect } from 'react'
import { sendQuery } from '../api'
import { ResponsiveContainer, BarChart, XAxis, YAxis, Tooltip, Bar } from 'recharts'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'

const s = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    padding: '32px 40px',
    gap: 28,
    animation: 'fadeIn 0.3s ease',
  },
  header: {
    display: 'flex',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 16,
  },
  title: {
    fontFamily: 'var(--font-display)',
    fontWeight: 700,
    fontSize: 26,
    color: 'var(--text-primary)',
    letterSpacing: '-0.5px',
  },
  subtitle: {
    color: 'var(--text-secondary)',
    fontSize: 13,
  },
  chatArea: {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    padding: '4px 0',
  },
  emptyState: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
    opacity: 0.5,
  },
  emptyIcon: { fontSize: 48 },
  emptyText: {
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 1.8,
  },
  bubble: (type) => ({
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    alignSelf: type === 'user' ? 'flex-end' : 'flex-start',
    maxWidth: '72%',
    animation: 'fadeUp 0.25s ease',
  }),
  bubbleLabel: (type) => ({
    fontSize: 10,
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    textAlign: type === 'user' ? 'right' : 'left',
  }),
  bubbleContent: (type, success) => ({
    padding: '12px 16px',
    borderRadius: type === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
    background: type === 'user'
      ? 'var(--teal-dim)'
      : success === false
        ? '#ef444415'
        : 'var(--bg-card)',
    border: type === 'user'
      ? '1px solid var(--border-glow)'
      : success === false
        ? '1px solid #ef444430'
        : '1px solid var(--border)',
    color: type === 'user' ? 'var(--teal)' : 'var(--text-primary)',
    fontSize: 13.5,
    lineHeight: 1.6,
    fontFamily: type === 'user' ? 'var(--font-mono)' : 'var(--font-body)',
  }),
  sqlChip: {
    fontFamily: 'var(--font-mono)',
    fontSize: 11,
    color: 'var(--text-muted)',
    background: 'var(--bg-base)',
    border: '1px solid var(--border)',
    borderRadius: 6,
    padding: '6px 10px',
    marginTop: 4,
    wordBreak: 'break-all',
    lineHeight: 1.5,
  },
  inputRow: {
    display: 'flex',
    gap: 10,
    alignItems: 'flex-end',
  },
  inputWrap: {
    flex: 1,
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: '12px 16px',
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    transition: 'border-color 0.2s',
  },
  input: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: 'var(--text-primary)',
    fontSize: 14,
    fontFamily: 'var(--font-body)',
  },
  sendBtn: {
    padding: '12px 22px',
    background: 'var(--teal)',
    color: '#050c0c',
    borderRadius: 'var(--radius-lg)',
    fontWeight: 700,
    fontSize: 13,
    fontFamily: 'var(--font-display)',
    letterSpacing: '0.3px',
    transition: 'all 0.15s',
    whiteSpace: 'nowrap',
  },
  micBtn: (recording) => ({
    width: 46,
    height: 46,
    borderRadius: '50%',
    background: recording ? '#ef4444' : 'var(--bg-card)',
    border: recording ? '1px solid #ef444460' : '1px solid var(--border)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 18,
    transition: 'all 0.2s',
    flexShrink: 0,
    boxShadow: recording ? '0 0 20px #ef444440' : 'none',
    animation: recording ? 'glow-pulse 1.5s infinite' : 'none',
  }),
  speakerBtn: (enabled) => ({
    width: 46,
    height: 46,
    borderRadius: '50%',
    background: enabled ? 'var(--teal-dim)' : 'var(--bg-card)',
    border: enabled ? '1px solid var(--border-glow)' : '1px solid var(--border)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 18,
    transition: 'all 0.2s',
    flexShrink: 0,
    cursor: 'pointer',
    color: enabled ? 'var(--teal)' : 'var(--text-muted)',
  }),
  typing: {
    display: 'flex',
    gap: 5,
    alignItems: 'center',
    padding: '14px 16px',
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: '12px 12px 12px 2px',
    alignSelf: 'flex-start',
  },
  dot: (i) => ({
    width: 6, height: 6,
    borderRadius: '50%',
    background: 'var(--teal)',
    animation: `blink 1.2s ${i * 0.2}s infinite`,
  }),
  quickChips: {
    display: 'flex',
    gap: 8,
    flexWrap: 'wrap',
  },
  chip: {
    padding: '5px 12px',
    borderRadius: 20,
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    color: 'var(--text-secondary)',
    fontSize: 12,
    fontFamily: 'var(--font-mono)',
    cursor: 'pointer',
    transition: 'all 0.15s',
    whiteSpace: 'nowrap',
  },
}

const QUICK = [
  'chawal kitna bacha hai',
  'sab items ki list dikhao',
  '50kg atta add karo',
  '10 packet biscuit becha',
  'kaunsa saman kam hai',
]

export default function VoicePanel({ onRefresh }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [recording, setRecording] = useState(false)
  const [focusInput, setFocusInput] = useState(false)
  const [voiceEnabled, setVoiceEnabled] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  function speak(text) {
    if (!voiceEnabled || !('speechSynthesis' in window)) return
    
    // Stop any ongoing speech
    window.speechSynthesis.cancel()
    
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'hi-IN'
    utterance.rate = 0.9
    utterance.pitch = 1.0
    window.speechSynthesis.speak(utterance)
  }

  async function submit(text) {
    const q = (text || input).trim()
    if (!q || loading) return
    setInput('')
    setMessages(prev => [...prev, { type: 'user', text: q }])
    setLoading(true)
    try {
      const res = await sendQuery(q)
      setMessages(prev => [...prev, {
        type: 'bot',
        text: res.response,
        sql: res.sql,
        success: res.success,
        intent: res.intent,
        db_rows: res.db_rows,
      }])
      // Speak the response if voice is enabled
      speak(res.response)
      // Refresh inventory after successful ADD or SELL operations
      if (res.success && (res.intent === 'ADD' || res.intent === 'SELL')) {
        if (onRefresh) onRefresh()
      }
    } catch (err) {
      const errMsg = '⚠️ API se connect nahi ho saka. Check karo ki backend chal raha hai.'
      setMessages(prev => [...prev, {
        type: 'bot',
        text: errMsg,
        success: false,
      }])
      speak(errMsg)
    }
    setLoading(false)
  }

  const handleDownloadPDF = async () => {
    const element = document.getElementById('report-view')
    if (!element) return

    const canvas = await html2canvas(element)
    const imgData = canvas.toDataURL('image/png')

    const pdf = new jsPDF('p', 'mm', 'a4')
    const imgProps = pdf.getImageProperties(imgData)
    const pdfWidth = pdf.internal.pageSize.getWidth()
    const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width

    pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight)
    pdf.save('Kirana_Monthly_Report.pdf')
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function handleMic() {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      alert('Browser speech recognition not supported. Type your query instead.')
      return
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    const recognition = new SR()
    recognition.lang = 'hi-IN'
    recognition.interimResults = false
    recognition.maxAlternatives = 1
    setRecording(true)
    recognition.start()
    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript
      setInput(transcript)
      setRecording(false)
      submit(transcript)
    }
    recognition.onerror = () => setRecording(false)
    recognition.onend = () => setRecording(false)
  }

  return (
    <div style={s.root}>
      <div style={s.header}>
        <div>
          <div style={s.title}>Voice Query <span style={{ color: 'var(--teal)' }}>बोलिए</span></div>
          <div style={s.subtitle}>Hinglish mein bolo ya type karo — atta, chawal, tel sab samajh aata hai</div>
        </div>
        <button
          style={s.speakerBtn(voiceEnabled)}
          onClick={() => setVoiceEnabled(!voiceEnabled)}
          title={voiceEnabled ? 'Voice output: ON' : 'Voice output: OFF'}
        >
          {voiceEnabled ? '🔊' : '🔇'}
        </button>
      </div>

      {/* Quick chips */}
      <div style={s.quickChips}>
        {QUICK.map(q => (
          <button key={q} style={s.chip}
            onClick={() => submit(q)}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = 'var(--teal)'
              e.currentTarget.style.color = 'var(--teal)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = 'var(--border)'
              e.currentTarget.style.color = 'var(--text-secondary)'
            }}
          >{q}</button>
        ))}
      </div>

      {/* Chat */}
      <div style={s.chatArea}>
        {messages.length === 0 && (
          <div style={s.emptyState}>
            <div style={s.emptyIcon}>🏪</div>
            <div style={s.emptyText}>
              {"50kg atta add karo\nchawal kitna bacha hai\n10 packet biscuit becha"}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            style={msg.intent === 'REPORT'
              ? { ...s.bubble(msg.type), maxWidth: '100%' }
              : s.bubble(msg.type)
            }
          >
            <div style={s.bubbleLabel(msg.type)}>
              {msg.type === 'user' ? 'aap' : `AI${msg.intent ? ` · ${msg.intent}` : ''}`}
            </div>
            <div style={s.bubbleContent(msg.type, msg.success)}>
              {msg.text}
            </div>
            {/* Inside the component that renders messages*/}
            {msg.intent === "REPORT" && msg.db_rows && msg.db_rows[0] && (
              <div id="report-view" className="bg-white p-6 rounded-lg text-black mt-4">
                <h3 className="text-xl font-bold mb-4">Monthly Analytics Dashboard</h3>

                {/* Sales Trend Chart */}
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={msg.db_rows[0].daily_breakdown}>
                      <XAxis dataKey="day" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="revenue" fill="#4f46e5" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Text summary sections to mirror the CLI report */}
                {(() => {
                  const report = msg.db_rows[0]
                  const meta = report.meta || {}
                  const summary = report.summary || {}
                  const topProducts = report.top_products || []
                  const daily = report.daily_breakdown || []
                  const critical = report.critical_stock || []
                  const dead = report.dead_stock || []
                  return (
                    <div style={{ marginTop: '1.5rem', fontSize: 13, lineHeight: 1.6 }}>
                      <div style={{ marginBottom: 8 }}>
                        <div style={{ fontWeight: 700 }}>💰 Financial Summary</div>
                        <div>Total Revenue: ₹{summary.total_revenue?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
                        <div>Total Profit: ₹{summary.total_profit?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
                        <div>Profit Margin: {summary.margin_pct}%</div>
                        <div>Total Orders: {summary.total_orders}</div>
                        <div>Units Sold: {summary.total_units_sold}</div>
                        <div>Unique Customers: {summary.unique_customers}</div>
                      </div>

                      <div style={{ marginBottom: 8 }}>
                        <div style={{ fontWeight: 700 }}>⏰ Peak Performance</div>
                        <div>Peak Day: {summary.peak_day?.day} (₹{summary.peak_day?.revenue?.toLocaleString('en-IN', { maximumFractionDigits: 0 })})</div>
                        <div>Peak Hour: {summary.peak_hour}</div>
                      </div>

                      <div style={{ marginBottom: 8 }}>
                        <div style={{ fontWeight: 700 }}>🏆 Top 5 Products</div>
                        {topProducts.slice(0, 5).map((p, idx) => (
                          <div key={p.item + idx}>
                            {idx + 1}. {p.item} {p.qty} units ₹{p.revenue?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                          </div>
                        ))}
                      </div>

                      <div style={{ marginBottom: 8 }}>
                        <div style={{ fontWeight: 700 }}>📦 Daily Sales (Last 7 days)</div>
                        {daily.slice(-7).map(d => (
                          <div key={d.day}>
                            {d.day} — ₹{d.revenue?.toLocaleString('en-IN', { maximumFractionDigits: 0 })} ({d.orders} orders)
                          </div>
                        ))}
                      </div>

                      <div style={{ marginBottom: 8 }}>
                        <div style={{ fontWeight: 700 }}>🔴 Critical Stock Alerts</div>
                        {critical.map(item => (
                          <div key={item.item}>
                            ⚠️ {item.item}: ~{item.days_until_stockout} din bacha hai!
                          </div>
                        ))}
                      </div>

                      <div>
                        <div style={{ fontWeight: 700 }}>🧊 Dead Stock (30+ days no sale)</div>
                        {dead.map(item => (
                          <div key={item.item}>
                            • {item.item}: Last sold {item.last_sold}
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })()}

                <button
                  onClick={() => handleDownloadPDF()}
                  className="mt-4 bg-green-600 text-white px-4 py-2 rounded"
                >
                  Download PDF Report
                </button>
              </div>
            )}
            {msg.sql && (
              <div style={s.sqlChip}>⚡ {msg.sql}</div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ animation: 'fadeUp 0.2s ease' }}>
            <div style={s.typing}>
              <div style={s.dot(0)} />
              <div style={s.dot(1)} />
              <div style={s.dot(2)} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input row */}
      <div style={s.inputRow}>
        <div
          style={{ ...s.inputWrap, borderColor: focusInput ? 'var(--teal)' : 'var(--border)' }}
        >
          <input
            ref={inputRef}
            style={s.input}
            placeholder="50kg atta add karo..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            onFocus={() => setFocusInput(true)}
            onBlur={() => setFocusInput(false)}
            disabled={loading}
          />
        </div>

        <button style={s.micBtn(recording)} onClick={handleMic} title="Voice input">
          {recording ? '⏹' : '🎙️'}
        </button>

        <button
          style={{
            ...s.sendBtn,
            opacity: loading ? 0.6 : 1,
            transform: 'scale(1)',
          }}
          onClick={() => submit()}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--teal-mid)' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'var(--teal)' }}
          disabled={loading}
        >
          {loading ? 'Processing...' : 'Send →'}
        </button>
      </div>
    </div>
  )
}
