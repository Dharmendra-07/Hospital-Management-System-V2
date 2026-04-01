<template>
  <div class="min-vh-100 d-flex align-items-center justify-content-center py-4"
       style="background:linear-gradient(135deg,#e8f0fe 0%,#f5f7fa 100%);">

    <div class="w-100" style="max-width:560px;padding:0 16px;">

      <!-- Brand -->
      <div class="text-center mb-4">
        <div style="font-size:48px;line-height:1;">🏥</div>
        <h1 style="font-size:20px;font-weight:700;margin-top:8px;color:#212529;">
          Create Patient Account
        </h1>
        <p class="text-muted small">Fill in your details to register</p>
      </div>

      <!-- Success state -->
      <div v-if="success" class="hms-card">
        <div class="card-body p-4 text-center">
          <div style="font-size:52px;">✅</div>
          <h5 class="fw-bold mt-3">Registration Successful!</h5>
          <p class="text-muted small">Your account has been created.</p>
          <router-link to="/login" class="btn btn-primary px-4">
            Sign In Now
          </router-link>
        </div>
      </div>

      <div v-else class="hms-card">
        <div class="card-body p-4">

          <!-- Global error -->
          <div v-if="globalError" class="alert alert-danger py-2 small">
            {{ globalError }}
          </div>

          <!-- Account details section -->
          <h6 class="fw-semibold text-muted mb-3 pb-2 border-bottom"
              style="font-size:12px;letter-spacing:.04em;text-transform:uppercase;">
            Account Details
          </h6>
          <div class="row g-2">
            <div class="col-12">
              <FormField v-model="form.full_name" label="Full Name" :required="true"
                         placeholder="Your full name" :error="errors.full_name"
                         @blur="touch('full_name')" />
            </div>
            <div class="col-sm-6">
              <FormField v-model="form.username" label="Username" :required="true"
                         placeholder="Choose a username" :error="errors.username"
                         hint="No spaces" @blur="touch('username')" />
            </div>
            <div class="col-sm-6">
              <FormField v-model="form.email" label="Email" type="email" :required="true"
                         placeholder="your@email.com" :error="errors.email"
                         @blur="touch('email')" />
            </div>
            <div class="col-sm-6">
              <FormField v-model="form.password" label="Password" type="password"
                         :required="true" placeholder="Min 6 characters"
                         :error="errors.password" @blur="touch('password')" />
            </div>
            <div class="col-sm-6">
              <FormField v-model="form.confirm_password" label="Confirm Password"
                         type="password" :required="true" placeholder="Repeat password"
                         :error="errors.confirm_password"
                         @blur="touch('confirm_password')" />
            </div>
          </div>

          <!-- Personal details section -->
          <h6 class="fw-semibold text-muted mb-3 pb-2 border-bottom mt-3"
              style="font-size:12px;letter-spacing:.04em;text-transform:uppercase;">
            Personal Details <span class="fw-normal">(optional)</span>
          </h6>
          <div class="row g-2">
            <div class="col-sm-6">
              <FormField v-model="form.gender" label="Gender" type="select"
                         :options="['Male','Female','Other']" />
            </div>
            <div class="col-sm-6">
              <FormField v-model="form.date_of_birth" label="Date of Birth" type="date" />
            </div>
            <div class="col-sm-6">
              <FormField v-model="form.contact_number" label="Contact Number" type="tel"
                         placeholder="+91 XXXXX XXXXX" :error="errors.contact_number"
                         @blur="touch('contact_number')" />
            </div>
            <div class="col-sm-6">
              <FormField v-model="form.blood_group" label="Blood Group" type="select"
                         :options="bloodGroups" />
            </div>
            <div class="col-12">
              <FormField v-model="form.address" label="Address" type="textarea"
                         :rows="2" placeholder="Your address" />
            </div>
          </div>

          <button class="btn btn-primary w-100 mt-3"
                  @click="handleRegister" :disabled="loading"
                  style="padding:10px;">
            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
            {{ loading ? 'Creating account…' : 'Create Account' }}
          </button>

          <p class="text-center mb-0 mt-3 text-muted small">
            Already have an account?
            <router-link to="/login" class="fw-semibold text-primary">Sign in</router-link>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { mapActions } from 'vuex'
import FormField from '../../components/shared/FormField.vue'
import { validateForm, schemas, validate, required, minLen, matches, isEmail, isPhone } from '../../utils/validators.js'

export default {
  name: 'RegisterView',
  components: { FormField },
  data() {
    return {
      form: {
        full_name: '', username: '', email: '',
        password: '', confirm_password: '',
        gender: '', date_of_birth: '',
        contact_number: '', blood_group: '', address: '',
      },
      errors:      {},
      globalError: '',
      loading:     false,
      success:     false,
      bloodGroups: ['A+','A-','B+','B-','AB+','AB-','O+','O-'],
    }
  },
  methods: {
    ...mapActions('auth', ['register']),

    touch(field) {
      const fieldSchema = {
        full_name:        [required('Full name')],
        username:         [required('Username'), minLen(3, 'Username')],
        email:            [required('Email'), isEmail],
        password:         [required('Password'), minLen(6, 'Password')],
        confirm_password: [matches(this.form.password, 'Passwords')],
        contact_number:   [isPhone],
      }
      if (fieldSchema[field]) {
        const err = validate(this.form[field], ...fieldSchema[field])
        if (err) {
          this.errors = { ...this.errors, [field]: err }
        } else {
          const { [field]: _, ...rest } = this.errors
          this.errors = rest
        }
      }
    },

    runValidation() {
      const errs = validateForm(this.form, schemas.patientRegister)
      if (this.form.password !== this.form.confirm_password) {
        errs.confirm_password = 'Passwords do not match.'
      }
      return errs
    },

    async handleRegister() {
      this.errors      = this.runValidation()
      this.globalError = ''
      if (Object.keys(this.errors).length) return

      this.loading = true
      try {
        const payload = { ...this.form }
        delete payload.confirm_password
        await this.register(payload)
        this.success = true
      } catch (err) {
        const resp = err.response?.data
        if (resp?.errors) {
          this.errors = resp.errors
        } else {
          this.globalError = resp?.error || 'Registration failed. Please try again.'
        }
      } finally {
        this.loading = false
      }
    },
  },
}
</script>
