<template>
  <div>
    <!-- Search bar -->
    <div class="input-group mb-3" style="max-width:340px;">
      <input v-model="search" type="text" class="form-control"
             placeholder="Search patients…" />
      <button class="btn btn-outline-secondary" @click="search=''">✕</button>
    </div>

    <div class="card border-0 shadow-sm">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>#</th><th>Name</th><th>Gender</th>
              <th>Blood Group</th><th>Contact</th>
              <th>Last Visit</th><th>Total Visits</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8" class="text-center py-4">
                <div class="spinner-border spinner-border-sm text-primary"></div>
              </td>
            </tr>
            <tr v-else-if="filtered.length === 0">
              <td colspan="8" class="text-center py-4 text-muted">No patients found.</td>
            </tr>
            <tr v-else v-for="p in filtered" :key="p.id">
              <td class="text-muted small">{{ p.id }}</td>
              <td class="fw-semibold">{{ p.full_name }}</td>
              <td>{{ p.gender || '—' }}</td>
              <td>{{ p.blood_group || '—' }}</td>
              <td>{{ p.contact_number || '—' }}</td>
              <td>{{ p.last_visit || '—' }}</td>
              <td>
                <span class="badge bg-secondary">{{ p.total_visits }}</span>
              </td>
              <td>
                <button class="btn btn-outline-primary btn-sm"
                        @click="viewHistory(p)">View History</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Patient History Modal ────────────── -->
    <div v-if="showHistory" class="modal d-block" style="background:rgba(0,0,0,.5);">
      <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <div>
              <h5 class="modal-title mb-0">{{ historyData?.patient?.full_name }}</h5>
              <div class="text-muted small d-flex gap-3">
                <span>Gender: {{ historyData?.patient?.gender || '—' }}</span>
                <span>Blood: {{ historyData?.patient?.blood_group || '—' }}</span>
                <span>DOB: {{ historyData?.patient?.date_of_birth || '—' }}</span>
              </div>
            </div>
            <button type="button" class="btn-close" @click="showHistory=false"></button>
          </div>
          <div class="modal-body">
            <div v-if="historyLoading" class="text-center py-4">
              <div class="spinner-border text-primary"></div>
            </div>
            <div v-else-if="!historyData?.history?.length"
                 class="text-center py-4 text-muted">No visit history found.</div>
            <div v-else>
              <div v-for="(entry, idx) in historyData.history" :key="entry.appointment_id"
                   class="card border mb-3">
                <div class="card-header d-flex justify-content-between align-items-center py-2">
                  <div>
                    <span class="fw-semibold">Visit {{ historyData.history.length - idx }}</span>
                    <span class="text-muted ms-2 small">
                      {{ entry.date }} · {{ entry.time_slot }} · {{ entry.visit_type }}
                    </span>
                  </div>
                  <span :class="statusBadge(entry.status)">{{ entry.status }}</span>
                </div>
                <div class="card-body">
                  <div v-if="!entry.treatment" class="text-muted small fst-italic">
                    No treatment recorded for this visit.
                  </div>
                  <div v-else class="row g-3">
                    <div class="col-md-6">
                      <div class="fw-semibold text-muted small mb-1">DIAGNOSIS</div>
                      <div>{{ entry.treatment.diagnosis || '—' }}</div>
                    </div>
                    <div class="col-md-6">
                      <div class="fw-semibold text-muted small mb-1">TESTS DONE</div>
                      <div>{{ entry.treatment.tests_done || '—' }}</div>
                    </div>
                    <div class="col-md-6">
                      <div class="fw-semibold text-muted small mb-1">PRESCRIPTION</div>
                      <div>{{ entry.treatment.prescription || '—' }}</div>
                    </div>
                    <div class="col-md-6">
                      <div class="fw-semibold text-muted small mb-1">NEXT VISIT</div>
                      <div>{{ entry.treatment.next_visit || '—' }}</div>
                    </div>
                    <div class="col-12" v-if="entry.treatment.medicines?.length">
                      <div class="fw-semibold text-muted small mb-2">MEDICINES</div>
                      <div class="d-flex flex-wrap gap-2">
                        <span v-for="(m, i) in entry.treatment.medicines" :key="i"
                              class="badge bg-primary bg-opacity-10 text-primary border border-primary px-2 py-1">
                          {{ m.name }}
                          <span class="text-muted ms-1">{{ m.dosage }}</span>
                        </span>
                      </div>
                    </div>
                    <div class="col-12" v-if="entry.treatment.doctor_notes">
                      <div class="fw-semibold text-muted small mb-1">DOCTOR NOTES</div>
                      <div class="fst-italic text-muted">{{ entry.treatment.doctor_notes }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showHistory=false">Close</button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import axios from 'axios'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'DoctorPatients',
  data() {
    return {
      patients:      [],
      loading:       true,
      search:        '',
      showHistory:   false,
      historyData:   null,
      historyLoading: false,
    }
  },
  computed: {
    filtered() {
      const q = this.search.toLowerCase()
      if (!q) return this.patients
      return this.patients.filter(p =>
        p.full_name.toLowerCase().includes(q) ||
        (p.contact_number || '').includes(q)
      )
    },
  },
  async mounted() {
    try {
      const { data } = await axios.get(`${API}/doctor/patients`)
      this.patients = data
    } catch (e) { console.error(e) }
    finally { this.loading = false }
  },
  methods: {
    async viewHistory(patient) {
      this.showHistory   = true
      this.historyData   = null
      this.historyLoading = true
      try {
        const { data } = await axios.get(`${API}/doctor/patients/${patient.id}/history`)
        this.historyData = data
      } catch (e) { console.error(e) }
      finally { this.historyLoading = false }
    },
    statusBadge(s) {
      return { Booked: 'badge bg-primary', Completed: 'badge bg-success', Cancelled: 'badge bg-danger' }[s] || 'badge bg-secondary'
    },
  },
}
</script>
