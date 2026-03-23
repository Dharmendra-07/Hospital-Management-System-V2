<template>
  <div class="row justify-content-center">
    <div class="col-lg-8">
      <div class="card border-0 shadow-sm">
        <div class="card-header bg-white fw-semibold border-bottom d-flex justify-content-between">
          <span>👤 My Profile</span>
          <button v-if="!editMode" class="btn btn-outline-primary btn-sm"
                  @click="editMode=true">Edit Profile</button>
        </div>

        <div v-if="loading" class="card-body text-center py-5">
          <div class="spinner-border text-primary"></div>
        </div>

        <div v-else class="card-body">
          <div v-if="alert.msg" :class="`alert alert-${alert.type} alert-dismissible mb-4`">
            {{ alert.msg }}
            <button type="button" class="btn-close" @click="alert.msg=''"></button>
          </div>

          <!-- View mode -->
          <div v-if="!editMode">
            <div class="d-flex align-items-center gap-3 mb-4">
              <div class="rounded-circle bg-primary bg-opacity-10 text-primary fw-bold
                          d-flex align-items-center justify-content-center"
                   style="width:64px;height:64px;font-size:24px;">
                {{ (profile.full_name || '?').charAt(0) }}
              </div>
              <div>
                <div class="fw-bold fs-5">{{ profile.full_name }}</div>
                <div class="text-muted">@{{ profile.username }}</div>
              </div>
            </div>
            <dl class="row mb-0">
              <dt class="col-sm-4 text-muted small">Email</dt>
              <dd class="col-sm-8">{{ profile.email }}</dd>
              <dt class="col-sm-4 text-muted small">Gender</dt>
              <dd class="col-sm-8">{{ profile.gender || '—' }}</dd>
              <dt class="col-sm-4 text-muted small">Date of Birth</dt>
              <dd class="col-sm-8">{{ profile.date_of_birth || '—' }}</dd>
              <dt class="col-sm-4 text-muted small">Blood Group</dt>
              <dd class="col-sm-8">{{ profile.blood_group || '—' }}</dd>
              <dt class="col-sm-4 text-muted small">Contact</dt>
              <dd class="col-sm-8">{{ profile.contact_number || '—' }}</dd>
              <dt class="col-sm-4 text-muted small">Emergency Contact</dt>
              <dd class="col-sm-8">{{ profile.emergency_contact || '—' }}</dd>
              <dt class="col-sm-4 text-muted small">Address</dt>
              <dd class="col-sm-8">{{ profile.address || '—' }}</dd>
            </dl>
          </div>

          <!-- Edit mode -->
          <div v-else>
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label fw-semibold">Full Name</label>
                <input v-model="form.full_name" type="text" class="form-control" />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Email</label>
                <input v-model="form.email" type="email" class="form-control" />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Gender</label>
                <select v-model="form.gender" class="form-select">
                  <option value="">Select</option>
                  <option>Male</option><option>Female</option><option>Other</option>
                </select>
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Date of Birth</label>
                <input v-model="form.date_of_birth" type="date" class="form-control" />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Blood Group</label>
                <select v-model="form.blood_group" class="form-select">
                  <option value="">Select</option>
                  <option v-for="bg in bloodGroups" :key="bg">{{ bg }}</option>
                </select>
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Contact Number</label>
                <input v-model="form.contact_number" type="tel" class="form-control" />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Emergency Contact</label>
                <input v-model="form.emergency_contact" type="tel" class="form-control" />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">
                  New Password
                  <span class="text-muted small fw-normal">(leave blank to keep)</span>
                </label>
                <input v-model="form.password" type="password" class="form-control"
                       placeholder="Min 6 characters" />
              </div>
              <div class="col-12">
                <label class="form-label fw-semibold">Address</label>
                <textarea v-model="form.address" class="form-control" rows="2"></textarea>
              </div>
            </div>

            <div class="d-flex gap-2 mt-4">
              <button class="btn btn-secondary" @click="cancelEdit">Cancel</button>
              <button class="btn btn-primary" @click="saveProfile" :disabled="saving">
                <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
                Save Changes
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'PatientProfile',
  emits: ['updated'],
  data() {
    return {
      profile:     {},
      form:        {},
      editMode:    false,
      loading:     true,
      saving:      false,
      alert:       { msg: '', type: 'success' },
      bloodGroups: ['A+','A-','B+','B-','AB+','AB-','O+','O-'],
    }
  },
  async mounted() { await this.fetchProfile() },
  methods: {
    async fetchProfile() {
      this.loading = true
      try {
        const { data } = await axios.get(`${API}/patient/profile`)
        this.profile = data
        this.form    = { ...data, password: '' }
      } catch (e) { console.error(e) }
      finally { this.loading = false }
    },
    cancelEdit() {
      this.form     = { ...this.profile, password: '' }
      this.editMode = false
    },
    async saveProfile() {
      this.saving = true
      try {
        await axios.put(`${API}/patient/profile`, this.form)
        await this.fetchProfile()
        this.editMode = false
        this.showAlert('Profile updated successfully.', 'success')
        this.$emit('updated')
      } catch (e) {
        this.showAlert(e.response?.data?.error || 'Update failed.', 'danger')
      } finally { this.saving = false }
    },
    showAlert(msg, type='success') {
      this.alert = { msg, type }
      setTimeout(() => { this.alert.msg = '' }, 3500)
    },
  },
}
</script>
