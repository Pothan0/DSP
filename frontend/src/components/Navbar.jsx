import { Link, useLocation } from 'react-router-dom'
import { Shield, Activity, Crosshair, Layers } from 'lucide-react'
import './Navbar.css'

export default function Navbar() {
  const location = useLocation()
  const isActive = (path) => location.pathname === path ? 'nav-link active' : 'nav-link'

  return (
    <nav className="navbar">
      <Link to="/" className="nav-brand">
        <div className="brand-icon">
          <Shield size={20} />
        </div>
        <span className="brand-text"><span className="text-cyan">Aegis</span>Health</span>
      </Link>
      <div className="nav-links">
        <Link to="/dashboard" className={isActive('/dashboard')}>
          <Activity size={16} />
          <span>SOC Dashboard</span>
        </Link>
        <Link to="/redteam" className={isActive('/redteam')}>
          <Crosshair size={16} />
          <span>Red Team</span>
        </Link>
        <Link to="/architecture" className={isActive('/architecture')}>
          <Layers size={16} />
          <span>Architecture</span>
        </Link>
        <Link to="/dashboard" className="nav-cta">
          Launch Console →
        </Link>
      </div>
    </nav>
  )
}
