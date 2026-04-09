import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import VoicePanel from './components/VoicePanel'
import InventoryPanel from './components/InventoryPanel'
import HistoryPanel from './components/HistoryPanel'
import TrendsPanel from './components/TrendsPanel'
import CustomerTrendsPanel from './components/CustomerTrendsPanel'
import BillUploadPanel from './components/BillUploadPanel'
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
  hinglish: {
    // Navigation
    voice: 'Voice Query',
    inventory: 'Inventory',
    history: 'History',
    trends: 'Trends & Reports',
    customer: 'Customer Trends',    bill: 'Upload Bill',    
    // VoicePanel
    voiceTitle: 'Voice Query',
    voiceSubtitle: 'Speak in Hinglish or type — rice, wheat, oil and all items understood',
    voiceQuickChips: [
      'how much rice is left',
      'show me all items',
      'add 50kg wheat',
      'sell 10 packets of biscuits',
      'which items are low on stock',
    ],
    voicePlaceholder: 'Enter query...',
    
    // InventoryPanel
    inventoryTitle: 'Inventory Management',
    
    // HistoryPanel
    historyTitle: 'Transaction History',
    
    // TrendsPanel
    trendsTitle: 'Trends & Analytics',
  },
  tamil: {
    // Navigation (Tanglish)
    voice: 'Voice Query - Tanglish',
    inventory: 'Inventory - Samanukkam',
    history: 'History - Varalaru',
    trends: 'Trends - Viral Kavai',
    customer: 'Customer Trends',
    bill: 'Upload Bill - Manilar Alai',
    
    // VoicePanel (Tanglish)
    voiceTitle: 'Voice Query - Tanglish',
    voiceSubtitle: 'Speak in Tanglish or type — rice, oil, flour and all items understood',
    voiceQuickChips: [
      'how much rice do we have',
      'show all items',
      'add 50kg of flour',
      'we need 10 packets of biscuits',
      'which items are running low',
    ],
    voicePlaceholder: 'Type here...',
    
    // InventoryPanel (Tanglish)
    inventoryTitle: 'Inventory Management - Samanukkam',
    
    // HistoryPanel (Tanglish)
    historyTitle: 'Transaction History - Varalaru',
    
    // TrendsPanel (Tanglish)
    trendsTitle: 'Trends & Analytics - Viral Kavai',
  },
}

export default function App() {
  const [active, setActive] = useState('voice')
  const [apiOnline, setApiOnline] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [language, setLanguage] = useState('hinglish')

  const triggerRefresh = () => {
    setRefreshKey(k => k + 1)
  }

  const panels = {
    voice:     <VoicePanel onRefresh={triggerRefresh} language={language} />,
    inventory: <InventoryPanel key={refreshKey} language={language} />,
    history:   <HistoryPanel language={language} />,
    trends:    <TrendsPanel language={language} />,
    customer:  <CustomerTrendsPanel />,
    bill:      <BillUploadPanel onBillProcessed={triggerRefresh} />,
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
      <Sidebar active={active} onNav={setActive} apiOnline={apiOnline} language={language} onLanguageChange={setLanguage} />

      <main style={styles.main}>
        <div style={styles.topbar}>
          <span style={styles.breadcrumb}>
            KiranaSQL / <span style={{ color: 'var(--text-secondary)' }}>{LABELS[language][active]}</span>
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
