<template>
  <div>
    <!-- Toolbar -->
    <div class="d-flex justify-content-between align-items-center mb-3">
      <span class="text-muted small">{{ filtered.length }} doctor(s)</span>
      <button class="btn btn-primary btn-sm" @click="openModal()">+ Add Doctor</button>
    </div>

    <!-- Alert -->
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
              <th>Specialization</th>
              <th>Department</th>
              <th>Experience</th>
              <th>Contact</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="8" class="text-center py-4">
              <div class="spinner-border spinner-border-sm text-primary"></div>
            </td></tr>
            <tr v-else-if="filtered.length === 0"><td colspan="8" class="text-center py-4 text-muted">
              No doctors found.
            </td></tr>
            <tr v-else v-for="d in filtered" :key="d.id">
              <td class="text-muted small">{{ d.id }}</td>
              <td>
                <div class="fw-semibold">{{ d.full_name }}</div>
                <div class="text-muted small">{{ d.username }}</div>
              </td>
              <td>{{ d.specialization }}</td>
              <td>{{ d.department || '—' }}</td>
              <td>{{ d.experience_years }} yr{{ d.experience_years !== 1 ? 's' : '' }}</td>
              <td>{{ d.contact_number || '—' }}</td>
              <td>
                <span :class="d.is_active ? 'badge bg-success' : 'badge bg-danger'">
                  {{ d.is_active ? 'Active' : 'Blacklisted' }}
                </span>
              </td>
              <td>
                <div class="d-flex gap-1">
                  <button class="btn btn-outline-primary btn-sm" @click="openModal(d)">Edit</button>
                  <button
                    :class="d.is_active ? 'btn btn-outline-danger btn-sm' : 'btn btn-outline-success btn-sm'"
                    @click="toggleBlacklist(d)"
                  >{{ d.is_active ? 'Blacklist' : 'Activate' }}</button>
                  <button class="btn btn-outline-secondary btn-sm" @click="viewPatientHistory(d)">History</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add / Edit Modal -->
    <div v-if="showModal" class="modal d-block" style="background:rgba(0,0,0,.5);">
      <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editMode ? 'Edit Doctor' : 'Add New Doctor' }}</h5>
            <button type="button" class="btn-close" @click="closeModal"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label fw-semibold">Full Name <span class="text-danger">*</span></label>
                <input v-model="form.full_name" type="text" class="form-control" />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Specialization <span class="text-danger">*</span></label>
                <input v-model="form.specialization" type="text" class="form-control" />
              </div>
              <div class="col-md-6" v-if="!editMode">
                <label class="form-label fw-semibold">Username <span class="text-danger">*</span></label>
                <input v-model="form.username" type="text" class="form-control" />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Email <span class="text-danger">*</span></label>
                <input v-model="form.email" type="email" class="form-control" />
              </div>
              <div class="col-md-6" v-if="!editMode">
                <label class="form-label fw-semibold">Password <span class="text-danger">*</span></label>
                <input v-model="form.password" type="password" class="form-control" placeholder="Min 6 chars" />
              </div>
              <div class="col-md-6" v-if="editMode">
                <label class="form-label fw-semibold">New Password <span class="text-muted small">(leave blank to keep)</span></label>
                <input v-model="form.password" type="password" class="form-control" />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Qualification</label>
                <input v-model="form.qualification" type="text" class="form-control" placeholder="MBBS, MD…" />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Experience (years)</label>
                <input v-model.number="form.experience_years" type="number" class="form-control" min="0" />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Contact Number</label>
                <input v-model="form.contact_number" type="tel" class="form-control" />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Department</label>
                <select v-model="form.department_id" class="form-select">
                  <option value="">Select department</option>
                  <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
                </select>
              </div>
              <div class="col-12">
                <label class="form-label fw-semibold">Bio</label>
                <textarea v-model="form.bio" class="form-control" rows="3"></textarea>
              </div>
            </div>
            <div v-if="formError" class="alert alert-danger mt-3 mb-0">{{ formError }}</div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="closeModal">Cancel</button>
            <button class="btn btn-primary" @click="saveDoctor" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
              {{ editMode ? 'Save Changes' : 'Add Doctor' }}
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

const emptyForm = () => ({
  full_name: '', username: '', email: '', password: '',
  specialization: '', qualification: '', experience_years: 0,
  contact_number: '', bio: '', department_id: '',
})

export default {
  name: 'AdminDoctors',
  props: { searchQuery: { type: String, default: '' } },
  data() {
    return {
      doctors:     [],
      departments: [],
      loading:     true,
      showModal:   false,
      editMode:    false,
      editId:      null,
      form:        emptyForm(),
      formError:   '',
      saving:      false,
      alert:       { msg: '', type: 'success' },
    }
  },
  computed: {
    filtered() {
      const q = this.searchQuery.toLowerCase()
      if (!q) return this.doctors
      return this.doctors.filter(d =>
        d.full_name.toLowerCase().includes(q) ||
        d.specialization.toLowerCase().includes(q) ||
        (d.department || '').toLowerCase().includes(q)
      )
    },
  },
  async mounted() {
    await this.fetchDoctors()
    await this.fetchDepartments()
  },
  methods: {
    async fetchDoctors() {
      this.loading = true
      try {
        const { data } = await axios.get(`${API}/admin/doctors`)
        this.doctors = data
      } catch (e) { console.error(e) }
      finally { this.loading = false }
    },
    async fetchDepartments() {
      try {
        const { data } = await axios.get(`${API}/admin/departments`)
        this.departments = data
      } catch (e) { console.error(e) }
    },
    openModal(doctor = null) {
      this.formError = ''
      if (doctor) {
        this.editMode = true
        this.editId   = doctor.id
        this.form = {
          full_name:        doctor.full_name,
          username:         doctor.username,
          email:            doctor.email,
          password:         '',
          specialization:   doctor.specialization,
          qualification:    doctor.qualification || '',
          experience_years: doctor.experience_years || 0,
          contact_number:   doctor.contact_number || '',
          bio:              doctor.bio || '',
          department_id:    doctor.department_id || '',
        }
      } else {
        this.editMode = false
        this.editId   = null
        this.form = emptyForm()
      }
      this.showModal = true
    },
    closeModal() { this.showModal = false },
    async saveDoctor() {
      this.formError = ''
      if (!this.form.full_name || !this.form.specialization) {
        this.formError = 'Full name and specialization are required.'
        return
      }
      if (!this.editMode && (!this.form.username || !this.form.email || !this.form.password)) {
        this.formError = 'Username, email, and password are required.'
        return
      }
      this.saving = true
      try {
        if (this.editMode) {
          await axios.put(`${API}/admin/doctors/${this.editId}`, this.form)
          this.showAlert('Doctor updated successfully.', 'success')
        } else {
          await axios.post(`${API}/admin/doctors`, this.form)
          this.showAlert('Doctor added successfully.', 'success')
        }
        this.closeModal()
        await this.fetchDoctors()
      } catch (e) {
        this.formError = e.response?.data?.error || 'Failed to save. Please try again.'
      } finally {
        this.saving = false
      }
    },
    async toggleBlacklist(doctor) {
      try {
        const { data } = await axios.patch(`${API}/admin/doctors/${doctor.id}/blacklist`)
        doctor.is_active = data.is_active
        this.showAlert(data.message, 'success')
      } catch (e) {
        this.showAlert('Failed to update doctor status.', 'danger')
      }
    },
    viewPatientHistory(doctor) {
      // Placeholder — hook into patient history modal if needed
      alert(`Viewing history for Dr. ${doctor.full_name} (coming in doctor milestone)`)
    },
    showAlert(msg, type = 'success') {
      this.alert = { msg, type }
      setTimeout(() => { this.alert.msg = '' }, 3000)
    },
  },
}
</script>
