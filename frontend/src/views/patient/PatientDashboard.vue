<template>
  <div class="d-flex" style="min-height:100vh;">

    <!-- ── Sidebar ──────────────────────────── -->
    <nav class="bg-dark text-white d-flex flex-column"
         style="width:230px;min-height:100vh;position:fixed;top:0;left:0;z-index:100;">
      <div class="px-3 py-4 border-bottom border-secondary">
        <div class="fw-bold">🏥 HMS Patient</div>
        <div class="text-secondary small mt-1">{{ patientName }}</div>
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

    <!-- ── Main Content ──────────────────────── -->
    <main class="flex-grow-1 bg-light" style="margin-left:230px;min-height:100vh;">
      <div class="container-fluid py-4 px-4">
        <div class="d-flex justify-content-between align-items-center mb-4">
          <h5 class="mb-0 fw-semibold">{{ currentTitle }}</h5>
          <span class="badge bg-success px-3 py-2">{{ today }}</span>
        </div>

        <PatientHome         v-if="activeView === 'home'"
                             :patient-name="patientName"
                             @go="switchView" />
        <PatientDoctors      v-else-if="activeView === 'doctors'"
                             @booked="switchView('appointments')" />
        <PatientAppointments v-else-if="activeView === 'appointments'" />
        <PatientHistory      v-else-if="activeView === 'history'" />
        <PatientProfile      v-else-if="activeView === 'profile'"
                             @updated="refreshName" />
      </div>
    </main>
  </div>
</template>

<script>
import axios from 'axios'
import { mapGetters, mapActions } from 'vuex'
import PatientHome         from '../../components/patient/PatientHome.vue'
import PatientDoctors      from '../../components/patient/PatientDoctors.vue'
import PatientAppointments from '../../components/patient/PatientAppointments.vue'
import PatientHistory      from '../../components/patient/PatientHistory.vue'
import PatientProfile      from '../../components/patient/PatientProfile.vue'
import PatientExport       from '../../components/patient/PatientExport.vue'

const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'PatientDashboard',
  components: { PatientHome, PatientDoctors, PatientAppointments, PatientHistory, PatientProfile, PatientExport },
  data() {
    return {
      activeView:  'home',
      patientName: '',
      navItems: [
        { view: 'home',         icon: '🏠', label: 'Home'          },
        { view: 'doctors',      icon: '🩺', label: 'Find Doctors'  },
        { view: 'appointments', icon: '📅', label: 'Appointments'  },
        { view: 'history',      icon: '📋', label: 'History'       },
        { view: 'profile',      icon: '👤', label: 'My Profile'    },
        { view: 'export',       icon: '📥', label: 'Export Data'   },
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
        home: 'Dashboard', doctors: 'Find Doctors',
        appointments: 'My Appointments', history: 'Treatment History',
        profile: 'My Profile',
      }[this.activeView] || ''
    },
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
    switchView(view) { this.activeView = view },
    async handleLogout() { await this.logout(); this.$router.push('/login') },
  },
}
</script>
