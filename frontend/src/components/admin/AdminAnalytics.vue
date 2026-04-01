<template>
  <div>
    <!-- KPI Summary row -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-xl-3" v-for="kpi in kpis" :key="kpi.label">
        <div class="hms-stat-card">
          <div class="hms-stat-icon" :style="`background:${kpi.bg}`">
            {{ kpi.icon }}
          </div>
          <div>
            <div class="hms-stat-value">
              <span v-if="summaryLoading" class="skeleton d-inline-block"
                    style="width:50px;height:28px;"></span>
              <span v-else>{{ kpi.value }}</span>
            </div>
            <div class="hms-stat-label">{{ kpi.label }}</div>
            <div v-if="kpi.growth !== undefined" class="mt-1" style="font-size:11px;">
              <span :class="kpi.growth >= 0 ? 'text-success' : 'text-danger'">
                {{ kpi.growth >= 0 ? '▲' : '▼' }} {{ Math.abs(kpi.growth) }}%
              </span>
              <span class="text-muted ms-1">vs last month</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Row 1: Trend + Doughnut -->
    <div class="row g-3 mb-3">
      <div class="col-lg-8">
        <div class="hms-card h-100">
          <div class="card-header d-flex justify-content-between align-items-center">
            <span>📈 Appointment Trends (12 Months)</span>
            <button class="btn btn-outline-secondary btn-sm"
                    @click="downloadChart('trendChart', 'appointment_trends')">
              ⬇ PNG
            </button>
          </div>
          <div class="card-body">
            <canvas ref="trendChart" height="100"></canvas>
          </div>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="hms-card h-100">
          <div class="card-header">🍩 Status Breakdown</div>
          <div class="card-body d-flex align-items-center justify-content-center">
            <canvas ref="doughnutChart" style="max-height:220px;"></canvas>
          </div>
        </div>
      </div>
    </div>

    <!-- Row 2: Specialization + Department -->
    <div class="row g-3 mb-3">
      <div class="col-lg-6">
        <div class="hms-card h-100">
          <div class="card-header">🩺 Specialization Demand</div>
          <div class="card-body">
            <canvas ref="specChart" height="120"></canvas>
          </div>
        </div>
      </div>
      <div class="col-lg-6">
        <div class="hms-card h-100">
          <div class="card-header">🏥 Department Load</div>
          <div class="card-body">
            <canvas ref="deptChart" height="120"></canvas>
          </div>
        </div>
      </div>
    </div>

    <!-- Row 3: Top Doctors + Daily -->
    <div class="row g-3">
      <div class="col-lg-5">
        <div class="hms-card h-100">
          <div class="card-header">🥇 Top Doctors (Completed)</div>
          <div class="card-body">
            <canvas ref="topDoctorsChart" height="140"></canvas>
          </div>
        </div>
      </div>
      <div class="col-lg-7">
        <div class="hms-card h-100">
          <div class="card-header">📅 Daily Appointments — This Month</div>
          <div class="card-body">
            <canvas ref="dailyChart" height="100"></canvas>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

// Chart.js is loaded from CDN in index.html
// We access it via window.Chart

const CHART_DEFAULTS = {
  responsive:          true,
  maintainAspectRatio: true,
  plugins: {
    legend: { labels: { font: { family: 'Inter, sans-serif', size: 12 } } },
    tooltip: { titleFont: { family: 'Inter' }, bodyFont: { family: 'Inter' } },
  },
  scales: {
    x: { ticks: { font: { family: 'Inter', size: 11 } }, grid: { display: false } },
    y: { ticks: { font: { family: 'Inter', size: 11 } }, grid: { color: '#f0f0f0' } },
  },
}

export default {
  name: 'AdminAnalytics',
  data() {
    return {
      summary:       {},
      summaryLoading: true,
      charts:        {},
    }
  },
  computed: {
    kpis() {
      const s = this.summary
      return [
        { label: 'Total Appointments', icon: '📅', value: s.total_appointments ?? '…',
          bg: 'rgba(13,110,253,.12)', growth: s.growth_pct },
        { label: 'This Month',         icon: '📆', value: s.this_month ?? '…',
          bg: 'rgba(25,135,84,.12)'  },
        { label: 'Active Doctors',     icon: '🩺', value: s.total_doctors ?? '…',
          bg: 'rgba(220,53,69,.10)'  },
        { label: 'Active Patients',    icon: '👤', value: s.total_patients ?? '…',
          bg: 'rgba(255,193,7,.12)'  },
      ]
    },
  },
  async mounted() {
    // Load Chart.js from CDN if not present
    if (!window.Chart) {
      await this.loadChartJS()
    }
    await Promise.all([
      this.loadSummary(),
      this.loadTrend(),
      this.loadDoughnut(),
      this.loadSpec(),
      this.loadDept(),
      this.loadTopDoctors(),
      this.loadDaily(),
    ])
  },
  beforeUnmount() {
    Object.values(this.charts).forEach(c => c?.destroy())
  },
  methods: {
    loadChartJS() {
      return new Promise((resolve, reject) => {
        const s = document.createElement('script')
        s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'
        s.onload  = resolve
        s.onerror = reject
        document.head.appendChild(s)
      })
    },

    makeChart(ref, type, data, extraOptions = {}) {
      if (this.charts[ref]) this.charts[ref].destroy()
      const ctx = this.$refs[ref]
      if (!ctx || !window.Chart) return
      this.charts[ref] = new window.Chart(ctx, {
        type,
        data,
        options: { ...CHART_DEFAULTS, ...extraOptions },
      })
    },

    async loadSummary() {
      try {
        const { data } = await axios.get(`${API}/analytics/summary`)
        this.summary = data
      } catch (e) { console.error(e) }
      finally { this.summaryLoading = false }
    },

    async loadTrend() {
      try {
        const { data } = await axios.get(`${API}/analytics/appointments-trend`)
        this.makeChart('trendChart', 'line', data)
      } catch (e) { console.error(e) }
    },

    async loadDoughnut() {
      try {
        const { data } = await axios.get(`${API}/analytics/status-breakdown`)
        this.makeChart('doughnutChart', 'doughnut', data, {
          scales: {},
          plugins: {
            legend: { position: 'bottom',
                      labels: { font: { family: 'Inter', size: 12 }, padding: 16 } },
          },
          cutout: '65%',
        })
      } catch (e) { console.error(e) }
    },

    async loadSpec() {
      try {
        const { data } = await axios.get(`${API}/analytics/specialization-demand`)
        this.makeChart('specChart', 'bar', data, {
          indexAxis: 'x',
          plugins: { legend: { display: false } },
        })
      } catch (e) { console.error(e) }
    },

    async loadDept() {
      try {
        const { data } = await axios.get(`${API}/analytics/department-load`)
        this.makeChart('deptChart', 'bar', data, {
          plugins: { legend: { display: false } },
        })
      } catch (e) { console.error(e) }
    },

    async loadTopDoctors() {
      try {
        const { data } = await axios.get(`${API}/analytics/top-doctors`)
        this.makeChart('topDoctorsChart', 'bar', data, {
          indexAxis: 'y',
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { font: { family: 'Inter', size: 11 } }, grid: { color: '#f0f0f0' } },
            y: { ticks: { font: { family: 'Inter', size: 11 } }, grid: { display: false } },
          },
        })
      } catch (e) { console.error(e) }
    },

    async loadDaily() {
      try {
        const { data } = await axios.get(`${API}/analytics/daily-appointments`)
        this.makeChart('dailyChart', 'line', data)
      } catch (e) { console.error(e) }
    },

    downloadChart(ref, filename) {
      const chart = this.charts[ref]
      if (!chart) return
      const url  = chart.toBase64Image()
      const link = document.createElement('a')
      link.download = `${filename}.png`
      link.href     = url
      link.click()
    },
  },
}
</script>
