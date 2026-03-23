<template>
  <div>
    <!-- Stat cards -->
    <div class="row g-3 mb-4">
      <div class="col-sm-4" v-for="card in cards" :key="card.label">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-body d-flex align-items-center gap-3">
            <div class="fs-2">{{ card.icon }}</div>
            <div>
              <div class="text-muted small">{{ card.label }}</div>
              <div v-if="!loading" class="fw-bold fs-4">{{ card.value }}</div>
              <div v-else class="placeholder-glow"><span class="placeholder col-4"></span></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Today's appointments -->
    <div class="card border-0 shadow-sm mb-4">
      <div class="card-header bg-white fw-semibold border-bottom d-flex justify-content-between">
        <span>📅 Today's Appointments</span>
        <span class="badge bg-primary rounded-pill">{{ todayList.length }}</span>
      </div>
      <div class="card-body p-0">
        <div v-if="loading" class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-primary"></div>
        </div>
        <div v-else-if="todayList.length === 0"
             class="text-center py-4 text-muted small">No appointments today.</div>
        <div class="table-responsive" v-else>
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>#</th><th>Patient</th><th>Time Slot</th><th>Type</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in todayList" :key="a.id">
                <td class="text-muted small">{{ a.id }}</td>
                <td class="fw-semibold">{{ a.patient_name }}</td>
                <td><span class="badge bg-secondary">{{ a.time_slot }}</span></td>
                <td>{{ a.visit_type }}</td>
                <td>
                  <div class="d-flex gap-1">
                    <button class="btn btn-success btn-sm"
                            @click="$emit('action', { type:'complete', appt: a })">
                      Mark Complete
                    </button>
                    <button class="btn btn-outline-danger btn-sm"
                            @click="$emit('action', { type:'cancel', appt: a })">
                      Cancel
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- This week -->
    <div class="card border-0 shadow-sm">
      <div class="card-header bg-white fw-semibold border-bottom d-flex justify-content-between">
        <span>📆 This Week's Upcoming</span>
        <span class="badge bg-info rounded-pill">{{ weekList.length }}</span>
      </div>
      <div class="card-body p-0">
        <div v-if="loading" class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-primary"></div>
        </div>
        <div v-else-if="weekList.length === 0"
             class="text-center py-4 text-muted small">No upcoming appointments this week.</div>
        <div class="table-responsive" v-else>
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr><th>#</th><th>Patient</th><th>Date</th><th>Time Slot</th><th>Type</th></tr>
            </thead>
            <tbody>
              <tr v-for="a in weekList" :key="a.id">
                <td class="text-muted small">{{ a.id }}</td>
                <td class="fw-semibold">{{ a.patient_name }}</td>
                <td>{{ a.date }}</td>
                <td><span class="badge bg-secondary">{{ a.time_slot }}</span></td>
                <td>{{ a.visit_type }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DoctorStats',
  props: {
    data:    { type: Object, default: () => ({}) },
    loading: { type: Boolean, default: true },
  },
  computed: {
    todayList() { return this.data.today_appointments || [] },
    weekList()  { return this.data.week_appointments  || [] },
    cards() {
      const s = this.data.stats || {}
      return [
        { label: "Today's Appointments", icon: '📅', value: s.today_count    || 0 },
        { label: "This Week's Bookings", icon: '📆', value: s.week_count     || 0 },
        { label: 'Total Patients',        icon: '👤', value: s.total_patients || 0 },
      ]
    },
  },
}
</script>
