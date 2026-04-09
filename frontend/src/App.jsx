import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import VoicePanel from './components/VoicePanel'
import InventoryPanel from './components/InventoryPanel'
import HistoryPanel from './components/HistoryPanel'
import TrendsPanel from './components/TrendsPanel'
import { getHealth } from './api'
import { jsPDF } from "jspdf";
import html2canvas from "html2canvas";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const panels = {
  voice:     <VoicePanel />,
  inventory: <InventoryPanel />,
  history:   <HistoryPanel />,
}

const styles = {
  layout: {
    display: 'flex',
    height: '100vh',
    overflow: 'hidden',
  },
  main: {
    flex: 1,
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  topbar: {
    height: 48,
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg-surface)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 40px',
    flexShrink: 0,
  },
  breadcrumb: {
    fontFamily: 'var(--font-mono)',
    fontSize: 11,
    color: 'var(--text-muted)',
    letterSpacing: '0.3px',
  },
  topRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  timeStr: {
    fontFamily: 'var(--font-mono)',
    fontSize: 11,
    color: 'var(--text-muted)',
  },
  versionTag: {
    fontFamily: 'var(--font-mono)',
    fontSize: 10,
    color: 'var(--text-muted)',
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 4,
    padding: '2px 7px',
  },
  panelWrap: {
    flex: 1,
    overflow: 'hidden',
    position: 'relative',
  },
  panel: {
    position: 'absolute',
    inset: 0,
    overflowY: 'auto',
  },
}

function Clock() {
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return (
    <span style={styles.timeStr}>
      {time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
    </span>
  )
}

const LABELS = {
  voice: 'Voice Query',
  inventory: 'Inventory',
  history: 'History',
  trends: 'Trends & Reports',
}

export default function App() {
  const [active, setActive] = useState('voice')
  const [apiOnline, setApiOnline] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const triggerRefresh = () => {
    setRefreshKey(k => k + 1)
  }

  const panels = {
    voice:     <VoicePanel onRefresh={triggerRefresh} />,
    inventory: <InventoryPanel key={refreshKey} />,
    history:   <HistoryPanel />,
    trends:    <TrendsPanel />,
  }

  useEffect(() => {
    getHealth()
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false))
  }, [])

  // Inside your App component, add a handler for the PDF download
  const downloadPDF = async () => {
    const element = document.getElementById('report-view');
    const canvas = await html2canvas(element);
    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF('p', 'mm', 'a4');
    pdf.addImage(imgData, 'PNG', 10, 10, 190, 0);
    pdf.save("Kirana_Monthly_Report.pdf");
  };

  return (
    <div style={styles.layout}>
      <Sidebar active={active} onNav={setActive} apiOnline={apiOnline} />

      <main style={styles.main}>
        <div style={styles.topbar}>
          <span style={styles.breadcrumb}>
            KiranaSQL / <span style={{ color: 'var(--text-secondary)' }}>{LABELS[active]}</span>
          </span>
          <div style={styles.topRight}>
            <Clock />
            <span style={styles.versionTag}>v1.0</span>
          </div>
        </div>

        <div style={styles.panelWrap}>
          {Object.entries(panels).map(([key, panel]) => (
            <div
              key={key}
              style={{
                ...styles.panel,
                opacity: active === key ? 1 : 0,
                pointerEvents: active === key ? 'auto' : 'none',
                transition: 'opacity 0.2s ease',
              }}
            >
              {panel}
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
