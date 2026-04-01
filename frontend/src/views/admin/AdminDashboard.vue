<template>
  <AppLayout
    v-model:activeView="activeView"
    :nav-items="navItems"
    :display-name="username"
    role-label="Administrator"
    :title-map="titleMap"
    @logout="handleLogout"
  >
    <AdminStats        v-if="activeView === 'dashboard'" />
    <AdminDoctors      v-else-if="activeView === 'doctor'"
                       :search-query="appliedSearch" />
    <AdminPatients     v-else-if="activeView === 'patient'"
                       :search-query="appliedSearch" />
    <AdminAppointments v-else-if="activeView === 'appointment'" />
    <AdminJobs         v-else-if="activeView === 'jobs'" />
    <AdminCache        v-else-if="activeView === 'cache'" />

    <!-- Search slot for doctor/patient views -->
    <template #header-right v-if="activeView === 'doctor' || activeView === 'patient'">
      <div class="input-group" style="max-width:300px;">
        <input v-model="searchQuery" type="text" class="form-control form-control-sm"
               :placeholder="`Search ${activeView}s…`"
               @keyup.enter="appliedSearch = searchQuery" />
        <button class="btn btn-primary btn-sm" @click="appliedSearch = searchQuery">
          Search
        </button>
        <button v-if="appliedSearch" class="btn btn-outline-secondary btn-sm"
                @click="searchQuery = ''; appliedSearch = ''">✕</button>
      </div>
    </template>
  </AppLayout>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'
import AppLayout        from '../../components/shared/AppLayout.vue'
import AdminStats        from '../../components/admin/AdminStats.vue'
import AdminDoctors      from '../../components/admin/AdminDoctors.vue'
import AdminPatients     from '../../components/admin/AdminPatients.vue'
import AdminAppointments from '../../components/admin/AdminAppointments.vue'
import AdminJobs         from '../../components/admin/AdminJobs.vue'
import AdminCache        from '../../components/admin/AdminCache.vue'

export default {
  name: 'AdminDashboard',
  components: {
    AppLayout, AdminStats, AdminDoctors, AdminPatients,
    AdminAppointments, AdminJobs, AdminCache,
  },
  data() {
    return {
      activeView:    'dashboard',
      searchQuery:   '',
      appliedSearch: '',
      navItems: [
        { view: 'dashboard',   icon: '📊', label: 'Dashboard'       },
        { view: 'doctor',      icon: '🩺', label: 'Doctors'         },
        { view: 'patient',     icon: '👤', label: 'Patients'        },
        { view: 'appointment', icon: '📅', label: 'Appointments'    },
        { view: 'jobs',        icon: '⚙️', label: 'Background Jobs' },
        { view: 'cache',       icon: '⚡', label: 'Cache Monitor'   },
      ],
      titleMap: {
        dashboard:   'Dashboard Overview',
        doctor:      'Manage Doctors',
        patient:     'Manage Patients',
        appointment: 'All Appointments',
        jobs:        'Background Jobs',
        cache:       'Cache Monitor',
      },
    }
  },
  computed: {
    ...mapGetters('auth', ['currentUser']),
    username() { return this.currentUser?.username || 'Admin' },
  },
  methods: {
    ...mapActions('auth', ['logout']),
    async handleLogout() { await this.logout(); this.$router.push('/login') },
  },
}
</script>
