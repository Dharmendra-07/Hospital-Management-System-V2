<template>
  <div>
    <!-- Stat Cards -->
    <div class="row g-3 mb-4">
      <div class="col-sm-6 col-xl-3" v-for="card in statCards" :key="card.label">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-body d-flex align-items-center gap-3">
            <div class="fs-2">{{ card.icon }}</div>
            <div>
              <div class="text-muted small">{{ card.label }}</div>
              <div class="fw-bold fs-4" v-if="!loading">{{ card.value }}</div>
              <div class="placeholder-glow" v-else>
                <span class="placeholder col-4"></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Appointment breakdown -->
    <div class="card border-0 shadow-sm">
      <div class="card-header bg-white fw-semibold border-bottom">
        Appointment Status Breakdown
      </div>
      <div class="card-body">
        <div class="row text-center g-3" v-if="!loading">
          <div class="col-4">
            <div class="p-3 rounded bg-primary bg-opacity-10">
              <div class="fw-bold fs-5 text-primary">{{ stats.appointments_by_status?.booked || 0 }}</div>
              <div class="text-muted small">Booked</div>
            </div>
          </div>
          <div class="col-4">
            <div class="p-3 rounded bg-success bg-opacity-10">
              <div class="fw-bold fs-5 text-success">{{ stats.appointments_by_status?.completed || 0 }}</div>
              <div class="text-muted small">Completed</div>
            </div>
          </div>
          <div class="col-4">
            <div class="p-3 rounded bg-danger bg-opacity-10">
              <div class="fw-bold fs-5 text-danger">{{ stats.appointments_by_status?.cancelled || 0 }}</div>
              <div class="text-muted small">Cancelled</div>
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
  name: 'AdminStats',
  data() {
    return { stats: {}, loading: true }
  },
  computed: {
    statCards() {
      return [
        { label: 'Total Doctors',      icon: '🩺', value: this.stats.total_doctors      || 0 },
        { label: 'Total Patients',     icon: '👤', value: this.stats.total_patients     || 0 },
        { label: 'Total Appointments', icon: '📅', value: this.stats.total_appointments || 0 },
        { label: 'Active Today',       icon: '✅', value: this.stats.appointments_by_status?.booked || 0 },
      ]
    },
  },
  async mounted() {
    try {
      const { data } = await axios.get(`${API}/admin/dashboard`)
      this.stats = data
    } catch (e) {
      console.error(e)
    } finally {
      this.loading = false
    }
  },
}
</script>
