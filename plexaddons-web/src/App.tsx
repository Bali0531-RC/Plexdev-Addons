import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Addons from './pages/Addons'
import AddonDetail from './pages/AddonDetail'
import Pricing from './pages/Pricing'
import Docs from './pages/Docs'
import Login from './pages/Login'
import AuthCallback from './pages/AuthCallback'
import Dashboard from './pages/dashboard/Dashboard'
import MyAddons from './pages/dashboard/MyAddons'
import AddonEditor from './pages/dashboard/AddonEditor'
import VersionEditor from './pages/dashboard/VersionEditor'
import Settings from './pages/dashboard/Settings'
import Subscription from './pages/dashboard/Subscription'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminUsers from './pages/admin/AdminUsers'
import AdminAddons from './pages/admin/AdminAddons'
import AdminAuditLog from './pages/admin/AdminAuditLog'
import ProtectedRoute from './components/ProtectedRoute'
import AdminRoute from './components/AdminRoute'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        {/* Public routes */}
        <Route index element={<Home />} />
        <Route path="addons" element={<Addons />} />
        <Route path="addons/:slug" element={<AddonDetail />} />
        <Route path="pricing" element={<Pricing />} />
        <Route path="docs" element={<Docs />} />
        <Route path="login" element={<Login />} />
        <Route path="auth/callback" element={<AuthCallback />} />

        {/* Protected routes */}
        <Route path="dashboard" element={<ProtectedRoute />}>
          <Route index element={<Dashboard />} />
          <Route path="addons" element={<MyAddons />} />
          <Route path="addons/new" element={<AddonEditor />} />
          <Route path="addons/:slug" element={<AddonEditor />} />
          <Route path="addons/:slug/versions/new" element={<VersionEditor />} />
          <Route path="addons/:slug/versions/:version" element={<VersionEditor />} />
          <Route path="settings" element={<Settings />} />
          <Route path="subscription" element={<Subscription />} />
        </Route>

        {/* Admin routes */}
        <Route path="admin" element={<AdminRoute />}>
          <Route index element={<AdminDashboard />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="addons" element={<AdminAddons />} />
          <Route path="audit-log" element={<AdminAuditLog />} />
        </Route>
      </Route>
    </Routes>
  )
}
