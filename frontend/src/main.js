// main.js
import { createApp } from 'vue'
import App    from './App.vue'
import router from './router'
import store  from './store'
import axios  from 'axios'

// Bootstrap CSS (via CDN in index.html, or install bootstrap npm pkg)
// import 'bootstrap/dist/css/bootstrap.min.css'
// import 'bootstrap/dist/js/bootstrap.bundle.min.js'

const app = createApp(App)

// Rehydrate token from localStorage on every page load
store.dispatch('auth/initAuth')

// Axios interceptor — auto-refresh on 401
axios.interceptors.response.use(
  res => res,
  async err => {
    const originalRequest = err.config
    if (err.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        await store.dispatch('auth/refreshToken')
        const token = store.state.auth.accessToken
        originalRequest.headers['Authorization'] = `Bearer ${token}`
        return axios(originalRequest)
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
