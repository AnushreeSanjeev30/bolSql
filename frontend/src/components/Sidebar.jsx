import { useState } from 'react'

const NAV_IDS = [
  { id: 'voice',     icon: '🎙️' },
  { id: 'inventory', icon: '📦' },
  { id: 'trends',    icon: '📈' },
  { id: 'customer',  icon: '👥' },
]

const NAV_LABELS = {
  hinglish: {
    voice: 'Voice Query',
    inventory: 'Inventory',
    history: 'History',
    trends: 'Trends & Reports',
    customer: 'Customer Trends',
  },
  tamil: {
    voice: 'Voice Query - Tanglish',
    inventory: 'Inventory - Samanukkam',
    history: 'History - Varalaru',
    trends: 'Trends - Viral Kavai',
    customer: 'Customer Trends',
  },
}

const styles = {
  sidebar: {
    width: 220,
    minHeight: '100vh',
    background: 'var(--bg-surface)',
    borderRight: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    flexShrink: 0,
    position: 'relative',
    zIndex: 10,
  },
  logo: {
    padding: '28px 20px 20px',
    borderBottom: '1px solid var(--border)',
  },
  logoTop: {
    fontFamily: 'var(--font-display)',
    fontWeight: 800,
    fontSize: 18,
    color: 'var(--teal)',
    letterSpacing: '-0.3px',
  },
  logoSub: {
    fontSize: 10,
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
    marginTop: 2,
    letterSpacing: '0.5px',
    textTransform: 'uppercase',
  },
  nav: {
    padding: '16px 12px',
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  navItem: (active) => ({
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '10px 12px',
    borderRadius: 'var(--radius)',
    cursor: 'pointer',
    background: active ? 'var(--teal-dim)' : 'transparent',
    border: active ? '1px solid var(--border-glow)' : '1px solid transparent',
    color: active ? 'var(--teal)' : 'var(--text-secondary)',
    fontWeight: active ? 500 : 400,
    fontSize: 13,
    transition: 'all 0.15s ease',
    fontFamily: 'var(--font-body)',
  }),
  navIcon: { fontSize: 16, width: 20, textAlign: 'center' },
  footer: {
    padding: '16px 20px',
    borderTop: '1px solid var(--border)',
    fontSize: 11,
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
  },
  dot: (on) => ({
    width: 6, height: 6,
    borderRadius: '50%',
    background: on ? 'var(--success)' : 'var(--text-muted)',
    display: 'inline-block',
    marginRight: 6,
    boxShadow: on ? '0 0 6px var(--success)' : 'none',
  }),
  langSection: {
    padding: '12px 16px',
    borderTop: '1px solid var(--border)',
    borderBottom: '1px solid var(--border)',
    display: 'flex',
    gap: 6,
    flexDirection: 'column',
  },
  langLabel: {
    fontSize: 10,
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: 4,
  },
  langButtons: {
    display: 'flex',
    gap: 6,
  },
  langBtn: (active) => ({
    flex: 1,
    padding: '6px 8px',
    borderRadius: 4,
    border: active ? '2px solid var(--teal)' : '1px solid var(--border)',
    background: active ? 'var(--teal-dim)' : 'var(--bg-card)',
    color: active ? 'var(--teal)' : 'var(--text-secondary)',
    fontFamily: 'var(--font-body)',
    fontSize: 11,
    fontWeight: active ? 600 : 400,
    cursor: 'pointer',
    transition: 'all 0.15s',
  }),
}

export default function Sidebar({ active, onNav, apiOnline, language, onLanguageChange }) {
  return (
    <aside style={styles.sidebar}>
      <div style={styles.logo}>
        <div style={styles.logoTop}>KiranaSQL</div>
        <div style={styles.logoSub}>आपकी दुकान का AI</div>
      </div>

      <nav style={styles.nav}>
        {NAV_IDS.map(item => (
          <button
            key={item.id}
            style={styles.navItem(active === item.id)}
            onClick={() => onNav(item.id)}
            onMouseEnter={e => {
              if (active !== item.id) {
                e.currentTarget.style.background = 'var(--bg-hover)'
                e.currentTarget.style.color = 'var(--text-primary)'
              }
            }}
            onMouseLeave={e => {
              if (active !== item.id) {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.color = 'var(--text-secondary)'
              }
            }}
          >
            <span style={styles.navIcon}>{item.icon}</span>
            {NAV_LABELS[language][item.id] || NAV_LABELS['hinglish'][item.id]}
          </button>
        ))}
      </nav>

      <div style={styles.langSection}>
        <div style={styles.langLabel}>🌐 Language</div>
        <div style={styles.langButtons}>
          <button 
            style={styles.langBtn(language === 'hinglish')}
            onClick={() => onLanguageChange('hinglish')}
          >
            Hinglish
          </button>
          <button 
            style={styles.langBtn(language === 'tamil')}
            onClick={() => onLanguageChange('tamil')}
          >
            Tanglish
          </button>
        </div>
      </div>

      <div style={styles.footer}>
        <span style={styles.dot(apiOnline)} />
        {apiOnline ? 'API connected' : 'API offline'}
      </div>
    </aside>
  )
}
