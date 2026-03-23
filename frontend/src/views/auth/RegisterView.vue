<template>
  <div class="min-vh-100 d-flex align-items-center justify-content-center bg-light py-4">
    <div class="card shadow-sm" style="width: 100%; max-width: 520px;">

      <!-- Header -->
      <div class="card-header bg-success text-white text-center py-4">
        <h4 class="mb-0">🏥 HMS — Patient Register</h4>
        <small class="opacity-75">Create your account to book appointments</small>
      </div>

      <div class="card-body p-4">
        <!-- Success -->
        <div v-if="success" class="alert alert-success">
          ✅ Registration successful!
          <router-link to="/login" class="alert-link">Click here to login.</router-link>
        </div>

        <!-- Error -->
        <div v-if="error" class="alert alert-danger alert-dismissible">
          {{ error }}
          <button type="button" class="btn-close" @click="error = ''"></button>
        </div>

        <template v-if="!success">
          <!-- Account Info -->
          <h6 class="text-muted fw-semibold mb-3 border-bottom pb-1">Account Details</h6>

          <div class="row g-3 mb-3">
            <div class="col-12">
              <label class="form-label fw-semibold">Full Name <span class="text-danger">*</span></label>
              <input v-model="form.full_name" type="text" class="form-control" placeholder="John Doe" />
            </div>
            <div class="col-md-6">
              <label class="form-label fw-semibold">Username <span class="text-danger">*</span></label>
              <input v-model="form.username" type="text" class="form-control" placeholder="johnDoe123" />
            </div>
            <div class="col-md-6">
              <label class="form-label fw-semibold">Email <span class="text-danger">*</span></label>
              <input v-model="form.email" type="email" class="form-control" placeholder="john@example.com" />
            </div>
            <div class="col-md-6">
              <label class="form-label fw-semibold">Password <span class="text-danger">*</span></label>
              <input v-model="form.password" type="password" class="form-control" placeholder="Min 6 characters" />
            </div>
            <div class="col-md-6">
              <label class="form-label fw-semibold">Confirm Password <span class="text-danger">*</span></label>
              <input v-model="form.confirm_password" type="password" class="form-control" placeholder="Repeat password" />
            </div>
          </div>

          <!-- Personal Info -->
          <h6 class="text-muted fw-semibold mb-3 border-bottom pb-1">Personal Details</h6>
          <div class="row g-3 mb-4">
            <div class="col-md-6">
              <label class="form-label fw-semibold">Gender</label>
              <select v-model="form.gender" class="form-select">
                <option value="">Select</option>
                <option>Male</option>
                <option>Female</option>
                <option>Other</option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label fw-semibold">Date of Birth</label>
              <input v-model="form.date_of_birth" type="date" class="form-control" />
            </div>
            <div class="col-md-6">
              <label class="form-label fw-semibold">Contact Number</label>
              <input v-model="form.contact_number" type="tel" class="form-control" placeholder="+91 XXXXX XXXXX" />
            </div>
            <div class="col-md-6">
              <label class="form-label fw-semibold">Blood Group</label>
              <select v-model="form.blood_group" class="form-select">
                <option value="">Select</option>
                <option v-for="bg in bloodGroups" :key="bg">{{ bg }}</option>
              </select>
            </div>
            <div class="col-12">
              <label class="form-label fw-semibold">Address</label>
              <textarea v-model="form.address" class="form-control" rows="2" placeholder="Your address"></textarea>
            </div>
          </div>

          <button
            class="btn btn-success w-100"
            @click="handleRegister"
            :disabled="loading"
          >
            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
            {{ loading ? 'Registering...' : 'Create Account' }}
          </button>

          <hr />
          <p class="text-center mb-0 text-muted small">
            Already have an account?
            <router-link to="/login" class="text-primary fw-semibold">Login here</router-link>
          </p>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import { mapActions } from 'vuex'

export default {
  name: 'RegisterView',
  data() {
    return {
      form: {
        username: '', email: '', password: '', confirm_password: '',
        full_name: '', gender: '', date_of_birth: '',
        contact_number: '', blood_group: '', address: '',
      },
      bloodGroups: ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
      loading: false,
      error:   '',
      success: false,
    }
  },
  methods: {
    ...mapActions('auth', ['register']),

    validate() {
      const { username, email, password, confirm_password, full_name } = this.form
      if (!full_name || !username || !email || !password)
        return 'Please fill in all required fields.'
      if (password.length < 6)
        return 'Password must be at least 6 characters.'
      if (password !== confirm_password)
        return 'Passwords do not match.'
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
        return 'Please enter a valid email address.'
      return null
    },

    async handleRegister() {
      this.error = ''
      const validationError = this.validate()
      if (validationError) { this.error = validationError; return }

      this.loading = true
      try {
        const payload = { ...this.form }
        delete payload.confirm_password
        await this.register(payload)
        this.success = true
      } catch (err) {
        this.error = err.response?.data?.error || 'Registration failed. Please try again.'
      } finally {
        this.loading = false
      }
    },
  },
}
</script>
