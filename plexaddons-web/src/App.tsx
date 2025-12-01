import { Routes, Route } from 'react-router-dom'
import { Toaster } from 'sonner'
import Layout from './components/Layout'
import Home from './pages/Home'
import Addons from './pages/Addons'
import AddonDetail from './pages/AddonDetail'
import Users from './pages/Users'
import Pricing from './pages/Pricing'
import Docs from './pages/Docs'
import ApiDocs from './pages/ApiDocs'
import Login from './pages/Login'
import AuthCallback from './pages/AuthCallback'
import Profile from './pages/Profile'
import Dashboard from './pages/dashboard/Dashboard'
import MyAddons from './pages/dashboard/MyAddons'
import AddonEditor from './pages/dashboard/AddonEditor'
import VersionEditor from './pages/dashboard/VersionEditor'
import Settings from './pages/dashboard/Settings'
import Subscription from './pages/dashboard/Subscription'
import Analytics from './pages/dashboard/Analytics'
import Support from './pages/dashboard/Support'
import NewTicket from './pages/dashboard/NewTicket'
import TicketDetail from './pages/dashboard/TicketDetail'
import Organizations from './pages/dashboard/Organizations'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminUsers from './pages/admin/AdminUsers'
import AdminAddons from './pages/admin/AdminAddons'
import AdminAddonDetail from './pages/admin/AdminAddonDetail'
import AdminAuditLog from './pages/admin/AdminAuditLog'
import AdminTickets from './pages/admin/AdminTickets'
import AdminTicketDetail from './pages/admin/AdminTicketDetail'
import AdminCannedResponses from './pages/admin/AdminCannedResponses'
import ProtectedRoute from './components/ProtectedRoute'
import AdminRoute from './components/AdminRoute'

export default function App() {
  return (
    <>
      <Toaster 
        theme="dark"
        position="top-right"
        richColors
        closeButton
        toastOptions={{
          style: {
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            color: 'var(--text)',
          },
        }}
      />
      <Routes>
        <Route path="/" element={<Layout />}>
        {/* Public routes */}
        <Route index element={<Home />} />
        <Route path="addons" element={<Addons />} />
        <Route path="addons/:slug" element={<AddonDetail />} />
        <Route path="users" element={<Users />} />
        <Route path="u/:identifier" element={<Profile />} />
        <Route path="pricing" element={<Pricing />} />
        <Route path="docs" element={<Docs />} />
        <Route path="redocs" element={<ApiDocs />} />
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
          <Route path="analytics" element={<Analytics />} />
          <Route path="support" element={<Support />} />
          <Route path="support/new" element={<NewTicket />} />
          <Route path="support/:ticketId" element={<TicketDetail />} />
          <Route path="organizations" element={<Organizations />} />
        </Route>

        {/* Admin routes */}
        <Route path="admin" element={<AdminRoute />}>
          <Route index element={<AdminDashboard />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="addons" element={<AdminAddons />} />
          <Route path="addons/:addonId" element={<AdminAddonDetail />} />
          <Route path="audit-log" element={<AdminAuditLog />} />
          <Route path="tickets" element={<AdminTickets />} />
          <Route path="tickets/:ticketId" element={<AdminTicketDetail />} />
          <Route path="canned-responses" element={<AdminCannedResponses />} />
        </Route>
      </Route>
    </Routes>
    </>
  )
}
