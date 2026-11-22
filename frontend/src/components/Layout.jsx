import { useState } from 'react'
import { NavLink, Link } from 'react-router-dom'
import {
  Activity, BadgeHelp, Bell, Bot, Building2, CheckCircle2, ChevronDown,
  ClipboardList, FileCheck2, FilePlus2, Globe2, LayoutDashboard,
  Menu, MessageSquareText, Search, ShieldCheck, X,
} from 'lucide-react'

const navigation = [
  {
    title: 'YOUR CIVIC DESK',
    links: [
      { label: 'Overview', path: '/', icon: LayoutDashboard },
      { label: 'AI assistant', path: '/assistant', icon: Bot, tag: 'AI' },
      { label: 'Government schemes', path: '/schemes', icon: Building2 },
    ],
  },
  {
    title: 'CITIZEN SERVICES',
    links: [
      { label: 'Report an issue', path: '/grievances/new', icon: FilePlus2 },
      { label: 'Track a complaint', path: '/tracking', icon: ClipboardList },
      { label: 'Service assistant', path: '/services', icon: BadgeHelp },
      { label: 'Policy explainer', path: '/policy', icon: FileCheck2 },
      { label: 'Fact verification', path: '/verify', icon: ShieldCheck },
    ],
  },
  {
    title: 'COMMUNITY',
    links: [
      { label: 'Public dashboard', path: '/public-dashboard', icon: Activity },
      { label: 'Admin workspace', path: '/admin', icon: FileCheck2 },
    ],
  },
]

export function AppLayout({ children }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const closeMenu = () => setMenuOpen(false)

  return (
    <div className="app-shell">
      {menuOpen && <button className="mobile-backdrop" onClick={closeMenu} aria-label="Close navigation" />}
      <aside className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`}>
        <Link to="/" className="brand" onClick={closeMenu}>
          <span className="brand-mark"><Activity size={21} strokeWidth={2.6} /></span>
          <span className="brand-name">civic<span>pulse</span><small>PUBLIC SERVICES, REIMAGINED</small></span>
        </Link>
        <div className="workspace-switcher">
          <span className="workspace-avatar"><Globe2 size={16} /></span>
          <span><strong>Citizen workspace</strong><small>India · English</small></span>
          <ChevronDown size={15} className="workspace-chevron" />
        </div>
        <nav className="side-nav" aria-label="Main navigation">
          {navigation.map((group) => (
            <div className="nav-group" key={group.title}>
              <div className="nav-caption">{group.title}</div>
              {group.links.map(({ label, path, icon: Icon, tag }) => (
                <NavLink key={path} to={path} end={path === '/'} onClick={closeMenu} className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
                  <Icon size={18} strokeWidth={1.8} /><span>{label}</span>{tag && <span className="nav-tag">{tag}</span>}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="help-card">
            <span className="help-icon"><MessageSquareText size={17} /></span>
            <strong>Need a hand?</strong>
            <p>Our civic assistant is here to help you find your way.</p>
            <Link to="/assistant" onClick={closeMenu}>Get assistance <span>→</span></Link>
          </div>
          <div className="profile-row">
            <div className="profile-avatar">AS</div>
            <div className="profile-copy"><strong>Arjun Sharma</strong><small>Citizen account</small></div>
            <ChevronDown size={15} />
          </div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <button className="mobile-menu" onClick={() => setMenuOpen(!menuOpen)} aria-label={menuOpen ? 'Close menu' : 'Open menu'}>
            {menuOpen ? <X size={21} /> : <Menu size={21} />}
          </button>
          <div className="topbar-breadcrumb"><span>Citizen portal</span><span className="breadcrumb-divider">/</span><strong>India</strong></div>
          <div className="topbar-actions">
            <button className="top-icon-button" aria-label="Search"><Search size={18} /></button>
            <button className="language-button"><Globe2 size={16} /><span>EN</span><ChevronDown size={13} /></button>
            <button className="notification-button" aria-label="Notifications"><Bell size={18} /><i /></button>
            <div className="top-user"><span>AS</span><ChevronDown size={13} /></div>
          </div>
        </header>
        <main className="main-content">{children}</main>
        <footer className="site-footer"><span>© 2025 CIVICPULSE AI</span><span><CheckCircle2 size={13} /> A secure digital public service</span><span>Built for every citizen</span></footer>
      </div>
    </div>
  )
}
