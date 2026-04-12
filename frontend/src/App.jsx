import { Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import RedTeam from './pages/RedTeam'
import Architecture from './pages/Architecture'
import './App.css'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/redteam" element={<RedTeam />} />
      <Route path="/architecture" element={<Architecture />} />
    </Routes>
  )
}
