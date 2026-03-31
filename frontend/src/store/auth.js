// store/auth.js  — Vuex module for JWT auth state

import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

const state = () => ({
  accessToken:  localStorage.getItem('access_token')  || null,
  refreshToken: localStorage.getItem('refresh_token') || null,
  user: JSON.parse(localStorage.getItem('user') || 'null'),
})

const getters = {
  isAuthenticated: s => !!s.accessToken,
  currentUser:     s => s.user,
  userRole:        s => s.user?.role || null,
  isAdmin:         s => s.user?.role === 'admin',
  isDoctor:        s => s.user?.role === 'doctor',
  isPatient:       s => s.user?.role === 'patient',
}

const mutations = {
  SET_TOKENS(state, { access_token, refresh_token }) {
    state.accessToken  = access_token
    state.refreshToken = refresh_token
    localStorage.setItem('access_token',  access_token)
    localStorage.setItem('refresh_token', refresh_token)
    // Attach to every axios request
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
  },
  SET_USER(state, user) {
    state.user = user
    localStorage.setItem('user', JSON.stringify(user))
  },
  CLEAR_AUTH(state) {
    state.accessToken  = null
    state.refreshToken = null
    state.user         = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    delete axios.defaults.headers.common['Authorization']
  },
}

const actions = {
  // ── Patient Registration ──────────────────
  async register({ commit }, payload) {
    const { data } = await axios.post(`${API}/auth/register`, payload)
    return data
  },

  // ── Login (all roles) ─────────────────────
  async login({ commit }, { username, password }) {
    const { data } = await axios.post(`${API}/auth/login`, { username, password })
    commit('SET_TOKENS', {
      access_token:  data.access_token,
      refresh_token: data.refresh_token,
    })
    commit('SET_USER', {
      user_id:  data.user_id,
      username: data.username,
      role:     data.role,
    })
    return data   // caller uses data.redirect for router.push
  },

  // ── Fetch full profile ────────────────────
  async fetchMe({ commit }) {
    const { data } = await axios.get(`${API}/auth/me`)
    commit('SET_USER', data)
    return data
  },

  // ── Refresh access token ──────────────────
  async refreshToken({ state, commit }) {
    const { data } = await axios.post(
      `${API}/auth/refresh`, {},
      { headers: { Authorization: `Bearer ${state.refreshToken}` } }
    )
    commit('SET_TOKENS', {
      access_token:  data.access_token,
      refresh_token: state.refreshToken,
    })
  },

  // ── Logout ────────────────────────────────
  async logout({ commit }) {
    try { await axios.post(`${API}/auth/logout`) } catch (_) {}
    commit('CLEAR_AUTH')
  },

  // ── Rehydrate token on app boot ───────────
  initAuth({ state }) {
    if (state.accessToken) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${state.accessToken}`
    }
  },
}

export default { namespaced: true, state, getters, mutations, actions }
