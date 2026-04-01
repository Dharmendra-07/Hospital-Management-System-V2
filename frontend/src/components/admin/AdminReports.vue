<template>
  <div>
    <div class="alert alert-info border-0 shadow-sm mb-4">
      <strong>📋 Report Center</strong> — Download monthly activity reports
      for any doctor as HTML (opens in browser, can be printed to PDF).
    </div>

    <div class="row g-3">
      <!-- Doctor Report Generator -->
      <div class="col-lg-6">
        <div class="hms-card">
          <div class="card-header">🩺 Monthly Doctor Report</div>
          <div class="card-body">
            <div class="mb-3">
              <label class="form-label fw-semibold">Select Doctor</label>
              <select v-model="reportForm.doctor_id" class="form-select">
                <option value="">— Select a doctor —</option>
                <option v-for="d in doctors" :key="d.id" :value="d.id">
                  Dr. {{ d.full_name }} — {{ d.specialization }}
                </option>
              </select>
            </div>
            <div class="row g-2 mb-3">
              <div class="col-6">
                <label class="form-label fw-semibold">Month</label>
                <select v-model="reportForm.month" class="form-select">
                  <option v-for="(m,i) in months" :key="i" :value="i+1">{{ m }}</option>
                </select>
              </div>
              <div class="col-6">
                <label class="form-label fw-semibold">Year</label>
                <select v-model="reportForm.year" class="form-select">
                  <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
                </select>
              </div>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-primary flex-grow-1"
                      @click="downloadDoctorReport('html')"
                      :disabled="!reportForm.doctor_id || downloading">
                <span v-if="downloading" class="spinner-border spinner-border-sm me-1"></span>
                📥 Download HTML
              </button>
              <button class="btn btn-outline-primary"
                      @click="previewDoctorReport"
                      :disabled="!reportForm.doctor_id">
                👁 Preview
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Patient History Report -->
      <div class="col-lg-6">
        <div class="hms-card">
          <div class="card-header">👤 Patient History Report</div>
          <div class="card-body">
            <div class="mb-3">
              <label class="form-label fw-semibold">Select Patient</label>
              <select v-model="patientReportId" class="form-select">
                <option value="">— Select a patient —</option>
                <option v-for="p in patients" :key="p.id" :value="p.id">
                  {{ p.full_name }} — {{ p.email }}
                </option>
              </select>
            </div>
            <p class="text-muted small mb-3">
              Downloads the complete treatment history for the selected patient.
            </p>
            <button class="btn btn-success w-100"
                    @click="downloadPatientReport"
                    :disabled="!patientReportId || patientDownloading">
              <span v-if="patientDownloading"
                    class="spinner-border spinner-border-sm me-1"></span>
              📥 Download Patient Report
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Alert -->
    <div v-if="alert.msg" :class="`alert alert-${alert.type} mt-3`">
      {{ alert.msg }}
    </div>
  </div>
</template>

<script>
import axios from 'axios'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'AdminReports',
  data() {
    const today = new Date()
    const prevMonth = today.getMonth() === 0 ? 12 : today.getMonth()
    const prevYear  = today.getMonth() === 0 ? today.getFullYear() - 1 : today.getFullYear()
    return {
      doctors:    [],
      patients:   [],
      reportForm: { doctor_id: '', month: prevMonth, year: prevYear },
      patientReportId:    '',
      downloading:        false,
      patientDownloading: false,
      alert: { msg: '', type: 'success' },
      months: ['January','February','March','April','May','June',
               'July','August','September','October','November','December'],
      years: Array.from({ length: 5 }, (_, i) => today.getFullYear() - i),
    }
  },
  async mounted() {
    await Promise.all([this.loadDoctors(), this.loadPatients()])
  },
  methods: {
    async loadDoctors() {
      try {
        const { data } = await axios.get(`${API}/admin/doctors`)
        this.doctors = data.filter(d => d.is_active)
      } catch (e) { console.error(e) }
    },
    async loadPatients() {
      try {
        const { data } = await axios.get(`${API}/admin/patients`)
        this.patients = data
      } catch (e) { console.error(e) }
    },

    async downloadDoctorReport(fmt = 'html') {
      if (!this.reportForm.doctor_id) return
      this.downloading = true
      try {
        const resp = await axios.get(
          `${API}/reports/doctor/${this.reportForm.doctor_id}/monthly`,
          {
            params:       { year: this.reportForm.year, month: this.reportForm.month, format: fmt },
            responseType: 'blob',
          }
        )
        const url  = URL.createObjectURL(new Blob([resp.data]))
        const link = document.createElement('a')
        const ext  = fmt === 'pdf' ? 'pdf' : 'html'
        link.href     = url
        link.download = `doctor_report_${this.reportForm.year}_${this.reportForm.month}.${ext}`
        link.click()
        URL.revokeObjectURL(url)
      } catch (e) {
        this.showAlert('Failed to generate report.', 'danger')
      } finally { this.downloading = false }
    },

    async previewDoctorReport() {
      if (!this.reportForm.doctor_id) return
      const url = `${API}/reports/doctor/${this.reportForm.doctor_id}/monthly`
              + `?year=${this.reportForm.year}&month=${this.reportForm.month}`
      window.open(url, '_blank')
    },

    async downloadPatientReport() {
      if (!this.patientReportId) return
      this.patientDownloading = true
      try {
        const resp = await axios.get(
          `${API}/reports/patient/${this.patientReportId}/history`,
          { responseType: 'blob' }
        )
        const url  = URL.createObjectURL(new Blob([resp.data]))
        const link = document.createElement('a')
        link.href     = url
        link.download = `patient_${this.patientReportId}_history.html`
        link.click()
        URL.revokeObjectURL(url)
      } catch (e) {
        this.showAlert('Failed to generate patient report.', 'danger')
      } finally { this.patientDownloading = false }
    },

    showAlert(msg, type = 'success') {
      this.alert = { msg, type }
      setTimeout(() => { this.alert.msg = '' }, 4000)
    },
  },
}
</script>
