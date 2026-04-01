<template>
  <div class="min-vh-100 d-flex align-items-center justify-content-center"
       style="background:linear-gradient(135deg,#e8f0fe 0%,#f5f7fa 100%);">

    <div class="w-100" style="max-width:420px;padding:0 16px;">

      <!-- Brand -->
      <div class="text-center mb-4">
        <div style="font-size:52px;line-height:1;">🏥</div>
        <h1 style="font-size:22px;font-weight:700;margin-top:8px;color:#212529;">HMS V2</h1>
        <p class="text-muted small">Hospital Management System</p>
      </div>

      <!-- Card -->
      <div class="hms-card">
        <div class="card-body p-4">
          <h5 class="fw-bold mb-4" style="font-size:16px;">Sign In</h5>

          <!-- Global error -->
          <div v-if="globalError" class="alert alert-danger py-2 small" role="alert">
            {{ globalError }}
          </div>

          <!-- Username -->
          <FormField
            v-model="form.username"
            label="Username"
            placeholder="Enter your username"
            :required="true"
            :error="errors.username"
            @blur="touch('username')"
          />

          <!-- Password -->
          <FormField
            v-model="form.password"
            label="Password"
            type="password"
            placeholder="Enter your password"
            :required="true"
            :error="errors.password"
            @blur="touch('password')"
          />

          <!-- Submit -->
          <button
            class="btn btn-primary w-100 mt-2"
            @click="handleLogin"
            :disabled="loading"
            style="padding:10px;"
          >
            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
            {{ loading ? 'Signing in…' : 'Sign In' }}
          </button>

          <hr class="my-3" />

          <p class="text-center mb-0 text-muted small">
            New patient?
            <router-link to="/register" class="fw-semibold text-primary">
              Create an account
            </router-link>
          </p>
        </div>
      </div>

      <!-- Role hint -->
      <div class="text-center mt-3">
        <small class="text-muted">
          Doctors & admins receive credentials from the hospital administrator.
        </small>
      </div>
    </div>
  </div>
</template>

<script>
import { mapActions } from 'vuex'
import FormField from '../../components/shared/FormField.vue'
import { validateForm, schemas } from '../../utils/validators.js'

export default {
  name: 'LoginView',
  components: { FormField },
  data() {
    return {
      form:        { username: '', password: '' },
      errors:      {},
      globalError: '',
      loading:     false,
      touched:     new Set(),
    }
  },
  methods: {
    ...mapActions('auth', ['login']),
    touch(field) {
      this.touched.add(field)
      this.errors = validateForm(this.form, schemas.login)
    },
    async handleLogin() {
      this.errors      = validateForm(this.form, schemas.login)
      this.globalError = ''
      if (Object.keys(this.errors).length) return

      this.loading = true
      try {
        const data = await this.login(this.form)
        const redirect = this.$route.query.redirect || data.redirect
        this.$router.push(redirect)
      } catch (err) {
        const resp = err.response?.data
        if (resp?.errors) {
          this.errors = resp.errors
        } else {
          this.globalError = resp?.error || 'Login failed. Please try again.'
        }
      } finally {
        this.loading = false
      }
    },
  },
}
</script>
