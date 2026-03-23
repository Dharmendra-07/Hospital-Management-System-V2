<template>
  <div class="d-flex" style="min-height:100vh;">

    <!-- ── Sidebar ──────────────────────────── -->
    <nav class="bg-dark text-white d-flex flex-column"
         style="width:230px;min-height:100vh;position:fixed;top:0;left:0;z-index:100;">
      <div class="px-3 py-4 border-bottom border-secondary">
        <div class="fw-bold">🩺 HMS Doctor</div>
        <div class="text-secondary small mt-1">{{ doctorName }}</div>
        <div class="text-secondary" style="font-size:11px;">{{ specialization }}</div>
      </div>
      <ul class="nav flex-column py-3 flex-grow-1">
        <li v-for="item in navItems" :key="item.view">
          <button
            class="nav-link text-start w-100 btn btn-link text-decoration-none px-3 py-2"
            :class="activeView === item.view
              ? 'text-white fw-semibold bg-secondary rounded mx-2'
              : 'text-secondary'"
            style="font-size:14px;"
            @click="switchView(item.view)"
          >{{ item.icon }} {{ item.label }}</button>
        </li>
      </ul>
      <div class="px-3 py-3 border-top border-secondary">
        <button class="btn btn-outline-danger btn-sm w-100" @click="handleLogout">Logout</button>
      </div>
    </nav>

    <!-- ── Main ─────────────────────────────── -->
    <main class="flex-grow-1 bg-light" style="margin-left:230px;min-height:100vh;">
      <div class="container-fluid py-4 px-4">
        <div class="d-flex justify-content-between align-items-center mb-4">
          <h5 class="mb-0 fw-semibold">{{ currentTitle }}</h5>
          <span class="badge bg-primary px-3 py-2">{{ today }}</span>
        </div>

        <DoctorStats        v-if="activeView === 'dashboard'"
                            :data="dashData" :loading="statsLoading" />
        <DoctorAppointments v-else-if="activeView === 'appointments'" />
        <DoctorPatients     v-else-if="activeView === 'patients'" />
        <DoctorAvailability v-else-if="activeView === 'availability'" />
      </div>
    </main>
  </div>
</template>

<script>
import axios from 'axios'
import { mapGetters, mapActions } from 'vuex'
import DoctorStats        from '../../components/doctor/DoctorStats.vue'
import DoctorAppointments from '../../components/doctor/DoctorAppointments.vue'
import DoctorPatients     from '../../components/doctor/DoctorPatients.vue'
import DoctorAvailability from '../../components/doctor/DoctorAvailability.vue'

const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'DoctorDashboard',
  components: { DoctorStats, DoctorAppointments, DoctorPatients, DoctorAvailability },
  data() {
    return {
      activeView:     'dashboard',
      dashData:       {},
      statsLoading:   true,
      doctorName:     '',
      specialization: '',
      navItems: [
        { view: 'dashboard',    icon: '📊', label: 'Dashboard'    },
        { view: 'appointments', icon: '📅', label: 'Appointments' },
        { view: 'patients',     icon: '👤', label: 'My Patients'  },
        { view: 'availability', icon: '🗓️', label: 'Availability' },
      ],
    }
  },
  computed: {
    ...mapGetters('auth', ['currentUser']),
    today() {
      return new Date().toLocaleDateString('en-IN', {
        weekday: 'long', year: 'numeric', month: 'short', day: 'numeric',
      })
    },
    currentTitle() {
      return {
        dashboard:    'Dashboard Overview',
        appointments: 'My Appointments',
        patients:     'My Patients',
        availability: 'Manage Availability',
      }[this.activeView] || ''
    },
  },
  async mounted() { await this.loadDashboard() },
  methods: {
    ...mapActions('auth', ['logout']),
    async loadDashboard() {
      this.statsLoading = true
      try {
        const { data } = await axios.get(`${API}/doctor/dashboard`)
        this.dashData       = data
        this.doctorName     = data.doctor?.full_name     || ''
        this.specialization = data.doctor?.specialization || ''
      } catch (e) { console.error(e) }
      finally { this.statsLoading = false }
    },
    switchView(view) {
      this.activeView = view
      if (view === 'dashboard') this.loadDashboard()
    },
    async handleLogout() { await this.logout(); this.$router.push('/login') },
  },
}
</script>
