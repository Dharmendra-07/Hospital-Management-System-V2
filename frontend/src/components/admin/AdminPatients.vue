<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <span class="text-muted small">{{ filtered.length }} patient(s)</span>
    </div>

    <div v-if="alert.msg" :class="`alert alert-${alert.type} alert-dismissible`">
      {{ alert.msg }}
      <button type="button" class="btn-close" @click="alert.msg=''"></button>
    </div>

    <!-- Table -->
    <div class="card border-0 shadow-sm">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>#</th>
              <th>Name</th>
              <th>Contact</th>
              <th>Gender</th>
              <th>Blood Group</th>
              <th>Appointments</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="8" class="text-center py-4">
              <div class="spinner-border spinner-border-sm text-primary"></div>
            </td></tr>
            <tr v-else-if="filtered.length === 0"><td colspan="8" class="text-center py-4 text-muted">
              No patients found.
            </td></tr>
            <tr v-else v-for="p in filtered" :key="p.id">
              <td class="text-muted small">{{ p.id }}</td>
              <td>
                <div class="fw-semibold">{{ p.full_name }}</div>
                <div class="text-muted small">{{ p.email }}</div>
              </td>
              <td>{{ p.contact_number || '—' }}</td>
              <td>{{ p.gender || '—' }}</td>
              <td>{{ p.blood_group || '—' }}</td>
              <td>{{ p.total_appointments }}</td>
              <td>
                <span :class="p.is_active ? 'badge bg-success' : 'badge bg-danger'">
                  {{ p.is_active ? 'Active' : 'Blacklisted' }}
                </span>
              </td>
              <td>
                <div class="d-flex gap-1">
                  <button class="btn btn-outline-primary btn-sm" @click="openEditModal(p)">Edit</button>
                  <button
                    :class="p.is_active ? 'btn btn-outline-danger btn-sm' : 'btn btn-outline-success btn-sm'"
                    @click="toggleBlacklist(p)"
                  >{{ p.is_active ? 'Blacklist' : 'Activate' }}</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Edit Patient Modal -->
    <div v-if="showModal" class="modal d-block" style="background:rgba(0,0,0,.5);">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Edit Patient Info</h5>
            <button type="button" class="btn-close" @click="showModal=false"></button>
          </div>
          <div class="modal-body">
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
                <label class="form-label fw-semibold">Contact Number</label>
                <input v-model="form.contact_number" type="tel" class="form-control" />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Gender</label>
                <select v-model="form.gender" class="form-select">
                  <option value="">Select</option>
                  <option>Male</option><option>Female</option><option>Other</option>
                </select>
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Blood Group</label>
                <select v-model="form.blood_group" class="form-select">
                  <option value="">Select</option>
                  <option v-for="bg in bloodGroups" :key="bg">{{ bg }}</option>
                </select>
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Address</label>
                <input v-model="form.address" type="text" class="form-control" />
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showModal=false">Cancel</button>
            <button class="btn btn-primary" @click="savePatient" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
              Save Changes
            </button>
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
  name: 'AdminPatients',
  props: { searchQuery: { type: String, default: '' } },
  data() {
    return {
      patients:    [],
      loading:     true,
      showModal:   false,
      editId:      null,
      form:        {},
      saving:      false,
      alert:       { msg: '', type: 'success' },
      bloodGroups: ['A+','A-','B+','B-','AB+','AB-','O+','O-'],
    }
  },
  computed: {
    filtered() {
      const q = this.searchQuery.toLowerCase()
      if (!q) return this.patients
      return this.patients.filter(p =>
        p.full_name.toLowerCase().includes(q) ||
        (p.contact_number || '').includes(q) ||
        p.email.toLowerCase().includes(q) ||
        String(p.id).includes(q)
      )
    },
  },
  async mounted() { await this.fetchPatients() },
  methods: {
    async fetchPatients() {
      this.loading = true
      try {
        const { data } = await axios.get(`${API}/admin/patients`)
        this.patients = data
      } catch (e) { console.error(e) }
      finally { this.loading = false }
    },
    openEditModal(p) {
      this.editId    = p.id
      this.form      = { full_name: p.full_name, email: p.email,
                         contact_number: p.contact_number, gender: p.gender,
                         blood_group: p.blood_group, address: p.address || '' }
      this.showModal = true
    },
    async savePatient() {
      this.saving = true
      try {
        await axios.put(`${API}/admin/patients/${this.editId}`, this.form)
        this.showAlert('Patient updated.', 'success')
        this.showModal = false
        await this.fetchPatients()
      } catch (e) {
        this.showAlert(e.response?.data?.error || 'Update failed.', 'danger')
      } finally { this.saving = false }
    },
    async toggleBlacklist(patient) {
      try {
        const { data } = await axios.patch(`${API}/admin/patients/${patient.id}/blacklist`)
        patient.is_active = data.is_active
        this.showAlert(data.message, 'success')
      } catch (e) {
        this.showAlert('Failed to update patient status.', 'danger')
      }
    },
    showAlert(msg, type = 'success') {
      this.alert = { msg, type }
      setTimeout(() => { this.alert.msg = '' }, 3000)
    },
  },
}
</script>
