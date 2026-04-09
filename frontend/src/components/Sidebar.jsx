import { useState } from 'react'

const NAV = [
  { id: 'voice',     icon: '🎙️', label: 'Voice Query'  },
  { id: 'inventory', icon: '📦', label: 'Inventory'    },
  { id: 'history',   icon: '🕒', label: 'History'      },
  { id: 'trends',    icon: '📈', label: 'Trends'       },
]

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
}

export default function Sidebar({ active, onNav, apiOnline }) {
  return (
    <aside style={styles.sidebar}>
      <div style={styles.logo}>
        <div style={styles.logoTop}>KiranaSQL</div>
        <div style={styles.logoSub}>आपकी दुकान का AI</div>
      </div>

      <nav style={styles.nav}>
        {NAV.map(item => (
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
            {item.label}
          </button>
        ))}
      </nav>

      <div style={styles.footer}>
        <span style={styles.dot(apiOnline)} />
        {apiOnline ? 'API connected' : 'API offline'}
      </div>
    </aside>
  )
}
