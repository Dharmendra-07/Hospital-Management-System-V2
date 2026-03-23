<template>
  <div>
    <!-- Tab toggle -->
    <div class="d-flex gap-2 mb-4">
      <button v-for="tab in tabs" :key="tab.val"
              :class="['btn', activeTab === tab.val ? tab.active : tab.outline]"
              @click="setTab(tab.val)">
        {{ tab.label }}
      </button>
    </div>

    <div v-if="alert.msg" :class="`alert alert-${alert.type} alert-dismissible`">
      {{ alert.msg }}
      <button type="button" class="btn-close" @click="alert.msg=''"></button>
    </div>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>
    <div v-else-if="appointments.length === 0"
         class="text-center py-5 text-muted">
      No {{ activeTab }} appointments found.
    </div>

    <div v-else class="row g-3">
      <div class="col-md-6" v-for="a in appointments" :key="a.id">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <div>
                <div class="fw-semibold">Dr. {{ a.doctor_name }}</div>
                <div class="text-muted small">{{ a.specialization }}</div>
              </div>
              <span :class="statusBadge(a.status)">{{ a.status }}</span>
            </div>
            <div class="text-muted small mb-1">📅 {{ a.date }} &middot; {{ a.time_slot }}</div>
            <div class="text-muted small mb-1">🏥 {{ a.department || '—' }}</div>
            <div class="text-muted small">🩺 {{ a.visit_type }}</div>
            <div v-if="a.notes" class="text-muted small mt-1 fst-italic">
              "{{ a.notes }}"
            </div>
          </div>
          <div v-if="a.status === 'Booked'" class="card-footer bg-white border-top d-flex gap-2">
            <button class="btn btn-outline-warning btn-sm flex-grow-1"
                    @click="openReschedule(a)">Reschedule</button>
            <button class="btn btn-outline-danger btn-sm flex-grow-1"
                    @click="cancelAppt(a)">Cancel</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Reschedule Modal ───────────────────── -->
    <div v-if="showReschedule" class="modal d-block" style="background:rgba(0,0,0,.5);">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <div>
              <h5 class="modal-title">Reschedule Appointment</h5>
              <div class="text-muted small">Dr. {{ reschedAppt?.doctor_name }}</div>
            </div>
            <button type="button" class="btn-close" @click="showReschedule=false"></button>
          </div>
          <div class="modal-body">
            <div class="alert alert-info small mb-3">
              Current: <strong>{{ reschedAppt?.date }}</strong> at
              <strong>{{ reschedAppt?.time_slot }}</strong>
            </div>
            <div class="mb-3">
              <label class="form-label fw-semibold">New Date</label>
              <select v-model="reschedForm.date" class="form-select" @change="reschedForm.time_slot=''">
                <option value="">-- Choose date --</option>
                <option v-for="day in reschedDays" :key="day.date"
                        :value="day.date"
                        :disabled="day.freeSlots.length === 0">
                  {{ day.date }} ({{ day.freeSlots.length }} slot{{ day.freeSlots.length !== 1 ? 's' : '' }})
                </option>
              </select>
            </div>
            <div class="mb-3" v-if="reschedForm.date">
              <label class="form-label fw-semibold">New Time Slot</label>
              <div class="d-flex flex-wrap gap-2">
                <button v-for="s in reschedSlotsForDate" :key="s"
                        :class="['btn btn-sm', reschedForm.time_slot === s
                          ? 'btn-primary' : 'btn-outline-primary']"
                        @click="reschedForm.time_slot = s">
                  {{ s }}
                </button>
              </div>
            </div>
            <div v-if="reschedError" class="alert alert-danger mb-0">{{ reschedError }}</div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showReschedule=false">Cancel</button>
            <button class="btn btn-warning" @click="confirmReschedule" :disabled="rescheduling">
              <span v-if="rescheduling" class="spinner-border spinner-border-sm me-1"></span>
              Confirm Reschedule
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
  name: 'PatientAppointments',
  data() {
    return {
      appointments:   [],
      loading:        true,
      activeTab:      'upcoming',
      alert:          { msg: '', type: 'success' },
      showReschedule: false,
      reschedAppt:    null,
      reschedDays:    [],
      reschedForm:    { date: '', time_slot: '' },
      reschedError:   '',
      rescheduling:   false,
      tabs: [
        { val: 'upcoming', label: '📅 Upcoming', active: 'btn-primary',   outline: 'btn-outline-primary'   },
        { val: 'past',     label: '📋 Past',     active: 'btn-secondary', outline: 'btn-outline-secondary' },
        { val: 'all',      label: '🗂️ All',      active: 'btn-dark',      outline: 'btn-outline-dark'      },
      ],
    }
  },
  computed: {
    reschedSlotsForDate() {
      if (!this.reschedForm.date) return []
      const day = this.reschedDays.find(d => d.date === this.reschedForm.date)
      return day ? day.freeSlots : []
    },
  },
  async mounted() { await this.fetch() },
  methods: {
    async fetch() {
      this.loading = true
      try {
        const { data } = await axios.get(`${API}/patient/appointments`,
          { params: { view: this.activeTab } })
        this.appointments = data
      } catch (e) { console.error(e) }
      finally { this.loading = false }
    },
    setTab(t) { this.activeTab = t; this.fetch() },

    async cancelAppt(a) {
      if (!confirm(`Cancel appointment with Dr. ${a.doctor_name} on ${a.date}?`)) return
      try {
        await axios.delete(`${API}/patient/appointments/${a.id}`)
        this.showAlert('Appointment cancelled.', 'success')
        await this.fetch()
      } catch (e) {
        this.showAlert(e.response?.data?.error || 'Failed to cancel.', 'danger')
      }
    },

    async openReschedule(a) {
      this.reschedAppt  = a
      this.reschedForm  = { date: '', time_slot: '' }
      this.reschedError = ''
      try {
        const { data } = await axios.get(`${API}/patient/doctors/${a.doctor_id}`)
        this.reschedDays = data.availability.map(day => ({
          date:      day.date,
          freeSlots: day.slots.filter(s => !s.is_booked).map(s => s.slot),
        }))
      } catch (e) { console.error(e) }
      this.showReschedule = true
    },

    async confirmReschedule() {
      this.reschedError = ''
      if (!this.reschedForm.date)      { this.reschedError = 'Please select a date.';      return }
      if (!this.reschedForm.time_slot) { this.reschedError = 'Please select a time slot.'; return }
      this.rescheduling = true
      try {
        await axios.put(`${API}/patient/appointments/${this.reschedAppt.id}/reschedule`,
          this.reschedForm)
        this.showReschedule = false
        this.showAlert('Appointment rescheduled successfully.', 'success')
        await this.fetch()
      } catch (e) {
        this.reschedError = e.response?.data?.error || 'Reschedule failed.'
      } finally { this.rescheduling = false }
    },

    statusBadge(s) {
      return { Booked: 'badge bg-primary', Completed: 'badge bg-success',
               Cancelled: 'badge bg-danger' }[s] || 'badge bg-secondary'
    },
    showAlert(msg, type='success') {
      this.alert = { msg, type }
      setTimeout(() => { this.alert.msg = '' }, 3500)
    },
  },
}
</script>
