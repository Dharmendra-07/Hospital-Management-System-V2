<template>
  <div>
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>
    <div v-else-if="history.length === 0"
         class="text-center py-5 text-muted">
      No treatment history found yet.
    </div>
    <div v-else>
      <p class="text-muted small mb-3">{{ history.length }} visit{{ history.length !== 1 ? 's' : '' }} recorded</p>
      <div v-for="(a, idx) in history" :key="a.id" class="card border-0 shadow-sm mb-3">
        <div class="card-header bg-white d-flex justify-content-between align-items-center py-2">
          <div>
            <span class="fw-semibold">Visit {{ history.length - idx }}</span>
            <span class="text-muted ms-2 small">
              Dr. {{ a.doctor_name }} &middot; {{ a.date }} &middot; {{ a.time_slot }}
            </span>
          </div>
          <div class="d-flex align-items-center gap-2">
            <span class="text-muted small">{{ a.visit_type }}</span>
            <span :class="statusBadge(a.status)">{{ a.status }}</span>
          </div>
        </div>
        <div class="card-body">
          <div v-if="!a.treatment" class="text-muted small fst-italic">
            No treatment recorded for this visit.
          </div>
          <div v-else class="row g-3">
            <div class="col-md-6">
              <div class="text-muted small fw-semibold mb-1">DIAGNOSIS</div>
              <div>{{ a.treatment.diagnosis || '—' }}</div>
            </div>
            <div class="col-md-6">
              <div class="text-muted small fw-semibold mb-1">TESTS DONE</div>
              <div>{{ a.treatment.tests_done || '—' }}</div>
            </div>
            <div class="col-md-6">
              <div class="text-muted small fw-semibold mb-1">PRESCRIPTION</div>
              <div>{{ a.treatment.prescription || '—' }}</div>
            </div>
            <div class="col-md-6">
              <div class="text-muted small fw-semibold mb-1">NEXT VISIT</div>
              <div>{{ a.treatment.next_visit || '—' }}</div>
            </div>
            <div class="col-12" v-if="a.treatment.medicines?.length">
              <div class="text-muted small fw-semibold mb-2">MEDICINES</div>
              <div class="d-flex flex-wrap gap-2">
                <span v-for="(m, i) in a.treatment.medicines" :key="i"
                      class="badge bg-primary bg-opacity-10 text-primary border border-primary px-2 py-1">
                  {{ m.name }}
                  <span v-if="m.dosage" class="text-muted ms-1">{{ m.dosage }}</span>
                </span>
              </div>
            </div>
            <div class="col-12" v-if="a.treatment.doctor_notes">
              <div class="text-muted small fw-semibold mb-1">DOCTOR NOTES</div>
              <div class="fst-italic text-muted">{{ a.treatment.doctor_notes }}</div>
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
  name: 'PatientHistory',
  data() {
    return { history: [], loading: true }
  },
  async mounted() {
    try {
      const { data } = await axios.get(`${API}/patient/appointments`, { params: { view: 'past' } })
      this.history = data
    } catch (e) { console.error(e) }
    finally { this.loading = false }
  },
  methods: {
    statusBadge(s) {
      return { Booked: 'badge bg-primary', Completed: 'badge bg-success',
               Cancelled: 'badge bg-danger' }[s] || 'badge bg-secondary'
    },
  },
}
</script>
