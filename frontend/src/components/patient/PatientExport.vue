<template>
  <div class="card border-0 shadow-sm">
    <div class="card-header bg-white fw-semibold border-bottom">
      📥 Export Treatment History
    </div>
    <div class="card-body">

      <!-- Idle state -->
      <div v-if="state === 'idle'">
        <p class="text-muted small mb-3">
          Download your complete treatment history as a CSV file.
          The file will be emailed to <strong>{{ userEmail }}</strong> once ready.
        </p>
        <button class="btn btn-primary" @click="triggerExport" :disabled="loading">
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          {{ loading ? 'Starting…' : '📤 Export as CSV' }}
        </button>
      </div>

      <!-- Progress state -->
      <div v-else-if="state === 'running'" class="py-2">
        <div class="d-flex align-items-center gap-3 mb-3">
          <div class="spinner-border text-primary" style="width:1.5rem;height:1.5rem;"></div>
          <div>
            <div class="fw-semibold small">{{ statusMessage }}</div>
            <div class="text-muted" style="font-size:12px;">
              Task ID: <code>{{ taskId }}</code>
            </div>
          </div>
        </div>
        <div class="progress" style="height:8px;">
          <div class="progress-bar progress-bar-striped progress-bar-animated"
               :style="{ width: progress + '%' }">
          </div>
        </div>
        <div class="text-muted small mt-2">{{ progress }}% complete</div>
      </div>

      <!-- Success state -->
      <div v-else-if="state === 'done'" class="py-2">
        <div class="alert alert-success d-flex align-items-start gap-3 mb-3">
          <div class="fs-4">✅</div>
          <div>
            <div class="fw-semibold">Export complete!</div>
            <div class="small mt-1">
              Your CSV has been sent to <strong>{{ userEmail }}</strong>.
            </div>
            <div class="small text-muted mt-1">
              File: <code>{{ filename }}</code> · {{ rows }} records
            </div>
            <div class="small text-muted">
              Completed at: {{ completedAt }}
            </div>
          </div>
        </div>
        <button class="btn btn-outline-primary btn-sm" @click="reset">
          Export Again
        </button>
      </div>

      <!-- Failed state -->
      <div v-else-if="state === 'failed'" class="py-2">
        <div class="alert alert-danger d-flex align-items-start gap-3 mb-3">
          <div class="fs-4">❌</div>
          <div>
            <div class="fw-semibold">Export failed</div>
            <div class="small mt-1">{{ errorMessage }}</div>
          </div>
        </div>
        <button class="btn btn-outline-danger btn-sm" @click="reset">
          Try Again
        </button>
      </div>

    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { mapGetters } from 'vuex'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'PatientExport',
  data() {
    return {
      state:         'idle',    // idle | running | done | failed
      loading:       false,
      taskId:        null,
      statusMessage: 'Starting export…',
      progress:      0,
      filename:      null,
      rows:          null,
      completedAt:   null,
      errorMessage:  '',
      pollTimer:     null,
    }
  },
  computed: {
    ...mapGetters('auth', ['currentUser']),
    userEmail() { return this.currentUser?.email || 'your registered email' },
  },
  beforeUnmount() {
    this.stopPolling()
  },
  methods: {
    async triggerExport() {
      this.loading = true
      try {
        const { data } = await axios.post(`${API}/patient/export`)
        this.taskId  = data.task_id
        this.state   = 'running'
        this.progress = 5
        this.statusMessage = 'Job queued…'
        this.startPolling()
      } catch (e) {
        this.state        = 'failed'
        this.errorMessage = e.response?.data?.error || 'Failed to start export.'
      } finally {
        this.loading = false
      }
    },

    startPolling() {
      // Poll every 2 seconds
      this.pollTimer = setInterval(this.pollStatus, 2000)
    },

    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },

    async pollStatus() {
      if (!this.taskId) return
      try {
        const { data } = await axios.get(`${API}/patient/export/${this.taskId}`)
        const s = data.state

        if (s === 'PENDING') {
          this.statusMessage = 'Waiting for worker…'
          this.progress      = 5
        } else if (s === 'PROGRESS') {
          this.statusMessage = data.message  || 'Processing…'
          this.progress      = data.progress || 50
        } else if (s === 'SUCCESS') {
          this.stopPolling()
          this.state       = 'done'
          this.progress    = 100
          this.filename    = data.filename
          this.rows        = data.rows
          this.completedAt = data.completed_at
        } else if (s === 'FAILURE') {
          this.stopPolling()
          this.state        = 'failed'
          this.errorMessage = data.error || 'An error occurred during export.'
        }
      } catch (e) {
        console.error('Poll error:', e)
      }
    },

    reset() {
      this.stopPolling()
      this.state         = 'idle'
      this.taskId        = null
      this.progress      = 0
      this.statusMessage = 'Starting export…'
      this.filename      = null
      this.rows          = null
      this.completedAt   = null
      this.errorMessage  = ''
    },
  },
}
</script>
