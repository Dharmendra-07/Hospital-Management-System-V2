<template>
  <div>
    <!-- Welcome banner -->
    <div class="card border-0 shadow-sm mb-4 bg-primary text-white">
      <div class="card-body py-4 px-4">
        <h4 class="mb-1">Welcome back, {{ patientName }} 👋</h4>
        <p class="mb-3 opacity-75">Book appointments, check history, and manage your health.</p>
        <button class="btn btn-light text-primary fw-semibold" @click="$emit('go', 'doctors')">
          + Book an Appointment
        </button>
      </div>
    </div>

    <div class="row g-4">
      <!-- Departments -->
      <div class="col-lg-7">
        <div class="card border-0 shadow-sm">
          <div class="card-header bg-white fw-semibold border-bottom">🏥 Departments</div>
          <div class="card-body">
            <div v-if="deptLoading" class="text-center py-3">
              <div class="spinner-border spinner-border-sm text-primary"></div>
            </div>
            <div v-else class="row g-2">
              <div class="col-sm-6" v-for="d in departments" :key="d.id">
                <div class="border rounded p-3 h-100"
                     style="cursor:pointer;transition:border-color .15s;"
                     @click="$emit('go', 'doctors')"
                     @mouseenter="e => e.currentTarget.style.borderColor='#0d6efd'"
                     @mouseleave="e => e.currentTarget.style.borderColor=''">
                  <div class="fw-semibold small">{{ d.name }}</div>
                  <div class="text-muted" style="font-size:12px;">{{ d.description }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Upcoming -->
      <div class="col-lg-5">
        <div class="card border-0 shadow-sm">
          <div class="card-header bg-white fw-semibold border-bottom d-flex justify-content-between">
            <span>📅 Upcoming Appointments</span>
            <button class="btn btn-link btn-sm p-0 text-primary"
                    @click="$emit('go', 'appointments')">View all</button>
          </div>
          <div class="card-body p-0">
            <div v-if="apptLoading" class="text-center py-3">
              <div class="spinner-border spinner-border-sm text-primary"></div>
            </div>
            <div v-else-if="upcoming.length === 0" class="text-center py-4 text-muted small">
              No upcoming appointments.
              <div class="mt-2">
                <button class="btn btn-sm btn-outline-primary"
                        @click="$emit('go', 'doctors')">Book Now</button>
              </div>
            </div>
            <ul v-else class="list-group list-group-flush">
              <li v-for="a in upcoming.slice(0,4)" :key="a.id"
                  class="list-group-item px-3 py-3">
                <div class="d-flex justify-content-between align-items-start">
                  <div>
                    <div class="fw-semibold small">Dr. {{ a.doctor_name }}</div>
                    <div class="text-muted" style="font-size:12px;">
                      {{ a.specialization }}
                    </div>
                    <div class="text-muted" style="font-size:12px;">
                      {{ a.date }} &middot; {{ a.time_slot }}
                    </div>
                  </div>
                  <span class="badge bg-primary">Booked</span>
                </div>
              </li>
            </ul>
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
  name: 'PatientHome',
  props: { patientName: { type: String, default: '' } },
  emits: ['go'],
  data() {
    return {
      departments: [], upcoming: [],
      deptLoading: true, apptLoading: true,
    }
  },
  async mounted() {
    await Promise.all([this.fetchDepts(), this.fetchUpcoming()])
  },
  methods: {
    async fetchDepts() {
      try { const { data } = await axios.get(`${API}/patient/departments`); this.departments = data }
      catch (e) { console.error(e) } finally { this.deptLoading = false }
    },
    async fetchUpcoming() {
      try {
        const { data } = await axios.get(`${API}/patient/appointments`, { params: { view: 'upcoming' } })
        this.upcoming = data
      } catch (e) { console.error(e) } finally { this.apptLoading = false }
    },
  },
}
</script>
