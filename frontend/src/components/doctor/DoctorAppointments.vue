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

    <!-- Shared history component with doctor actions -->
    <AppointmentHistory
      :appointments="appointments"
      :loading="loading"
      role="doctor"
      title=""
      :show-header="false"
      :show-filters="false"
      :show-actions="true"
      @mark-complete="openTreatment"
      @cancel="cancelAppt"
      @add-treatment="openTreatment"
    />

    <!-- Pagination -->
    <div class="d-flex justify-content-between align-items-center mt-3"
         v-if="totalPages > 1">
      <small class="text-muted">Page {{ page }} of {{ totalPages }}</small>
      <div class="d-flex gap-1">
        <button class="btn btn-outline-secondary btn-sm"
                :disabled="page === 1" @click="changePage(page-1)">‹</button>
        <button class="btn btn-outline-secondary btn-sm"
                :disabled="page === totalPages" @click="changePage(page+1)">›</button>
      </div>
    </div>

    <!-- Shared Treatment Modal -->
    <TreatmentModal
      :show="showTreatment"
      :appointment="selectedAppt"
      @close="showTreatment=false"
      @saved="onTreatmentSaved"
    />
  </div>
</template>

<script>
import axios from 'axios'
import AppointmentHistory from '../shared/AppointmentHistory.vue'
import TreatmentModal     from '../shared/TreatmentModal.vue'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'DoctorAppointments',
  components: { AppointmentHistory, TreatmentModal },
  data() {
    return {
      appointments:  [],
      loading:       true,
      page:          1,
      totalPages:    1,
      activeView:    'upcoming',
      activeStatus:  '',
      showTreatment: false,
      selectedAppt:  null,
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
    setView(v)    { this.activeView = v;   this.page = 1; this.fetch() },
    setStatus(s)  { this.activeStatus = s; this.page = 1; this.fetch() },
    changePage(p) { this.page = p; this.fetch() },

    openTreatment(appt) {
      this.selectedAppt  = appt
      this.showTreatment = true
    },

    onTreatmentSaved() {
      this.showTreatment = false
      this.showAlert('Treatment saved. Appointment marked Completed.', 'success')
      this.fetch()
    },

    async cancelAppt(a) {
      if (!confirm(`Cancel appointment #${a.id} for ${a.patient_name}?`)) return
      try {
        await axios.patch(`${API}/appointments/${a.id}/status`, { status: 'Cancelled' })
        this.showAlert('Appointment cancelled.', 'success')
        this.fetch()
      } catch (e) {
        this.showAlert(e.response?.data?.error || 'Cancel failed.', 'danger')
      }
    },

    showAlert(msg, type='success') {
      this.alert = { msg, type }
      setTimeout(() => { this.alert.msg = '' }, 3500)
    },
  },
}
</script>
