<template>
  <div class="min-vh-100 d-flex align-items-center justify-content-center bg-light">
    <div class="card shadow-sm" style="width: 100%; max-width: 420px;">

      <!-- Header -->
      <div class="card-header bg-primary text-white text-center py-4">
        <h4 class="mb-0">🏥 HMS — Login</h4>
        <small class="opacity-75">Hospital Management System</small>
      </div>

      <div class="card-body p-4">
        <!-- Error Alert -->
        <div v-if="error" class="alert alert-danger alert-dismissible" role="alert">
          {{ error }}
          <button type="button" class="btn-close" @click="error = ''"></button>
        </div>

        <!-- Form -->
        <div class="mb-3">
          <label class="form-label fw-semibold">Username</label>
          <input
            v-model="form.username"
            type="text"
            class="form-control"
            placeholder="Enter username"
            @keyup.enter="handleLogin"
            autofocus
          />
        </div>

        <div class="mb-3">
          <label class="form-label fw-semibold">Password</label>
          <div class="input-group">
            <input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              class="form-control"
              placeholder="Enter password"
              @keyup.enter="handleLogin"
            />
            <button class="btn btn-outline-secondary" type="button" @click="showPassword = !showPassword">
              {{ showPassword ? '🙈' : '👁️' }}
            </button>
          </div>
        </div>

        <button
          class="btn btn-primary w-100 mt-2"
          @click="handleLogin"
          :disabled="loading"
        >
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>

        <hr />
        <p class="text-center mb-0 text-muted small">
          Don't have an account?
          <router-link to="/register" class="text-primary fw-semibold">Register as Patient</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import { mapActions } from 'vuex'

export default {
  name: 'LoginView',
  data() {
    return {
      form:         { username: '', password: '' },
      loading:      false,
      error:        '',
      showPassword: false,
    }
  },
  methods: {
    ...mapActions('auth', ['login']),

    async handleLogin() {
      this.error = ''
      if (!this.form.username || !this.form.password) {
        this.error = 'Please enter both username and password.'
        return
      }
      this.loading = true
      try {
        const data = await this.login(this.form)
        // Navigate to role-specific dashboard
        const redirect = this.$route.query.redirect || data.redirect
        this.$router.push(redirect)
      } catch (err) {
        this.error = err.response?.data?.error || 'Login failed. Please try again.'
      } finally {
        this.loading = false
      }
    },
  },
}
</script>
