<template>
  <div>
    <div class="alert alert-info border-0 shadow-sm mb-4">
      <strong>⚙️ Background Jobs</strong> — Manually trigger scheduled Celery jobs for testing.
      In production these run automatically on schedule.
    </div>

    <div class="row g-3">

      <!-- Daily Reminders -->
      <div class="col-md-6">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-header bg-white fw-semibold border-bottom">
            📧 Daily Appointment Reminders
          </div>
          <div class="card-body">
            <p class="text-muted small mb-3">
              Sends reminder emails to all patients with appointments today.
              Auto-runs every day at <strong>07:00 AM</strong>.
            </p>
            <button class="btn btn-primary btn-sm"
                    @click="triggerJob('reminders')"
                    :disabled="jobs.reminders.running">
              <span v-if="jobs.reminders.running"
                    class="spinner-border spinner-border-sm me-1"></span>
              {{ jobs.reminders.running ? 'Running…' : 'Trigger Now' }}
            </button>
          </div>
          <div class="card-footer bg-white border-top" v-if="jobs.reminders.result">
            <JobResult :result="jobs.reminders.result" />
          </div>
        </div>
      </div>

      <!-- Monthly Reports -->
      <div class="col-md-6">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-header bg-white fw-semibold border-bottom">
            📋 Monthly Doctor Reports
          </div>
          <div class="card-body">
            <p class="text-muted small mb-3">
              Generates and emails HTML activity reports to all active doctors.
              Auto-runs on the <strong>1st of every month</strong> at 06:00 AM.
            </p>
            <button class="btn btn-primary btn-sm"
                    @click="triggerJob('reports')"
                    :disabled="jobs.reports.running">
              <span v-if="jobs.reports.running"
                    class="spinner-border spinner-border-sm me-1"></span>
              {{ jobs.reports.running ? 'Running…' : 'Trigger Now' }}
            </button>
          </div>
          <div class="card-footer bg-white border-top" v-if="jobs.reports.result">
            <JobResult :result="jobs.reports.result" />
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
import axios from 'axios'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

const JobResult = {
  name: 'JobResult',
  props: { result: Object },
  template: `
    <div>
      <div v-if="result.state === 'running'" class="text-muted small d-flex align-items-center gap-2">
        <div class="spinner-border spinner-border-sm text-primary"></div>
        Job running… Task ID: <code>{{ result.task_id }}</code>
      </div>
      <div v-else-if="result.state === 'SUCCESS'" class="text-success small">
        ✅ Done — {{ result.data?.sent ?? '' }} sent, {{ result.data?.failed ?? '' }} failed
        <span v-if="result.data?.completed_at" class="text-muted ms-2">
          at {{ result.data.completed_at }}
        </span>
      </div>
      <div v-else-if="result.state === 'FAILURE'" class="text-danger small">
        ❌ Failed: {{ result.error }}
      </div>
    </div>
  `,
}

export default {
  name: 'AdminJobs',
  components: { JobResult },
  data() {
    return {
      jobs: {
        reminders: { running: false, result: null, taskId: null, timer: null },
        reports:   { running: false, result: null, taskId: null, timer: null },
      },
    }
  },
  beforeUnmount() {
    Object.values(this.jobs).forEach(j => { if (j.timer) clearInterval(j.timer) })
  },
  methods: {
    async triggerJob(type) {
      const job     = this.jobs[type]
      const url     = type === 'reminders'
        ? `${API}/admin/jobs/reminders`
        : `${API}/admin/jobs/reports`

      job.running = true
      job.result  = null

      try {
        const { data } = await axios.post(url)
        job.taskId = data.task_id
        job.result = { state: 'running', task_id: data.task_id }
        job.timer  = setInterval(() => this.pollJob(type), 2500)
      } catch (e) {
        job.running = false
        job.result  = { state: 'FAILURE', error: e.response?.data?.error || 'Trigger failed.' }
      }
    },

    async pollJob(type) {
      const job = this.jobs[type]
      if (!job.taskId) return
      try {
        const { data } = await axios.get(`${API}/admin/jobs/${job.taskId}`)
        if (data.state === 'SUCCESS') {
          clearInterval(job.timer)
          job.running = false
          job.result  = { state: 'SUCCESS', data: data.result }
        } else if (data.state === 'FAILURE') {
          clearInterval(job.timer)
          job.running = false
          job.result  = { state: 'FAILURE', error: data.error }
        }
      } catch (e) { console.error('Poll error', e) }
    },
  },
}
</script>
