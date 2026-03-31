// router/index.js — Vue Router with RBAC navigation guards

import { createRouter, createWebHistory } from 'vue-router'
import store from '../store'

// ── Lazy-loaded views ─────────────────────────────────────────
const LoginView          = () => import('../views/auth/LoginView.vue')
const RegisterView       = () => import('../views/auth/RegisterView.vue')
const AdminDashboard     = () => import('../views/admin/AdminDashboard.vue')
const DoctorDashboard    = () => import('../views/doctor/DoctorDashboard.vue')
const PatientDashboard   = () => import('../views/patient/PatientDashboard.vue')
const NotFound           = () => import('../views/NotFound.vue')
const Unauthorized       = () => import('../views/Unauthorized.vue')

const routes = [
  // ── Public ──────────────────────────────
  { path: '/',        redirect: '/login' },
  { path: '/login',   name: 'Login',    component: LoginView,    meta: { guest: true } },
  { path: '/register',name: 'Register', component: RegisterView, meta: { guest: true } },

  // ── Admin ────────────────────────────────
  {
    path: '/admin',
    meta: { requiresAuth: true, role: 'admin' },
    children: [
      { path: 'dashboard', name: 'AdminDashboard', component: AdminDashboard },
    ]
  },

  // ── Doctor ───────────────────────────────
  {
    path: '/doctor',
    meta: { requiresAuth: true, role: 'doctor' },
    children: [
      { path: 'dashboard', name: 'DoctorDashboard', component: DoctorDashboard },
    ]
  },

  // ── Patient ──────────────────────────────
  {
    path: '/patient',
    meta: { requiresAuth: true, role: 'patient' },
    children: [
      { path: 'dashboard', name: 'PatientDashboard', component: PatientDashboard },
    ]
  },

  // ── Fallbacks ────────────────────────────
  { path: '/unauthorized', name: 'Unauthorized', component: Unauthorized },
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: NotFound },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ── Global Navigation Guard ───────────────────────────────────
router.beforeEach((to, from, next) => {
  const isAuthenticated = store.getters['auth/isAuthenticated']
  const userRole        = store.getters['auth/userRole']

  // Redirect logged-in users away from guest pages
  if (to.meta.guest && isAuthenticated) {
    const dashMap = { admin: '/admin/dashboard', doctor: '/doctor/dashboard', patient: '/patient/dashboard' }
    return next(dashMap[userRole] || '/')
  }

  // Route requires auth
  if (to.meta.requiresAuth) {
    if (!isAuthenticated) return next({ name: 'Login', query: { redirect: to.fullPath } })

    // Role check — walk up meta chain (child inherits parent meta)
    const requiredRole = to.meta.role || to.matched.find(r => r.meta.role)?.meta.role
    if (requiredRole && userRole !== requiredRole) {
      return next({ name: 'Unauthorized' })
    }
  }

  next()
})

export default router
