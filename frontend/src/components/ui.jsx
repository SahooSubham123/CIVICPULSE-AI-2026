import { ArrowUpRight } from 'lucide-react'

export function PageTitle({ eyebrow, title, description, action }) {
  return (
    <div className="page-title">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function Panel({ children, className = '' }) {
  return <section className={`panel ${className}`}>{children}</section>
}

export function SectionHeading({ title, subtitle, action }) {
  return (
    <div className="section-heading">
      <div>
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function Button({ children, variant = 'primary', className = '', ...props }) {
  return <button className={`button button-${variant} ${className}`} {...props}>{children}</button>
}

export function Badge({ children, tone = 'blue' }) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}

export function StatCard({ label, value, note, icon: Icon, tone = 'blue' }) {
  return (
    <div className="stat-card">
      <div className={`stat-icon icon-${tone}`}><Icon size={19} /></div>
      <div className="stat-copy">
        <span>{label}</span>
        <strong>{value}</strong>
        {note && <small>{note}</small>}
      </div>
    </div>
  )
}

export function TextLink({ children, to = '#', ...props }) {
  return <a className="text-link" href={to} {...props}>{children}<ArrowUpRight size={14} /></a>
}

export function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="empty-state">
      <span className="empty-icon"><Icon size={23} /></span>
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  )
}
