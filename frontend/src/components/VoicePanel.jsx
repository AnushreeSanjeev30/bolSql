import { useState, useRef, useEffect } from 'react'
import { sendQuery, getAllTrends, synthesizeVoice } from '../api'
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
    flexWrap: 'wrap',
  },
  headerControls: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 10,
    flexWrap: 'wrap',
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
  voiceSettingsCard: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: '12px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  voiceSettingsInline: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 10,
    padding: '8px 10px',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
    justifyContent: 'flex-end',
    minHeight: 44,
  },
  inlineDivider: {
    width: 1,
    height: 20,
    background: 'var(--border)',
  },
  voiceSettingsTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 10,
  },
  voiceSettingsTitle: {
    fontSize: 12,
    fontFamily: 'var(--font-mono)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    color: 'var(--text-secondary)',
  },
  voiceSettingsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
    gap: 10,
  },
  voiceSettingRow: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  voiceSettingLabel: {
    fontSize: 11,
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-muted)',
  },
  voiceSettingSelect: {
    background: 'var(--bg-base)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    color: 'var(--text-primary)',
    fontSize: 12,
    padding: '8px 10px',
    outline: 'none',
    minWidth: 118,
  },
  smallActionBtn: {
    background: 'var(--teal-dim)',
    color: 'var(--teal)',
    border: '1px solid var(--border-glow)',
    borderRadius: 8,
    fontSize: 12,
    fontFamily: 'var(--font-mono)',
    padding: '6px 10px',
    cursor: 'pointer',
  },
  speakingBadge: (active) => ({
    fontSize: 11,
    fontFamily: 'var(--font-mono)',
    color: active ? 'var(--teal)' : 'var(--text-muted)',
    background: active ? 'var(--teal-dim)' : 'var(--bg-base)',
    border: active ? '1px solid var(--border-glow)' : '1px solid var(--border)',
    borderRadius: 999,
    padding: '4px 8px',
    animation: active ? 'glow-pulse 1.2s infinite' : 'none',
  }),
  engineBadge: {
    fontSize: 11,
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-secondary)',
    background: 'var(--bg-base)',
    border: '1px solid var(--border)',
    borderRadius: 999,
    padding: '4px 8px',
  },
}

const DEFAULT_VOICE_SETTINGS = {
  preset: 'auto',
}

const VOICE_PRESETS = {
  auto: { rate: 0.82, pitch: 0.92, volume: 0.88, voiceProfile: 'auto' },
  female: { rate: 0.88, pitch: 1.2, volume: 0.9, voiceProfile: 'female' },
  male: { rate: 0.84, pitch: 0.9, volume: 0.9, voiceProfile: 'male' },
}

const QUICK_HINGLISH = [
  'chawal kitna bacha hai',
  'sab items ki list dikhao',
  '50kg atta add karo',
  '10 packet biscuit becha',
  'kaunsa saman kam hai',
]

const QUICK_TANGLISH = [
  'arisi evlo irukku',
  'ella items list kaatu',
  '50kg aatta add pannunga',
  '10 packet biscuit vithachu',
  'endha item kammi irukku',
]

// Intent label translations
const INTENT_LABELS = {
  hinglish: {
    'ADD': 'ADD',
    'SELL': 'SELL',
    'QUERY': 'QUERY',
    'TREND': 'TREND',
    'PRICE': 'PRICE',
    'REPORT': 'REPORT',
  },
  tamil: {
    'ADD': 'ADD',
    'SELL': 'SELL',
    'QUERY': 'QUERY',
    'TREND': 'TREND',
    'PRICE': 'PRICE',
    'REPORT': 'REPORT',
  }
}

const USER_LABELS = {
  hinglish: 'aap',
  tamil: 'nee',
}

const REPORT_TRENDS = [
  { type: 'sales_trend', title: 'Sales Trend', description: 'Monthly/weekly revenue over time' },
  { type: 'hourly_rush', title: 'Hourly Rush', description: 'Busiest hours of the day for sales' },
  { type: 'product_demand', title: 'Product Demand', description: 'Top-selling products by volume or revenue' },
  { type: 'dead_stock', title: 'Dead Stock', description: 'Products with very low or no sales' },
  { type: 'seasonal_trend', title: 'Seasonal Trend', description: 'Which products sell more in which months' },
  { type: 'festival_trend', title: 'Festival Trend', description: 'Sales spikes around known festival dates' },
]

function hasTrendData(trend) {
  if (!trend) return false
  if (Array.isArray(trend.raw?.data)) return trend.raw.data.length > 0
  if (Array.isArray(trend.raw)) return trend.raw.length > 0
  return Boolean(trend.raw)
}

export default function VoicePanel({ onRefresh, language = 'hinglish' }) {
  const storageKey = `voice-chat-messages-${language}`
  const voiceSettingsKey = `voice-output-settings-${language}`
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem(storageKey)
    return saved ? JSON.parse(saved) : []
  })
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [recording, setRecording] = useState(false)
  const [focusInput, setFocusInput] = useState(false)
  const [voiceEnabled, setVoiceEnabled] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [voiceEngine, setVoiceEngine] = useState('Browser')
  const [voiceSettings, setVoiceSettings] = useState(DEFAULT_VOICE_SETTINGS)
  const [reportTrends, setReportTrends] = useState([])
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const speechTokenRef = useRef(0)
  const currentUtteranceRef = useRef(null)
  const currentAudioRef = useRef(null)
  const currentAudioContextRef = useRef(null)
  const currentMediaSourceRef = useRef(null)
  const currentToneNodeRef = useRef(null)
  const currentPresenceNodeRef = useRef(null)

  // Save messages to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(messages))
  }, [messages, storageKey])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    const saved = localStorage.getItem(voiceSettingsKey)
    if (!saved) {
      setVoiceSettings(DEFAULT_VOICE_SETTINGS)
      return
    }
    try {
      const parsed = JSON.parse(saved)
      const normalizedPreset = parsed.preset === 'aman' ? 'male' : parsed.preset
      setVoiceSettings({
        preset: ['auto', 'female', 'male'].includes(normalizedPreset) ? normalizedPreset : DEFAULT_VOICE_SETTINGS.preset,
      })
    } catch {
      setVoiceSettings(DEFAULT_VOICE_SETTINGS)
    }
  }, [voiceSettingsKey])

  useEffect(() => {
    localStorage.setItem(voiceSettingsKey, JSON.stringify(voiceSettings))
  }, [voiceSettings, voiceSettingsKey])

  function stopSpeaking() {
    speechTokenRef.current += 1
    setIsSpeaking(false)
    currentUtteranceRef.current = null
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
    if (currentAudioRef.current) {
      try {
        currentAudioRef.current.pause()
        currentAudioRef.current.currentTime = 0
      } catch {
        // no-op
      }
      currentAudioRef.current = null
    }
    if (currentMediaSourceRef.current) {
      try {
        currentMediaSourceRef.current.disconnect()
      } catch {
        // no-op
      }
      currentMediaSourceRef.current = null
    }
    if (currentToneNodeRef.current) {
      try {
        currentToneNodeRef.current.disconnect()
      } catch {
        // no-op
      }
      currentToneNodeRef.current = null
    }
    if (currentPresenceNodeRef.current) {
      try {
        currentPresenceNodeRef.current.disconnect()
      } catch {
        // no-op
      }
      currentPresenceNodeRef.current = null
    }
    if (currentAudioContextRef.current) {
      try {
        currentAudioContextRef.current.close()
      } catch {
        // no-op
      }
      currentAudioContextRef.current = null
    }
  }

  useEffect(() => {
    // Avoid leftover speech when component unmounts.
    return () => stopSpeaking()
  }, [])

  useEffect(() => {
    if (!voiceEnabled) stopSpeaking()
  }, [voiceEnabled])

  useEffect(() => {
    // Language switches should not continue reading in the previous voice.
    stopSpeaking()
  }, [language])

  function normalizeSpeechText(text) {
    let out = String(text || '').trim()
    // Keep spoken numbers concise: 10.000000 -> 10, 10.500000 -> 10.5
    out = out.replace(/\b(-?\d+)\.0+\b/g, '$1')
    out = out.replace(/\b(-?\d+\.\d*?[1-9])0+\b/g, '$1')
    // Remove emoji and symbol clutter to improve spoken quality.
    out = out.replace(/[\u2600-\u27BF\u{1F300}-\u{1FAFF}]/gu, ' ')
    out = out.replace(/[\u2022\u25CF\u25AA\u2713]/g, ' ')
    out = out.replace(/\s+/g, ' ').trim()
    return out
  }

  function buildSpeechChunks(text) {
    let out = normalizeSpeechText(text)
    if (!out) return []

    const rawSentences = out
      .replace(/\n+/g, '. ')
      .split(/[.!?]+/)
      .map(s => s.trim())
      .filter(Boolean)

    let sentences = rawSentences
    if (sentences.length > 2 || out.length > 180) {
      const closing = language === 'tamil'
        ? 'Meedhiya details screen la irukku.'
        : 'Baaki details screen par hai.'
      sentences = [...rawSentences.slice(0, 2), closing]
    }

    const chunks = []
    for (const sentence of sentences) {
      if (sentence.length <= 120) {
        chunks.push(sentence)
        continue
      }
      const parts = sentence.split(/[,;:]/).map(p => p.trim()).filter(Boolean)
      if (!parts.length) chunks.push(sentence)
      else chunks.push(...parts)
    }

    return chunks.slice(0, 6)
  }

  function getTargetLang() {
    const langMap = { 'hinglish': 'hi-IN', 'hindi': 'hi-IN', 'tamil': 'ta-IN' }
    return langMap[language] || 'hi-IN'
  }

  function getPreferredVoice(voices, targetLang, voiceProfile) {
    if (!voices.length) return null
    const primaryLang = targetLang.split('-')[0]
    const languagePool = voices.filter(v => v.lang === targetLang || v.lang?.startsWith(primaryLang))
    const indianPool = voices.filter(v => {
      const lang = (v.lang || '').toLowerCase()
      const text = `${v.name || ''} ${v.voiceURI || ''}`.toLowerCase()
      return lang === 'hi-in' || lang === 'ta-in' || lang === 'en-in' || /india|indian|hindi|tamil/.test(text)
    })
    const pool = languagePool.length ? languagePool : (indianPool.length ? indianPool : voices)

    const asText = (v) => `${v.name || ''} ${v.voiceURI || ''}`.toLowerCase()
    const femaleHint = /(female|woman|samantha|victoria|karen|zira|moira|tessa|veena|ava|allison|susan|serena|kathy)/i
    const maleHint = /(male|man|david|alex|fred|daniel|thomas|ralph|jorge|aaron|lee|bruce)/i

    if (voiceProfile === 'female') {
      const femaleVoice = pool.find(v => femaleHint.test(asText(v))) || voices.find(v => femaleHint.test(asText(v)))
      if (femaleVoice) return femaleVoice
    }

    if (voiceProfile === 'male') {
      const maleVoice = pool.find(v => maleHint.test(asText(v))) || voices.find(v => maleHint.test(asText(v)))
      if (maleVoice) return maleVoice
    }

    return pool.find(v => v.lang === targetLang)
      || pool.find(v => v.lang?.startsWith(primaryLang))
      || indianPool.find(v => v.lang?.toLowerCase() === 'en-in')
      || indianPool.find(v => v.lang?.toLowerCase() === 'hi-in')
      || indianPool.find(v => v.lang?.toLowerCase() === 'ta-in')
      || indianPool.find(v => /hindi|tamil|india|indian/i.test(`${v.name || ''} ${v.voiceURI || ''}`))
      || null
  }

  function cleanupCloudProfileNodes() {
    if (currentMediaSourceRef.current) {
      try {
        currentMediaSourceRef.current.disconnect()
      } catch {
        // no-op
      }
      currentMediaSourceRef.current = null
    }
    if (currentToneNodeRef.current) {
      try {
        currentToneNodeRef.current.disconnect()
      } catch {
        // no-op
      }
      currentToneNodeRef.current = null
    }
    if (currentPresenceNodeRef.current) {
      try {
        currentPresenceNodeRef.current.disconnect()
      } catch {
        // no-op
      }
      currentPresenceNodeRef.current = null
    }
    if (currentAudioContextRef.current) {
      currentAudioContextRef.current.close().catch(() => {})
      currentAudioContextRef.current = null
    }
  }

  function attachCloudProfile(audio, voiceProfile) {
    const AudioContextCtor = window.AudioContext || window.webkitAudioContext
    if (!AudioContextCtor) return

    const audioContext = new AudioContextCtor()
    const source = audioContext.createMediaElementSource(audio)
    const tone = audioContext.createBiquadFilter()
    const presence = audioContext.createBiquadFilter()

    if (voiceProfile === 'female') {
      tone.type = 'lowshelf'
      tone.frequency.value = 220
      tone.gain.value = -4
      presence.type = 'highshelf'
      presence.frequency.value = 2000
      presence.gain.value = 4
    } else {
      tone.type = 'peaking'
      tone.frequency.value = 1000
      tone.Q.value = 1
      tone.gain.value = 0
      presence.type = 'peaking'
      presence.frequency.value = 2500
      presence.Q.value = 1
      presence.gain.value = 0
    }

    source.connect(tone)
    tone.connect(presence)
    presence.connect(audioContext.destination)

    currentAudioContextRef.current = audioContext
    currentMediaSourceRef.current = source
    currentToneNodeRef.current = tone
    currentPresenceNodeRef.current = presence
  }

  function speakWithBrowser(chunks, token) {
    if (!('speechSynthesis' in window) || !chunks.length) {
      setVoiceEngine('Browser')
      setIsSpeaking(false)
      return
    }

    const targetLang = getTargetLang()
    const preset = VOICE_PRESETS[voiceSettings.preset] || VOICE_PRESETS.auto
    setVoiceEngine(preset.voiceProfile === 'male' ? 'Browser Male' : 'Browser Fallback')

    const voices = window.speechSynthesis.getVoices() || []
    const preferredVoice = getPreferredVoice(voices, targetLang, preset.voiceProfile)

    const speakChunk = (idx) => {
      if (speechTokenRef.current !== token || idx >= chunks.length) {
        if (speechTokenRef.current === token) {
          currentUtteranceRef.current = null
          setIsSpeaking(false)
        }
        return
      }

      const utterance = new SpeechSynthesisUtterance(chunks[idx])
      if (preferredVoice) utterance.voice = preferredVoice
      utterance.lang = targetLang
      utterance.rate = preset.rate
      utterance.pitch = preset.pitch
      utterance.volume = preset.volume
      utterance.onstart = () => {
        currentUtteranceRef.current = utterance
        setIsSpeaking(true)
      }
      utterance.onend = () => {
        if (speechTokenRef.current !== token) return
        setTimeout(() => speakChunk(idx + 1), 110)
      }
      utterance.onerror = () => {
        if (speechTokenRef.current === token) {
          currentUtteranceRef.current = null
          setIsSpeaking(false)
        }
      }

      window.speechSynthesis.speak(utterance)
    }

    speakChunk(0)
  }

  async function speak(text) {
    if (!voiceEnabled) return
    const chunks = buildSpeechChunks(text)
    if (!chunks.length) return

    stopSpeaking()
    const token = speechTokenRef.current
    const selectedPreset = VOICE_PRESETS[voiceSettings.preset] || VOICE_PRESETS.auto
    const spokenText = chunks.join('. ')

    if (selectedPreset.voiceProfile === 'male') {
      speakWithBrowser(chunks, token)
      return
    }

    try {
      const audioBlob = await synthesizeVoice(spokenText, language)
      if (speechTokenRef.current !== token) return

      if (selectedPreset.voiceProfile === 'female') setVoiceEngine('Indian Cloud Female')
      else setVoiceEngine('Indian Cloud')

      const audioUrl = URL.createObjectURL(audioBlob)
      const audio = new Audio(audioUrl)

      // gTTS returns a single cloud voice. Shape playback so male/female presets are audibly distinct.
      if (selectedPreset.voiceProfile === 'female') {
        audio.playbackRate = 1.1
      }

      if ('preservesPitch' in audio) {
        audio.preservesPitch = false
      }
      if ('mozPreservesPitch' in audio) {
        audio.mozPreservesPitch = false
      }
      if ('webkitPreservesPitch' in audio) {
        audio.webkitPreservesPitch = false
      }

      cleanupCloudProfileNodes()
      attachCloudProfile(audio, selectedPreset.voiceProfile)

      currentAudioRef.current = audio

      audio.onplay = () => {
        if (currentAudioContextRef.current?.state === 'suspended') {
          currentAudioContextRef.current.resume().catch(() => {})
        }
        setIsSpeaking(true)
      }
      audio.onended = () => {
        if (speechTokenRef.current === token) setIsSpeaking(false)
        cleanupCloudProfileNodes()
        if (currentAudioRef.current === audio) currentAudioRef.current = null
        URL.revokeObjectURL(audioUrl)
      }
      audio.onerror = () => {
        cleanupCloudProfileNodes()
        if (currentAudioRef.current === audio) currentAudioRef.current = null
        URL.revokeObjectURL(audioUrl)
        if (speechTokenRef.current === token) {
          speakWithBrowser(chunks, token)
        }
      }

      await audio.play()
    } catch {
      speakWithBrowser(chunks, token)
    }
  }

  async function submit(text) {
    const q = (text || input).trim()
    if (!q) return
    stopSpeaking()
    if (loading) return
    setInput('')
    setMessages(prev => [...prev, { type: 'user', text: q }])
    setLoading(true)
    try {
      const res = await sendQuery(q, language)
      setMessages(prev => [...prev, {
        type: 'bot',
        text: res.response,
        sql: res.sql,
        success: res.success,
        intent: res.intent,
        db_rows: res.db_rows,
      }])

      if (res.intent === 'REPORT') {
        try {
          const trendsRes = await getAllTrends()
          setReportTrends(trendsRes.trends || [])
        } catch {
          setReportTrends([])
        }
      } else {
        setReportTrends([])
      }

      // Speak the response if voice is enabled
      speak(res.response)
      // Refresh inventory after successful ADD or SELL operations
      if (res.success && (res.intent === 'ADD' || res.intent === 'SELL')) {
        if (onRefresh) onRefresh()
      }
    } catch (err) {
      const errMsg = language === 'tamil'
        ? '⚠️ API connect pannathu illa. Backend running irukku check panna.'
        : '⚠️ API se connect nahi ho saka. Check karo ki backend chal raha hai.'
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
    stopSpeaking()
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
        <div style={{ flex: 1 }}>
          <div style={s.title}>
            {language === 'tamil' ? 'Voice Query - Tanglish' : 'Voice Query'}
            <span style={{ color: 'var(--teal)' }}>
              {language === 'tamil' ? ' 🎙️' : ' बोलिए'}
            </span>
          </div>
          <div style={s.subtitle}>
            {language === 'tamil' 
              ? 'Tanglish la pesunga illa type pannunga — aatta, arisi, ennai ellam puriyum' 
              : 'Hinglish mein bolo ya type karo — atta, chawal, tel sab samajh aata hai'}
          </div>
        </div>
        <div style={s.headerControls}>
          <button
            style={s.speakerBtn(voiceEnabled)}
            onClick={() => setVoiceEnabled(v => !v)}
            title={voiceEnabled ? 'Voice output: ON' : 'Voice output: OFF'}
          >
            {voiceEnabled ? '🔊' : '🔇'}
          </button>
          <button
            style={{
              ...s.speakerBtn(false),
              background: 'var(--bg-card)',
              color: 'var(--text-muted)',
            }}
            onClick={() => {
              stopSpeaking()
              if (confirm('Clear all chat history?')) {
                setMessages([])
                localStorage.removeItem(storageKey)
              }
            }}
            title="Clear chat history"
          >
            🗑️
          </button>
          <div style={s.voiceSettingsInline}>
            <label style={s.voiceSettingLabel}>Voice</label>
            <select
              style={{ ...s.voiceSettingSelect, padding: '6px 10px' }}
              value={voiceSettings.preset}
              onChange={(e) => setVoiceSettings(prev => ({ ...prev, preset: e.target.value }))}
            >
              <option value="auto">Auto</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
            </select>
            <div style={s.inlineDivider} />
            <div style={s.engineBadge}>{voiceEngine}</div>
            <div style={s.speakingBadge(isSpeaking)}>
              {isSpeaking ? 'Speaking...' : 'Ready'}
            </div>
            <button
              style={s.smallActionBtn}
              onClick={() => speak(language === 'tamil' ? 'Idhu test voice output.' : 'Yeh test voice output hai.')}
              disabled={!voiceEnabled}
              title={voiceEnabled ? 'Play test speech' : 'Enable speaker first'}
            >
              Test Voice
            </button>
          </div>
        </div>
      </div>

      {/* Quick chips */}
      <div style={s.quickChips}>
        {(language === 'tamil' ? QUICK_TANGLISH : QUICK_HINGLISH).map(q => (
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
              {language === 'tamil'
                ? "50kg aatta add pannunga\narisi evlo irukku\n10 packet biscuit vithachu"
                : "50kg atta add karo\nchawal kitna bacha hai\n10 packet biscuit becha"}
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
              {msg.type === 'user' 
                ? USER_LABELS[language] || 'aap'
                : `AI${msg.intent ? ` · ${INTENT_LABELS[language][msg.intent] || msg.intent}` : ''}`
              }
            </div>
            <div style={s.bubbleContent(msg.type, msg.success)}>
              {msg.text}
            </div>
            {/* Inside the component that renders messages*/}
            {msg.intent === "REPORT" && msg.db_rows && msg.db_rows[0] && (
              <div id="report-view" className="bg-white p-6 rounded-lg text-black mt-4">
                <h3 className="text-xl font-bold mb-4">Imported CSV Analytics Report</h3>

                {reportTrends.length > 0 && (
                  <div style={{ marginBottom: '1rem' }}>
                    <div style={{ fontWeight: 700, marginBottom: 8 }}>📈 Trend coverage from imported CSV</div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
                      {REPORT_TRENDS.map((item) => {
                        const trend = reportTrends.find(t => t.type === item.type)
                        const available = hasTrendData(trend)
                        return (
                          <div
                            key={item.type}
                            style={{
                              border: '1px solid rgba(0,0,0,0.12)',
                              borderRadius: 10,
                              padding: '12px 14px',
                              background: available ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.06)',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginBottom: 4 }}>
                              <div style={{ fontWeight: 700 }}>{item.title}</div>
                              <div style={{ fontFamily: 'monospace', fontSize: 12, color: available ? '#059669' : '#dc2626' }}>
                                {available ? 'Yes' : 'No'}
                              </div>
                            </div>
                            <div style={{ fontSize: 12, color: '#4b5563', lineHeight: 1.4 }}>
                              {item.description}
                            </div>
                            {trend?.insight && (
                              <div style={{ marginTop: 6, fontSize: 12, color: '#111827' }}>
                                {trend.insight}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

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
            placeholder={language === 'tamil' ? '50kg aatta add panna...' : '50kg atta add karo...'}
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
