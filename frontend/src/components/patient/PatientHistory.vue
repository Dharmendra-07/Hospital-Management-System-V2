<template>
  <div>
    <div class="d-flex gap-2 mb-4">
      <button v-for="tab in tabs" :key="tab.val"
              :class="['btn', activeTab === tab.val ? tab.active : tab.outline]"
              @click="setTab(tab.val)">{{ tab.label }}</button>
    </div>
    <AppointmentHistory
      :appointments="history"
      :loading="loading"
      role="patient"
      :show-header="false"
      :show-filters="true"
      :show-actions="false"
      :show-doctor-notes="true"
    />
  </div>
</template>

<script>
import axios from 'axios'
import AppointmentHistory from '../shared/AppointmentHistory.vue'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'PatientHistory',
  components: { AppointmentHistory },
  data() {
    return {
      history: [], loading: true, activeTab: 'all',
      tabs: [
        { val: 'all',      label: '🗂️ All',      active: 'btn-dark',      outline: 'btn-outline-dark'      },
        { val: 'past',     label: '📋 Past',     active: 'btn-secondary', outline: 'btn-outline-secondary' },
        { val: 'upcoming', label: '📅 Upcoming', active: 'btn-primary',   outline: 'btn-outline-primary'   },
      ],
    }
  },
  async mounted() { await this.fetch() },
  methods: {
    async fetch() {
      this.loading = true
      try {
        const { data } = await axios.get(`${API}/appointments/history/me`,
          { params: { view: this.activeTab } })
        this.history = data
      } catch (e) { console.error(e) }
      finally { this.loading = false }
    },
    setTab(t) { this.activeTab = t; this.fetch() },
  },
}
</script>
