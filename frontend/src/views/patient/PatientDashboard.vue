<template>
  <AppLayout
    v-model:activeView="activeView"
    :nav-items="navItems"
    :display-name="patientName"
    role-label="Patient"
    :title-map="titleMap"
    @logout="handleLogout"
  >
    <PatientHome         v-if="activeView === 'home'"
                         :patient-name="patientName"
                         @go="activeView = $event" />
    <PatientDoctors      v-else-if="activeView === 'doctors'"
                         @booked="activeView = 'appointments'" />
    <PatientAppointments v-else-if="activeView === 'appointments'" />
    <PatientHistory      v-else-if="activeView === 'history'" />
    <PatientProfile      v-else-if="activeView === 'profile'"
                         @updated="refreshName" />
    <PatientExport       v-else-if="activeView === 'export'" />
  </AppLayout>
</template>

<script>
import axios from 'axios'
import { mapActions } from 'vuex'
import AppLayout         from '../../components/shared/AppLayout.vue'
import PatientHome         from '../../components/patient/PatientHome.vue'
import PatientDoctors      from '../../components/patient/PatientDoctors.vue'
import PatientAppointments from '../../components/patient/PatientAppointments.vue'
import PatientHistory      from '../../components/patient/PatientHistory.vue'
import PatientProfile      from '../../components/patient/PatientProfile.vue'
import PatientExport       from '../../components/patient/PatientExport.vue'

const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'PatientDashboard',
  components: {
    AppLayout, PatientHome, PatientDoctors, PatientAppointments,
    PatientHistory, PatientProfile, PatientExport,
  },
  data() {
    return {
      activeView:  'home',
      patientName: '',
      navItems: [
        { view: 'home',         icon: '🏠', label: 'Home'         },
        { view: 'doctors',      icon: '🩺', label: 'Find Doctors' },
        { view: 'appointments', icon: '📅', label: 'Appointments' },
        { view: 'history',      icon: '📋', label: 'History'      },
        { view: 'profile',      icon: '👤', label: 'My Profile'   },
        { view: 'export',       icon: '📥', label: 'Export Data'  },
      ],
      titleMap: {
        home:         'Welcome',
        doctors:      'Find Doctors',
        appointments: 'My Appointments',
        history:      'Treatment History',
        profile:      'My Profile',
        export:       'Export Data',
      },
    }
  },
  async mounted() { await this.refreshName() },
  methods: {
    ...mapActions('auth', ['logout']),
    async refreshName() {
      try {
        const { data } = await axios.get(`${API}/patient/profile`)
        this.patientName = data.full_name
      } catch (e) { console.error(e) }
    },
    async handleLogout() { await this.logout(); this.$router.push('/login') },
  },
}
</script>
