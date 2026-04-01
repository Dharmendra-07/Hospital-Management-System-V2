// main.js
import { createApp } from 'vue'
import App    from './App.vue'
import router from './router'
import store  from './store'
import axios  from 'axios'

// Global styles
import './assets/main.css'

const app = createApp(App)

// Rehydrate auth token on every page load
store.dispatch('auth/initAuth')

// Axios interceptor — auto-refresh on 401
axios.interceptors.response.use(
  res => res,
  async err => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        await store.dispatch('auth/refreshToken')
        const token = store.state.auth.accessToken
        original.headers['Authorization'] = `Bearer ${token}`
        return axios(original)
      } catch (_) {
        store.dispatch('auth/logout')
        router.push('/login')
      }
    }
    return Promise.reject(err)
  }
)

app.use(store)
app.use(router)
app.mount('#app')
