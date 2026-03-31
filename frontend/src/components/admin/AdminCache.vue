<template>
  <div>
    <div class="alert alert-warning border-0 shadow-sm mb-4">
      <strong>⚡ Redis Cache Monitor</strong> — View live cache stats and
      manually invalidate stale keys when needed.
    </div>

    <!-- Stats cards -->
    <div class="row g-3 mb-4">
      <div class="col-sm-6 col-xl-3" v-for="card in statCards" :key="card.label">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-body text-center py-3">
            <div class="fs-2 mb-1">{{ card.icon }}</div>
            <div class="fw-bold fs-5" :class="card.color">{{ card.value }}</div>
            <div class="text-muted small">{{ card.label }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="row g-3">

      <!-- Key breakdown -->
      <div class="col-lg-6">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-header bg-white fw-semibold border-bottom">
            🗂️ Cached Keys by Group
          </div>
          <div class="card-body p-0">
            <div v-if="loading" class="text-center py-4">
              <div class="spinner-border spinner-border-sm text-primary"></div>
            </div>
            <table v-else class="table table-hover align-middle mb-0">
              <thead class="table-light">
                <tr><th>Group</th><th>Keys</th><th>TTL Policy</th><th></th></tr>
              </thead>
              <tbody>
                <tr v-for="g in keyGroups" :key="g.name">
                  <td class="fw-semibold small">{{ g.name }}</td>
                  <td>
                    <span class="badge bg-primary rounded-pill">
                      {{ stats?.key_counts?.[g.key] ?? '—' }}
                    </span>
                  </td>
                  <td class="text-muted" style="font-size:11px;">{{ g.ttl }}</td>
                  <td>
                    <button class="btn btn-outline-danger btn-sm"
                            @click="invalidate(g.group, g.needsId)"
                            :disabled="invalidating === g.group">
                      <span v-if="invalidating === g.group"
                            class="spinner-border spinner-border-sm"></span>
                      <span v-else>Bust</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TTL policy + controls -->
      <div class="col-lg-6">
        <div class="card border-0 shadow-sm mb-3">
          <div class="card-header bg-white fw-semibold border-bottom">
            ⏱️ TTL Expiry Policy
          </div>
          <div class="card-body p-0">
            <table class="table mb-0" style="font-size:13px;">
              <thead class="table-light">
                <tr><th>Constant</th><th>Duration</th><th>Used For</th></tr>
              </thead>
              <tbody>
                <tr v-for="p in ttlPolicies" :key="p.name">
                  <td><code>{{ p.name }}</code></td>
                  <td class="fw-semibold">{{ p.duration }}</td>
                  <td class="text-muted">{{ p.usedFor }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Danger zone -->
        <div class="card border-danger border-0 shadow-sm">
          <div class="card-header bg-white fw-semibold border-bottom text-danger">
            ⚠️ Danger Zone
          </div>
          <div class="card-body">
            <p class="text-muted small mb-3">
              Flush the entire Redis cache. All data will be re-fetched on the
              next request. Use only in emergencies or after bulk data changes.
            </p>
            <button class="btn btn-danger" @click="flushAll" :disabled="flushing">
              <span v-if="flushing" class="spinner-border spinner-border-sm me-1"></span>
              {{ flushing ? 'Flushing…' : '🗑️ Flush Entire Cache' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Alert -->
    <div v-if="alert.msg"
         :class="`alert alert-${alert.type} alert-dismissible mt-3`">
      {{ alert.msg }}
      <button type="button" class="btn-close" @click="alert.msg=''"></button>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'AdminCache',
  data() {
    return {
      stats:       null,
      loading:     true,
      flushing:    false,
      invalidating: null,
      alert:       { msg: '', type: 'success' },
      keyGroups: [
        { name: 'Admin',        key: 'admin',        group: 'admin',        ttl: '60 s',    needsId: false },
        { name: 'Doctor list',  key: 'doctors_list', group: 'doctor',       ttl: '300 s',   needsId: false },
        { name: 'Patient list', key: 'patient',      group: 'patient',      ttl: '300 s',   needsId: false },
        { name: 'Departments',  key: 'departments',  group: 'departments',  ttl: '86400 s', needsId: false },
        { name: 'Appointments', key: 'appointments', group: 'appointments', ttl: '60 s',    needsId: false },
      ],
      ttlPolicies: [
        { name: 'TTL_SHORT',  duration: '60 s',     usedFor: 'Dashboard, availability, appointment lists' },
        { name: 'TTL_MEDIUM', duration: '5 min',    usedFor: 'Doctor/patient lists, patient history'     },
        { name: 'TTL_LONG',   duration: '30 min',   usedFor: 'Doctor and patient profiles'               },
        { name: 'TTL_DAY',    duration: '24 hr',    usedFor: 'Department catalogue'                      },
      ],
    }
  },
  computed: {
    statCards() {
      return [
        {
          label: 'Redis Connected', icon: '🔴',
          value: this.stats ? (this.stats.redis_connected ? '✅ Yes' : '❌ No') : '…',
          color: this.stats?.redis_connected ? 'text-success' : 'text-danger',
        },
        {
          label: 'Total Keys',  icon: '🗝️',
          value: this.stats?.total_keys ?? '…', color: 'text-primary',
        },
        {
          label: 'Memory Used', icon: '💾',
          value: this.stats?.used_memory_human ?? '…', color: 'text-warning',
        },
        {
          label: 'Peak Memory', icon: '📈',
          value: this.stats?.peak_memory_human ?? '…', color: 'text-secondary',
        },
      ]
    },
  },
  async mounted() { await this.fetchStats() },
  methods: {
    async fetchStats() {
      this.loading = true
      try {
        const { data } = await axios.get(`${API}/admin/cache/stats`)
        this.stats = data
      } catch (e) {
        this.showAlert('Could not connect to Redis.', 'danger')
      } finally { this.loading = false }
    },

    async invalidate(group, needsId) {
      // For list-level busting we pass no id
      this.invalidating = group
      try {
        await axios.post(`${API}/admin/cache/invalidate`, { group })
        this.showAlert(`Cache group '${group}' invalidated.`, 'success')
        await this.fetchStats()
      } catch (e) {
        this.showAlert(e.response?.data?.error || 'Invalidation failed.', 'danger')
      } finally { this.invalidating = null }
    },

    async flushAll() {
      if (!confirm('This will clear the ENTIRE Redis cache. Continue?')) return
      this.flushing = true
      try {
        await axios.post(`${API}/admin/cache/flush`)
        this.showAlert('Entire cache flushed.', 'success')
        await this.fetchStats()
      } catch (e) {
        this.showAlert('Flush failed.', 'danger')
      } finally { this.flushing = false }
    },

    showAlert(msg, type = 'success') {
      this.alert = { msg, type }
      setTimeout(() => { this.alert.msg = '' }, 4000)
    },
  },
}
</script>
