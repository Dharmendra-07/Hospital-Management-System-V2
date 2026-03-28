<template>
  <div>
    <!-- Header row -->
    <div class="d-flex justify-content-between align-items-center mb-3" v-if="showHeader">
      <div>
        <h6 class="mb-0 fw-semibold">{{ title }}</h6>
        <div class="text-muted small" v-if="subtitle">{{ subtitle }}</div>
      </div>
      <div class="d-flex gap-2" v-if="showFilters">
        <select v-model="filterStatus" class="form-select form-select-sm" style="width:140px;">
          <option value="">All Statuses</option>
          <option value="Booked">Booked</option>
          <option value="Completed">Completed</option>
          <option value="Cancelled">Cancelled</option>
        </select>
        <input v-model="filterSearch" type="text"
               class="form-control form-control-sm" style="width:180px;"
               :placeholder="role === 'admin' ? 'Search doctor…' : 'Search…'" />
      </div>
    </div>

    <!-- Summary badges -->
    <div class="d-flex gap-2 mb-3 flex-wrap" v-if="appointments.length > 0">
      <span class="badge bg-secondary rounded-pill">{{ appointments.length }} total</span>
      <span class="badge bg-primary rounded-pill">{{ countBy('Booked') }} booked</span>
      <span class="badge bg-success rounded-pill">{{ countBy('Completed') }} completed</span>
      <span class="badge bg-danger rounded-pill">{{ countBy('Cancelled') }} cancelled</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
      <div class="text-muted small mt-2">Loading history…</div>
    </div>

    <!-- Empty -->
    <div v-else-if="filtered.length === 0"
         class="text-center py-5 text-muted">
      <div class="fs-1 mb-2">📋</div>
      <div>No records found.</div>
    </div>

    <!-- Records -->
    <div v-else>
      <div v-for="(a, idx) in filtered" :key="a.id"
           class="card border-0 shadow-sm mb-3">

        <!-- Card header -->
        <div class="card-header bg-white border-bottom py-2 px-3">
          <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
            <div>
              <!-- Visit number -->
              <span class="badge bg-secondary me-2" style="font-size:11px;">
                Visit #{{ filtered.length - idx }}
              </span>
              <!-- Role-adaptive label -->
              <span class="fw-semibold small" v-if="role === 'patient'">
                Dr. {{ a.doctor_name }}
                <span class="text-muted fw-normal">· {{ a.specialization }}</span>
              </span>
              <span class="fw-semibold small" v-else>
                {{ a.patient_name }}
                <span class="text-muted fw-normal ms-1" v-if="role === 'admin'">
                  → Dr. {{ a.doctor_name }}
                </span>
              </span>
            </div>
            <div class="d-flex align-items-center gap-2 flex-wrap">
              <span class="text-muted small">{{ a.date }} · {{ a.time_slot }}</span>
              <span class="badge bg-light text-dark border small">{{ a.visit_type }}</span>
              <span :class="statusBadge(a.status)">{{ a.status }}</span>
            </div>
          </div>
          <!-- Department tag -->
          <div class="text-muted mt-1" style="font-size:11px;" v-if="a.department">
            🏥 {{ a.department }}
          </div>
        </div>

        <!-- Card body: treatment or placeholder -->
        <div class="card-body px-3 py-3">
          <!-- No treatment yet -->
          <div v-if="!a.treatment"
               class="text-muted small fst-italic d-flex align-items-center gap-2">
            <span>📝</span>
            <span v-if="a.status === 'Booked'">Appointment upcoming — no treatment yet.</span>
            <span v-else-if="a.status === 'Cancelled'">Appointment was cancelled.</span>
            <span v-else>No treatment recorded for this visit.</span>
          </div>

          <!-- Treatment details -->
          <div v-else>
            <div class="row g-3">
              <div class="col-md-6">
                <div class="text-muted fw-semibold mb-1" style="font-size:11px;letter-spacing:.05em;">
                  DIAGNOSIS
                </div>
                <div class="small">{{ a.treatment.diagnosis || '—' }}</div>
              </div>

              <div class="col-md-6">
                <div class="text-muted fw-semibold mb-1" style="font-size:11px;letter-spacing:.05em;">
                  TESTS DONE
                </div>
                <div class="small">{{ a.treatment.tests_done || '—' }}</div>
              </div>

              <div class="col-md-6">
                <div class="text-muted fw-semibold mb-1" style="font-size:11px;letter-spacing:.05em;">
                  PRESCRIPTION
                </div>
                <div class="small">{{ a.treatment.prescription || '—' }}</div>
              </div>

              <div class="col-md-6">
                <div class="text-muted fw-semibold mb-1" style="font-size:11px;letter-spacing:.05em;">
                  NEXT VISIT
                </div>
                <div class="small">{{ a.treatment.next_visit || '—' }}</div>
              </div>

              <!-- Medicines pills -->
              <div class="col-12" v-if="a.treatment.medicines?.length">
                <div class="text-muted fw-semibold mb-2" style="font-size:11px;letter-spacing:.05em;">
                  MEDICINES
                </div>
                <div class="d-flex flex-wrap gap-2">
                  <span v-for="(m, i) in a.treatment.medicines" :key="i"
                        class="badge bg-primary bg-opacity-10 text-primary border border-primary px-2 py-1">
                    {{ m.name }}
                    <span v-if="m.dosage" class="opacity-75 ms-1">{{ m.dosage }}</span>
                  </span>
                </div>
              </div>

              <!-- Doctor notes (hidden from patient if empty) -->
              <div class="col-12"
                   v-if="a.treatment.doctor_notes && (role !== 'patient' || showDoctorNotes)">
                <div class="text-muted fw-semibold mb-1" style="font-size:11px;letter-spacing:.05em;">
                  DOCTOR NOTES
                </div>
                <div class="small fst-italic text-muted">{{ a.treatment.doctor_notes }}</div>
              </div>

              <!-- Timestamps -->
              <div class="col-12 d-flex gap-3" style="font-size:11px;">
                <span class="text-muted">
                  Recorded: {{ a.treatment.created_at || '—' }}
                </span>
                <span class="text-muted" v-if="a.treatment.updated_at !== a.treatment.created_at">
                  Updated: {{ a.treatment.updated_at }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Card footer: slot actions for admin/doctor -->
        <div class="card-footer bg-white border-top py-2 px-3 d-flex gap-2"
             v-if="showActions && a.status === 'Booked'">
          <button class="btn btn-success btn-sm"
                  @click="$emit('mark-complete', a)">
            Mark Complete
          </button>
          <button class="btn btn-outline-danger btn-sm"
                  @click="$emit('cancel', a)">
            Cancel
          </button>
          <button class="btn btn-outline-primary btn-sm"
                  @click="$emit('add-treatment', a)"
                  v-if="role === 'doctor'">
            + Treatment
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AppointmentHistory',
  props: {
    appointments: { type: Array,   default: () => [] },
    loading:      { type: Boolean, default: false    },
    role:         { type: String,  default: 'patient' }, // admin | doctor | patient
    title:        { type: String,  default: 'Appointment History' },
    subtitle:     { type: String,  default: '' },
    showHeader:   { type: Boolean, default: true  },
    showFilters:  { type: Boolean, default: true  },
    showActions:  { type: Boolean, default: false },
    showDoctorNotes: { type: Boolean, default: true },
  },
  emits: ['mark-complete', 'cancel', 'add-treatment'],
  data() {
    return {
      filterStatus: '',
      filterSearch: '',
    }
  },
  computed: {
    filtered() {
      let list = this.appointments
      if (this.filterStatus) {
        list = list.filter(a => a.status === this.filterStatus)
      }
      if (this.filterSearch.trim()) {
        const q = this.filterSearch.toLowerCase()
        list = list.filter(a =>
          a.doctor_name?.toLowerCase().includes(q)  ||
          a.patient_name?.toLowerCase().includes(q) ||
          a.specialization?.toLowerCase().includes(q) ||
          a.department?.toLowerCase().includes(q)
        )
      }
      return list
    },
  },
  methods: {
    countBy(status) {
      return this.appointments.filter(a => a.status === status).length
    },
    statusBadge(s) {
      return {
        Booked:    'badge bg-primary',
        Completed: 'badge bg-success',
        Cancelled: 'badge bg-danger',
      }[s] || 'badge bg-secondary'
    },
  },
}
</script>
