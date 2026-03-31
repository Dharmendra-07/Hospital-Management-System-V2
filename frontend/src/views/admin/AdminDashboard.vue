<template>
  <div class="d-flex" style="min-height:100vh;">

    <!-- ── Sidebar ─────────────────────────── -->
    <nav class="bg-dark text-white d-flex flex-column p-0"
         style="width:230px;min-height:100vh;position:fixed;top:0;left:0;z-index:100;">
      <div class="px-3 py-4 border-bottom border-secondary">
        <div class="fw-bold fs-6">🏥 HMS Admin</div>
        <div class="text-secondary small mt-1">{{ username }}</div>
      </div>
      <ul class="nav flex-column py-3 flex-grow-1">
        <li class="nav-item" v-for="item in navItems" :key="item.view">
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

    <!-- ── Main content ─────────────────────── -->
    <main class="flex-grow-1 bg-light" style="margin-left:230px;min-height:100vh;">
      <div class="container-fluid py-4 px-4">

        <!-- Header bar -->
        <div class="d-flex justify-content-between align-items-center mb-4">
          <h5 class="mb-0 fw-semibold">{{ currentTitle }}</h5>
          <div class="input-group" style="max-width:320px;"
               v-if="activeView === 'doctor' || activeView === 'patient'">
            <input v-model="searchQuery" type="text"
                   class="form-control form-control-sm"
                   :placeholder="`Search ${activeView}s…`"
                   @keyup.enter="runSearch" />
            <button class="btn btn-primary btn-sm" @click="runSearch">Search</button>
            <button class="btn btn-outline-secondary btn-sm" v-if="appliedSearch"
                    @click="clearSearch">✕</button>
          </div>
        </div>

        <!-- Routed sub-views -->
        <AdminStats        v-if="activeView === 'dashboard'" />
        <AdminDoctors      v-else-if="activeView === 'doctor'"
                           :search-query="appliedSearch" />
        <AdminPatients     v-else-if="activeView === 'patient'"
                           :search-query="appliedSearch" />
        <AdminAppointments v-else-if="activeView === 'appointment'" />
        <AdminJobs         v-else-if="activeView === 'jobs'" />
        <AdminCache        v-else-if="activeView === 'cache'" />

      </div>
    </main>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'
import AdminStats        from '../../components/admin/AdminStats.vue'
import AdminDoctors      from '../../components/admin/AdminDoctors.vue'
import AdminPatients     from '../../components/admin/AdminPatients.vue'
import AdminAppointments from '../../components/admin/AdminAppointments.vue'
import AdminJobs         from '../../components/admin/AdminJobs.vue'
import AdminCache        from '../../components/admin/AdminCache.vue'

export default {
  name: 'AdminDashboard',
  components: { AdminStats, AdminDoctors, AdminPatients, AdminAppointments, AdminJobs, AdminCache },
  data() {
    return {
      activeView:    'dashboard',
      searchQuery:   '',
      appliedSearch: '',
      navItems: [
        { view: 'dashboard',   icon: '📊', label: 'Dashboard'    },
        { view: 'doctor',      icon: '🩺', label: 'Doctors'      },
        { view: 'patient',     icon: '👤', label: 'Patients'     },
        { view: 'appointment', icon: '📅', label: 'Appointments' },
        { view: 'jobs',        icon: '⚙️', label: 'Background Jobs'},
        { view: 'cache',       icon: '⚡', label: 'Cache Monitor' },
      ],
    }
  },
  computed: {
    ...mapGetters('auth', ['currentUser']),
    username() { return this.currentUser?.username || 'Admin' },
    currentTitle() {
      const map = {
        dashboard:   'Dashboard Overview',
        doctor:      'Manage Doctors',
        patient:     'Manage Patients',
        appointment: 'All Appointments',
        jobs:        'Background Jobs',
        cache:       'Cache Monitor',
      }
      return map[this.activeView] || ''
    },
  },
  methods: {
    ...mapActions('auth', ['logout']),
    switchView(view) {
      this.activeView    = view
      this.searchQuery   = ''
      this.appliedSearch = ''
    },
    runSearch()  { this.appliedSearch = this.searchQuery.trim() },
    clearSearch() {
      this.searchQuery   = ''
      this.appliedSearch = ''
    },
    async handleLogout() {
      await this.logout()
      this.$router.push('/login')
    },
  },
}
</script>
