<template>
  <AppLayout
    v-model:activeView="activeView"
    :nav-items="navItems"
    :display-name="doctorName"
    role-label="Doctor"
    :title-map="titleMap"
    @logout="handleLogout"
    @update:activeView="onViewChange"
  >
    <DoctorStats        v-if="activeView === 'dashboard'"
                        :data="dashData" :loading="statsLoading" />
    <DoctorAppointments v-else-if="activeView === 'appointments'" />
    <DoctorPatients     v-else-if="activeView === 'patients'" />
    <DoctorAvailability v-else-if="activeView === 'availability'" />
  </AppLayout>
</template>

<script>
import axios from 'axios'
import { mapActions } from 'vuex'
import AppLayout        from '../../components/shared/AppLayout.vue'
import DoctorStats        from '../../components/doctor/DoctorStats.vue'
import DoctorAppointments from '../../components/doctor/DoctorAppointments.vue'
import DoctorPatients     from '../../components/doctor/DoctorPatients.vue'
import DoctorAvailability from '../../components/doctor/DoctorAvailability.vue'

const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'DoctorDashboard',
  components: { AppLayout, DoctorStats, DoctorAppointments, DoctorPatients, DoctorAvailability },
  data() {
    return {
      activeView:     'dashboard',
      dashData:       {},
      statsLoading:   true,
      doctorName:     '',
      navItems: [
        { view: 'dashboard',    icon: '📊', label: 'Dashboard'    },
        { view: 'appointments', icon: '📅', label: 'Appointments' },
        { view: 'patients',     icon: '👤', label: 'My Patients'  },
        { view: 'availability', icon: '🗓️', label: 'Availability' },
      ],
      titleMap: {
        dashboard:    'Dashboard Overview',
        appointments: 'My Appointments',
        patients:     'My Patients',
        availability: 'Manage Availability',
      },
    }
  },
  async mounted() { await this.loadDashboard() },
  methods: {
    ...mapActions('auth', ['logout']),
    async loadDashboard() {
      this.statsLoading = true
      try {
        const { data } = await axios.get(`${API}/doctor/dashboard`)
        this.dashData   = data
        this.doctorName = data.doctor?.full_name || ''
      } catch (e) { console.error(e) }
      finally { this.statsLoading = false }
    },
    onViewChange(view) {
      this.activeView = view
      if (view === 'dashboard') this.loadDashboard()
    },
    async handleLogout() { await this.logout(); this.$router.push('/login') },
  },
}
</script>
