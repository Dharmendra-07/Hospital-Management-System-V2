<template>
  <div>
    <!-- Filters -->
    <div class="card border-0 shadow-sm mb-3">
      <div class="card-body py-2">
        <div class="d-flex gap-2 flex-wrap align-items-center">
          <span class="text-muted small fw-semibold me-1">Filter:</span>
          <button
            v-for="s in statusOptions" :key="s.value"
            :class="['btn btn-sm', activeStatus === s.value ? s.active : s.outline]"
            @click="setStatus(s.value)"
          >{{ s.label }}</button>
        </div>
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
              <th>#</th>
              <th>Patient</th>
              <th>Doctor</th>
              <th>Department</th>
              <th>Date</th>
              <th>Slot</th>
              <th>Type</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="9" class="text-center py-4">
              <div class="spinner-border spinner-border-sm text-primary"></div>
            </td></tr>
            <tr v-else-if="appointments.length === 0"><td colspan="9" class="text-center py-4 text-muted">
              No appointments found.
            </td></tr>
            <tr v-else v-for="a in appointments" :key="a.id">
              <td class="text-muted small">{{ a.id }}</td>
              <td>{{ a.patient_name }}</td>
              <td>{{ a.doctor_name }}</td>
              <td>{{ a.department || '—' }}</td>
              <td>{{ a.date }}</td>
              <td><span class="badge bg-secondary">{{ a.time_slot }}</span></td>
              <td>{{ a.visit_type }}</td>
              <td>
                <span :class="statusBadge(a.status)">{{ a.status }}</span>
              </td>
              <td>
                <div class="d-flex gap-1">
                  <button class="btn btn-outline-primary btn-sm" @click="viewDetail(a)">View</button>
                  <button
                    v-if="a.status === 'Booked'"
                    class="btn btn-outline-danger btn-sm"
                    @click="cancelAppointment(a)"
                  >Cancel</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="card-footer bg-white d-flex justify-content-between align-items-center"
           v-if="totalPages > 1">
        <small class="text-muted">Page {{ page }} of {{ totalPages }} ({{ total }} total)</small>
        <div class="d-flex gap-1">
          <button class="btn btn-outline-secondary btn-sm" :disabled="page === 1"
                  @click="changePage(page - 1)">‹ Prev</button>
          <button class="btn btn-outline-secondary btn-sm" :disabled="page === totalPages"
                  @click="changePage(page + 1)">Next ›</button>
        </div>
      </div>
    </div>

    <!-- Detail Modal -->
    <div v-if="selected" class="modal d-block" style="background:rgba(0,0,0,.5);">
      <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Appointment #{{ selected.id }}</h5>
            <button type="button" class="btn-close" @click="selected=null"></button>
          </div>
          <div class="modal-body">
            <dl class="row mb-0">
              <dt class="col-5">Patient</dt>   <dd class="col-7">{{ selected.patient_name }}</dd>
              <dt class="col-5">Doctor</dt>    <dd class="col-7">{{ selected.doctor_name }}</dd>
              <dt class="col-5">Date</dt>      <dd class="col-7">{{ selected.date }}</dd>
              <dt class="col-5">Time Slot</dt> <dd class="col-7">{{ selected.time_slot }}</dd>
              <dt class="col-5">Status</dt>    <dd class="col-7">
                <span :class="statusBadge(selected.status)">{{ selected.status }}</span>
              </dd>
              <template v-if="selected.treatment">
                <dt class="col-5 mt-2">Diagnosis</dt>
                <dd class="col-7 mt-2">{{ selected.treatment.diagnosis || '—' }}</dd>
                <dt class="col-5">Prescription</dt>
                <dd class="col-7">{{ selected.treatment.prescription || '—' }}</dd>
                <dt class="col-5">Tests Done</dt>
                <dd class="col-7">{{ selected.treatment.tests_done || '—' }}</dd>
                <dt class="col-5">Next Visit</dt>
                <dd class="col-7">{{ selected.treatment.next_visit || '—' }}</dd>
                <dt class="col-5">Doctor Notes</dt>
                <dd class="col-7">{{ selected.treatment.doctor_notes || '—' }}</dd>
              </template>
              <template v-else>
                <dt class="col-5 mt-2">Treatment</dt>
                <dd class="col-7 mt-2 text-muted">Not recorded yet</dd>
              </template>
            </dl>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="selected=null">Close</button>
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
  name: 'AdminAppointments',
  data() {
    return {
      appointments: [],
      loading:      true,
      activeStatus: '',
      page:         1,
      totalPages:   1,
      total:        0,
      selected:     null,
      alert:        { msg: '', type: 'success' },
      statusOptions: [
        { value: '',          label: 'All',       active: 'btn-secondary',    outline: 'btn-outline-secondary' },
        { value: 'Booked',    label: 'Booked',    active: 'btn-primary',      outline: 'btn-outline-primary'   },
        { value: 'Completed', label: 'Completed', active: 'btn-success',      outline: 'btn-outline-success'   },
        { value: 'Cancelled', label: 'Cancelled', active: 'btn-danger',       outline: 'btn-outline-danger'    },
      ],
    }
  },
  async mounted() { await this.fetchAppointments() },
  methods: {
    async fetchAppointments() {
      this.loading = true
      try {
        const params = { page: this.page, per_page: 15 }
        if (this.activeStatus) params.status = this.activeStatus
        const { data } = await axios.get(`${API}/admin/appointments`, { params })
        this.appointments = data.appointments
        this.totalPages   = data.pages
        this.total        = data.total
      } catch (e) { console.error(e) }
      finally { this.loading = false }
    },
    setStatus(val) { this.activeStatus = val; this.page = 1; this.fetchAppointments() },
    changePage(p)  { this.page = p; this.fetchAppointments() },
    async viewDetail(a) {
      try {
        const { data } = await axios.get(`${API}/admin/appointments/${a.id}`)
        this.selected = data
      } catch (e) { console.error(e) }
    },
    async cancelAppointment(a) {
      if (!confirm(`Cancel appointment #${a.id}?`)) return
      try {
        await axios.patch(`${API}/admin/appointments/${a.id}/cancel`)
        a.status = 'Cancelled'
        this.showAlert('Appointment cancelled.', 'success')
        if (this.selected?.id === a.id) this.selected.status = 'Cancelled'
      } catch (e) {
        this.showAlert(e.response?.data?.error || 'Failed to cancel.', 'danger')
      }
    },
    statusBadge(s) {
      return {
        Booked:    'badge bg-primary',
        Completed: 'badge bg-success',
        Cancelled: 'badge bg-danger',
      }[s] || 'badge bg-secondary'
    },
    showAlert(msg, type = 'success') {
      this.alert = { msg, type }
      setTimeout(() => { this.alert.msg = '' }, 3000)
    },
  },
}
</script>
