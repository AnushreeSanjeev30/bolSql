import { useEffect, useState } from 'react'
import { getCustomerTrends } from '../api'

export default function CustomerTrendsPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await getCustomerTrends()
        setData(res)
      } catch (e) {
        console.error('Customer trends error:', e)
        setError(e.message || 'Failed to load customer trends')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const styles = {
    container: {
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      padding: 20,
      background: 'var(--bg)',
      color: 'var(--text)',
      overflowY: 'auto',
      gap: 16,
    },
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'baseline',
      marginBottom: 8,
    },
    title: {
      fontSize: 18,
      fontWeight: 600,
    },
    subtitle: {
      fontSize: 12,
      color: 'var(--text-muted)',
    },
    grid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
      gap: 16,
    },
    card: {
      background: 'var(--bg-card)',
      borderRadius: 8,
      border: '1px solid var(--border)',
      padding: 16,
      fontSize: 13,
    },
    cardTitle: {
      fontWeight: 600,
      marginBottom: 8,
      fontSize: 14,
    },
    list: {
      listStyle: 'none',
      padding: 0,
      margin: 0,
    },
    listItem: {
      display: 'flex',
      justifyContent: 'space-between',
      padding: '4px 0',
      borderBottom: '1px dashed var(--border-subtle)',
      fontSize: 12,
    },
    pill: {
      fontFamily: 'var(--font-mono)',
      fontSize: 11,
      padding: '2px 6px',
      borderRadius: 999,
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
    },
    loading: {
      padding: 40,
      textAlign: 'center',
      color: 'var(--text-muted)',
    },
    error: {
      background: '#fee',
      border: '1px solid #fcc',
      borderRadius: 4,
      padding: 12,
      color: '#c33',
      fontSize: 12,
    },
  }

  if (loading) {
    return <div style={styles.loading}>Loading customer trends…</div>
  }

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>{error}</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div style={styles.loading}>
        No data yet. Try generating some transactions first.
      </div>
    )
  }

  const topRfm = (data.rfm || []).slice(0, 5)
  const atRisk = (data.churn || []).slice(0, 5)
  const topLtv = (data.ltv || []).slice(0, 5)
  const loyal = (data.loyalty || []).slice(0, 5)
  const visits = (data.visit_frequency || []).slice(0, 5)
  const baskets = (data.basket_size || []).slice(0, 5)
  const nextPurchases = (data.next_purchases || []).slice(0, 5)
  const deliveryOrders = (data.delivery_orders || []).slice(0, 5)

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Customer Trends Dashboard</h2>
        <span style={styles.subtitle}>
          Generated at {new Date(data.generated_at || Date.now()).toLocaleString('en-IN')}
        </span>
      </div>

      <div style={styles.grid}>
        <section style={styles.card}>
          <div style={styles.cardTitle}>🏆 Top RFM Segments</div>
          <ul style={styles.list}>
            {topRfm.map((c) => (
              <li key={c.customer_id} style={styles.listItem}>
                <span>{c.customer_id}</span>
                <span>
                  <span style={styles.pill}>{c.segment}</span>{' '}
                  RFM {c.rfm_score}
                </span>
              </li>
            ))}
            {topRfm.length === 0 && <li style={{ fontSize: 12, color: 'var(--text-muted)' }}>No customers yet.</li>}
          </ul>
        </section>

        <section style={styles.card}>
          <div style={styles.cardTitle}>⚠️ Churn Risk (At Risk)</div>
          <ul style={styles.list}>
            {atRisk.map((c) => (
              <li key={c.customer_id} style={styles.listItem}>
                <span>{c.customer_id}</span>
                <span>
                  {c.days_silent} days silent · risk {Math.round((c.churn_risk || 0) * 100)}%
                </span>
              </li>
            ))}
            {atRisk.length === 0 && <li style={{ fontSize: 12, color: 'var(--text-muted)' }}>No at-risk customers yet.</li>}
          </ul>
        </section>

        <section style={styles.card}>
          <div style={styles.cardTitle}>💰 Top LTV (next 6 months)</div>
          <ul style={styles.list}>
            {topLtv.map((c) => (
              <li key={c.customer_id} style={styles.listItem}>
                <span>{c.customer_id}</span>
                <span>
                  ₹{c.ltv_6m?.toFixed(0)} est. · avg ₹{c.avg_monthly?.toFixed(0)}/month
                </span>
              </li>
            ))}
            {topLtv.length === 0 && <li style={{ fontSize: 12, color: 'var(--text-muted)' }}>No LTV data yet.</li>}
          </ul>
        </section>

        <section style={styles.card}>
          <div style={styles.cardTitle}>💚 Loyalty Scores</div>
          <ul style={styles.list}>
            {loyal.map((c) => (
              <li key={c.customer_id} style={styles.listItem}>
                <span>{c.customer_id}</span>
                <span>
                  {c.loyalty_score} / 100 · {c.segment}
                </span>
              </li>
            ))}
            {loyal.length === 0 && <li style={{ fontSize: 12, color: 'var(--text-muted)' }}>No loyalty data yet.</li>}
          </ul>
        </section>

        <section style={styles.card}>
          <div style={styles.cardTitle}>📅 Visit Frequency</div>
          <ul style={styles.list}>
            {visits.map((c) => (
              <li key={c.customer_id} style={styles.listItem}>
                <span>{c.customer_id}</span>
                <span>
                  every {c.avg_gap_days} days · {c.visit_count} visits
                </span>
              </li>
            ))}
            {visits.length === 0 && <li style={{ fontSize: 12, color: 'var(--text-muted)' }}>No visit history yet.</li>}
          </ul>
        </section>

        <section style={styles.card}>
          <div style={styles.cardTitle}>🧺 Basket Size</div>
          <ul style={styles.list}>
            {baskets.map((c) => (
              <li key={c.customer_id} style={styles.listItem}>
                <span>{c.customer_id}</span>
                <span>
                  {c.avg_items} items · avg bill ₹{c.avg_basket_value?.toFixed(0)}
                </span>
              </li>
            ))}
            {baskets.length === 0 && <li style={{ fontSize: 12, color: 'var(--text-muted)' }}>No basket data yet.</li>}
          </ul>
        </section>

        <section style={styles.card}>
          <div style={styles.cardTitle}>📦 Upcoming Deliveries</div>
          <ul style={styles.list}>
            {deliveryOrders.map((o) => (
              <li key={o.customer_id} style={styles.listItem}>
                <span>{o.name || o.customer_id}</span>
                <span>
                  {o.items?.length || 0} items · by {o.earliest}
                </span>
              </li>
            ))}
            {deliveryOrders.length === 0 && (
              <li style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                No delivery suggestions yet.
              </li>
            )}
          </ul>
        </section>

        <section style={styles.card}>
          <div style={styles.cardTitle}>🔮 Next Likely Purchases</div>
          <ul style={styles.list}>
            {nextPurchases.map((p) => (
              <li key={`${p.customer_id}-${p.item}`} style={styles.listItem}>
                <span>{p.customer_id} → {p.item}</span>
                <span>
                  ~{p.avg_qty} qty · by {p.next_expected}
                </span>
              </li>
            ))}
            {nextPurchases.length === 0 && (
              <li style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                No next-purchase signals yet.
              </li>
            )}
          </ul>
        </section>
      </div>
    </div>
  )
}
