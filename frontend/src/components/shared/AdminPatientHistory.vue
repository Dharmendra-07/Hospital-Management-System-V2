<template>
  <div v-if="show" class="modal d-block" style="background:rgba(0,0,0,.5);">
    <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
      <div class="modal-content">

        <!-- Header -->
        <div class="modal-header">
          <div v-if="data">
            <h5 class="modal-title mb-0">{{ data.patient.full_name }} — Full History</h5>
            <div class="text-muted small d-flex flex-wrap gap-3 mt-1">
              <span>Gender: {{ data.patient.gender || '—' }}</span>
              <span>Blood: {{ data.patient.blood_group || '—' }}</span>
              <span>DOB: {{ data.patient.date_of_birth || '—' }}</span>
              <span>Contact: {{ data.patient.contact_number || '—' }}</span>
              <span>Email: {{ data.patient.email || '—' }}</span>
            </div>
          </div>
          <button type="button" class="btn-close" @click="$emit('close')"></button>
        </div>

        <div class="modal-body">
          <!-- Loading -->
          <div v-if="loading" class="text-center py-5">
            <div class="spinner-border text-primary"></div>
          </div>

          <template v-else-if="data">
            <!-- Summary cards -->
            <div class="row g-3 mb-4">
              <div class="col-3" v-for="card in summaryCards" :key="card.label">
                <div class="card border-0 text-center py-3" :class="card.bg">
                  <div class="fw-bold fs-4" :class="card.text">{{ card.value }}</div>
                  <div class="small" :class="card.text" style="opacity:.75;">{{ card.label }}</div>
                </div>
              </div>
            </div>

            <!-- Full appointment history -->
            <AppointmentHistory
              :appointments="data.all"
              :loading="false"
              role="admin"
              title="All Appointments"
              :show-header="true"
              :show-filters="true"
              :show-actions="false"
            />
          </template>
        </div>

        <div class="modal-footer">
          <button class="btn btn-secondary" @click="$emit('close')">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import AppointmentHistory from './AppointmentHistory.vue'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'AdminPatientHistory',
  components: { AppointmentHistory },
  props: {
    show:      { type: Boolean, default: false },
    patientId: { type: Number,  default: null  },
  },
  emits: ['close'],
  data() {
    return { data: null, loading: false }
  },
  computed: {
    summaryCards() {
      if (!this.data) return []
      const s = this.data.summary
      return [
        { label: 'Total',     value: s.total,     bg: 'bg-secondary bg-opacity-10', text: 'text-secondary' },
        { label: 'Booked',    value: s.booked,    bg: 'bg-primary bg-opacity-10',   text: 'text-primary'   },
        { label: 'Completed', value: s.completed, bg: 'bg-success bg-opacity-10',   text: 'text-success'   },
        { label: 'Cancelled', value: s.cancelled, bg: 'bg-danger bg-opacity-10',    text: 'text-danger'    },
      ]
    },
  },
  watch: {
    async patientId(id) { if (id && this.show) await this.load(id) },
    async show(val)     { if (val && this.patientId) await this.load(this.patientId) },
  },
  methods: {
    async load(id) {
      this.loading = true
      this.data    = null
      try {
        const { data } = await axios.get(`${API}/appointments/history/admin/${id}`)
        this.data = data
      } catch (e) { console.error(e) }
      finally { this.loading = false }
    },
  },
}
</script>
