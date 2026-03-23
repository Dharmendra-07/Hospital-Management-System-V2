<template>
  <div>
    <!-- Filters -->
    <div class="card border-0 shadow-sm mb-3">
      <div class="card-body py-2 d-flex flex-wrap gap-2 align-items-center">
        <span class="text-muted small fw-semibold">View:</span>
        <button v-for="v in viewOptions" :key="v.val"
                :class="['btn btn-sm', activeView === v.val ? v.active : v.outline]"
                @click="setView(v.val)">{{ v.label }}</button>
        <span class="ms-2 text-muted small fw-semibold">Status:</span>
        <button v-for="s in statusOptions" :key="s.val"
                :class="['btn btn-sm', activeStatus === s.val ? s.active : s.outline]"
                @click="setStatus(s.val)">{{ s.label }}</button>
      </div>
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
              <th>#</th><th>Patient</th><th>Date</th>
              <th>Time Slot</th><th>Type</th><th>Status</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7" class="text-center py-4">
                <div class="spinner-border spinner-border-sm text-primary"></div>
              </td>
            </tr>
            <tr v-else-if="appointments.length === 0">
              <td colspan="7" class="text-center py-4 text-muted">No appointments found.</td>
            </tr>
            <tr v-else v-for="a in appointments" :key="a.id">
              <td class="text-muted small">{{ a.id }}</td>
              <td class="fw-semibold">{{ a.patient_name }}</td>
              <td>{{ a.date }}</td>
              <td><span class="badge bg-secondary">{{ a.time_slot }}</span></td>
              <td>{{ a.visit_type }}</td>
              <td><span :class="statusBadge(a.status)">{{ a.status }}</span></td>
              <td>
                <div class="d-flex gap-1 flex-wrap">
                  <button v-if="a.status === 'Booked'"
                          class="btn btn-success btn-sm"
                          @click="openTreatment(a)">
                    + Treatment
                  </button>
                  <button v-if="a.status === 'Booked'"
                          class="btn btn-outline-danger btn-sm"
                          @click="cancelAppt(a)">Cancel</button>
                  <button v-if="a.has_treatment || a.status === 'Completed'"
                          class="btn btn-outline-primary btn-sm"
                          @click="openTreatment(a)">View/Edit</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="card-footer bg-white d-flex justify-content-between align-items-center"
           v-if="totalPages > 1">
        <small class="text-muted">Page {{ page }} of {{ totalPages }}</small>
        <div class="d-flex gap-1">
          <button class="btn btn-outline-secondary btn-sm"
                  :disabled="page === 1" @click="changePage(page-1)">‹</button>
          <button class="btn btn-outline-secondary btn-sm"
                  :disabled="page === totalPages" @click="changePage(page+1)">›</button>
        </div>
      </div>
    </div>

    <!-- ── Treatment Modal ─────────────────── -->
    <div v-if="showTreatment" class="modal d-block" style="background:rgba(0,0,0,.5);">
      <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <div>
              <h5 class="modal-title mb-0">Treatment — {{ selected?.patient_name }}</h5>
              <div class="text-muted small">Appointment #{{ selected?.id }} · {{ selected?.date }} · {{ selected?.time_slot }}</div>
            </div>
            <button type="button" class="btn-close" @click="showTreatment=false"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label fw-semibold">Visit Type</label>
                <input :value="selected?.visit_type" class="form-control" disabled />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Tests Done</label>
                <input v-model="treatForm.tests_done" type="text"
                       class="form-control" placeholder="ECG, Blood Test…" />
              </div>
              <div class="col-12">
                <label class="form-label fw-semibold">Diagnosis <span class="text-danger">*</span></label>
                <textarea v-model="treatForm.diagnosis" class="form-control" rows="3"
                          placeholder="Enter diagnosis…"></textarea>
              </div>
              <div class="col-12">
                <label class="form-label fw-semibold">Prescription</label>
                <textarea v-model="treatForm.prescription" class="form-control" rows="2"
                          placeholder="Enter prescription…"></textarea>
              </div>

              <!-- Medicines -->
              <div class="col-12">
                <label class="form-label fw-semibold d-flex justify-content-between">
                  <span>Medicines</span>
                  <button class="btn btn-outline-primary btn-sm" @click="addMedicine">+ Add</button>
                </label>
                <div v-for="(med, idx) in treatForm.medicines" :key="idx"
                     class="d-flex gap-2 mb-2 align-items-center">
                  <input v-model="med.name" class="form-control form-control-sm"
                         placeholder="Medicine name" />
                  <input v-model="med.dosage" class="form-control form-control-sm"
                         placeholder="Dosage (1-0-1)" style="max-width:120px;" />
                  <button class="btn btn-outline-danger btn-sm"
                          @click="removeMedicine(idx)">✕</button>
                </div>
                <div v-if="treatForm.medicines.length === 0"
                     class="text-muted small">No medicines added yet.</div>
              </div>

              <div class="col-md-6">
                <label class="form-label fw-semibold">Next Visit Date</label>
                <input v-model="treatForm.next_visit" type="date" class="form-control" />
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold">Doctor Notes</label>
                <textarea v-model="treatForm.doctor_notes" class="form-control" rows="2"
                          placeholder="Internal notes…"></textarea>
              </div>
            </div>
            <div v-if="treatError" class="alert alert-danger mt-3 mb-0">{{ treatError }}</div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showTreatment=false">Cancel</button>
            <button class="btn btn-primary" @click="saveTreatment" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
              Save Treatment & Mark Complete
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

const emptyTreat = () => ({
  diagnosis: '', prescription: '', medicines: [],
  tests_done: '', next_visit: '', doctor_notes: '',
})

export default {
  name: 'DoctorAppointments',
  data() {
    return {
      appointments:  [],
      loading:       true,
      page:          1,
      totalPages:    1,
      activeView:    'upcoming',
      activeStatus:  '',
      showTreatment: false,
      selected:      null,
      treatForm:     emptyTreat(),
      treatError:    '',
      saving:        false,
      alert:         { msg: '', type: 'success' },
      viewOptions: [
        { val: 'upcoming', label: 'Upcoming', active: 'btn-primary',   outline: 'btn-outline-primary'   },
        { val: 'past',     label: 'Past',     active: 'btn-secondary', outline: 'btn-outline-secondary' },
        { val: 'all',      label: 'All',      active: 'btn-dark',      outline: 'btn-outline-dark'      },
      ],
      statusOptions: [
        { val: '',          label: 'All',       active: 'btn-secondary', outline: 'btn-outline-secondary' },
        { val: 'Booked',    label: 'Booked',    active: 'btn-primary',   outline: 'btn-outline-primary'   },
        { val: 'Completed', label: 'Completed', active: 'btn-success',   outline: 'btn-outline-success'   },
        { val: 'Cancelled', label: 'Cancelled', active: 'btn-danger',    outline: 'btn-outline-danger'    },
      ],
    }
  },
  async mounted() { await this.fetch() },
  methods: {
    async fetch() {
      this.loading = true
      try {
        const params = { page: this.page, per_page: 15, view: this.activeView }
        if (this.activeStatus) params.status = this.activeStatus
        const { data } = await axios.get(`${API}/doctor/appointments`, { params })
        this.appointments = data.appointments
        this.totalPages   = data.pages
      } catch (e) { console.error(e) }
      finally { this.loading = false }
    },
    setView(v)   { this.activeView = v;   this.page = 1; this.fetch() },
    setStatus(s) { this.activeStatus = s; this.page = 1; this.fetch() },
    changePage(p){ this.page = p; this.fetch() },

    openTreatment(appt) {
      this.selected   = appt
      this.treatError = ''
      this.treatForm  = emptyTreat()

      // Pre-fill if treatment exists — fetch fresh
      if (appt.has_treatment) {
        axios.get(`${API}/doctor/patients/${appt.patient_id}/history`).then(({ data }) => {
          const entry = data.history.find(h => h.appointment_id === appt.id)
          if (entry?.treatment) {
            const t = entry.treatment
            this.treatForm = {
              diagnosis:    t.diagnosis    || '',
              prescription: t.prescription || '',
              medicines:    t.medicines    || [],
              tests_done:   t.tests_done   || '',
              next_visit:   t.next_visit   || '',
              doctor_notes: t.doctor_notes || '',
            }
          }
        }).catch(() => {})
      }
      this.showTreatment = true
    },

    addMedicine()          { this.treatForm.medicines.push({ name: '', dosage: '' }) },
    removeMedicine(idx)    { this.treatForm.medicines.splice(idx, 1) },

    async saveTreatment() {
      if (!this.treatForm.diagnosis.trim()) {
        this.treatError = 'Diagnosis is required.'
        return
      }
      this.saving = true
      try {
        await axios.post(`${API}/doctor/appointments/${this.selected.id}/treatment`, this.treatForm)
        this.showTreatment = false
        this.showAlert('Treatment saved and appointment marked complete.', 'success')
        await this.fetch()
      } catch (e) {
        this.treatError = e.response?.data?.error || 'Failed to save treatment.'
      } finally { this.saving = false }
    },

    async cancelAppt(a) {
      if (!confirm(`Cancel appointment #${a.id} for ${a.patient_name}?`)) return
      try {
        await axios.patch(`${API}/doctor/appointments/${a.id}/status`, { status: 'Cancelled' })
        a.status = 'Cancelled'
        this.showAlert('Appointment cancelled.', 'success')
        await this.fetch()
      } catch (e) {
        this.showAlert(e.response?.data?.error || 'Failed to cancel.', 'danger')
      }
    },

    statusBadge(s) {
      return { Booked: 'badge bg-primary', Completed: 'badge bg-success', Cancelled: 'badge bg-danger' }[s] || 'badge bg-secondary'
    },
    showAlert(msg, type = 'success') {
      this.alert = { msg, type }
      setTimeout(() => { this.alert.msg = '' }, 3500)
    },
  },
}
</script>
