<template>
  <div>
    <!-- Search bar -->
    <div class="card border-0 shadow-sm mb-4">
      <div class="card-body">
        <div class="row g-2 align-items-end">
          <div class="col-md-5">
            <label class="form-label small fw-semibold mb-1">Search by name or specialization</label>
            <input v-model="search" type="text" class="form-control"
                   placeholder="e.g. Cardiology, Dr. Sharma…"
                   @keyup.enter="fetchDoctors" />
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold mb-1">Department</label>
            <select v-model="selectedDept" class="form-select">
              <option value="">All Departments</option>
              <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </div>
          <div class="col-md-3 d-flex gap-2">
            <button class="btn btn-primary flex-grow-1" @click="fetchDoctors">Search</button>
            <button class="btn btn-outline-secondary" @click="clearSearch">✕</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Doctor cards -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>
    <div v-else-if="doctors.length === 0" class="text-center py-5 text-muted">
      No doctors found. Try a different search.
    </div>
    <div v-else class="row g-3 mb-4">
      <div class="col-md-6 col-xl-4" v-for="d in doctors" :key="d.id">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-body">
            <div class="d-flex align-items-center gap-3 mb-3">
              <div class="rounded-circle bg-primary bg-opacity-10 text-primary fw-bold
                          d-flex align-items-center justify-content-center"
                   style="width:48px;height:48px;font-size:18px;">
                {{ d.full_name.charAt(0) }}
              </div>
              <div>
                <div class="fw-semibold">Dr. {{ d.full_name }}</div>
                <div class="text-muted small">{{ d.specialization }}</div>
                <div class="text-muted" style="font-size:11px;">{{ d.department }}</div>
              </div>
            </div>
            <div class="d-flex gap-2 flex-wrap mb-3" style="font-size:12px;">
              <span class="badge bg-secondary bg-opacity-10 text-secondary border">
                {{ d.qualification || 'MBBS' }}
              </span>
              <span class="badge bg-secondary bg-opacity-10 text-secondary border">
                {{ d.experience_years }} yr exp
              </span>
              <span :class="d.available_slots > 0
                ? 'badge bg-success bg-opacity-10 text-success border border-success'
                : 'badge bg-danger bg-opacity-10 text-danger border border-danger'">
                {{ d.available_slots }} slot{{ d.available_slots !== 1 ? 's' : '' }} free
              </span>
            </div>
            <p v-if="d.bio" class="text-muted small mb-0"
               style="display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">
              {{ d.bio }}
            </p>
          </div>
          <div class="card-footer bg-white border-top d-flex gap-2">
            <button class="btn btn-outline-primary btn-sm flex-grow-1"
                    @click="viewDoctor(d)">View Profile</button>
            <button class="btn btn-primary btn-sm flex-grow-1"
                    :disabled="d.available_slots === 0"
                    @click="openBook(d)">Book</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Doctor Profile Modal -->
    <div v-if="selectedDoctor && showProfile" class="modal d-block" style="background:rgba(0,0,0,.5);">
      <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <div>
              <h5 class="modal-title">Dr. {{ selectedDoctor.full_name }}</h5>
              <div class="text-muted small">
                {{ selectedDoctor.specialization }} · {{ selectedDoctor.department }}
              </div>
            </div>
            <button type="button" class="btn-close" @click="showProfile=false"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3 mb-4">
              <div class="col-sm-4">
                <div class="text-muted small fw-semibold">Qualification</div>
                <div>{{ selectedDoctor.qualification || '—' }}</div>
              </div>
              <div class="col-sm-4">
                <div class="text-muted small fw-semibold">Experience</div>
                <div>{{ selectedDoctor.experience_years }} years</div>
              </div>
              <div class="col-sm-4">
                <div class="text-muted small fw-semibold">Contact</div>
                <div>{{ selectedDoctor.contact_number || '—' }}</div>
              </div>
              <div class="col-12" v-if="selectedDoctor.bio">
                <div class="text-muted small fw-semibold">About</div>
                <div>{{ selectedDoctor.bio }}</div>
              </div>
            </div>
            <h6 class="fw-semibold mb-3">📅 Availability (Next 7 Days)</h6>
            <div v-for="day in selectedDoctor.availability" :key="day.date" class="mb-2">
              <div class="d-flex align-items-center gap-2 flex-wrap">
                <span class="text-muted small fw-semibold" style="min-width:100px;">{{ day.date }}</span>
                <span v-if="day.slots.length === 0" class="text-muted small fst-italic">No slots</span>
                <button v-for="s in day.slots" :key="s.id"
                        :class="['btn btn-sm', s.is_booked
                          ? 'btn-danger opacity-50 disabled' : 'btn-outline-success']"
                        :disabled="s.is_booked"
                        @click="quickBook(selectedDoctor, day.date, s.slot)">
                  {{ s.slot }} {{ s.is_booked ? '(Booked)' : '' }}
                </button>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showProfile=false">Close</button>
            <button class="btn btn-primary" @click="openBook(selectedDoctor)">Book Appointment</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Book Appointment Modal (with ConflictChecker) -->
    <div v-if="showBook" class="modal d-block" style="background:rgba(0,0,0,.5);">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <div>
              <h5 class="modal-title">Book Appointment</h5>
              <div class="text-muted small">Dr. {{ bookDoctor?.full_name }}</div>
            </div>
            <button type="button" class="btn-close" @click="showBook=false"></button>
          </div>
          <div class="modal-body">
            <!-- Date -->
            <div class="mb-3">
              <label class="form-label fw-semibold">Select Date</label>
              <select v-model="bookForm.date" class="form-select" @change="onDateChange">
                <option value="">-- Choose a date --</option>
                <option v-for="day in bookDays" :key="day.date"
                        :value="day.date"
                        :disabled="day.freeSlots.length === 0">
                  {{ day.date }}
                  ({{ day.freeSlots.length }} slot{{ day.freeSlots.length !== 1 ? 's' : '' }})
                </option>
              </select>
            </div>

            <!-- Slot picker with live conflict check -->
            <ConflictChecker
              v-if="bookForm.date"
              v-model="bookForm.time_slot"
              :slots="slotsForSelectedDate"
              :doctor-id="bookDoctor?.id"
              :date="bookForm.date"
            />

            <!-- Visit type + notes -->
            <div class="mb-3">
              <label class="form-label fw-semibold">Visit Type</label>
              <select v-model="bookForm.visit_type" class="form-select">
                <option>In-person</option>
                <option>Online</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label fw-semibold">Notes (optional)</label>
              <textarea v-model="bookForm.notes" class="form-control" rows="2"
                        placeholder="Describe your symptoms or reason for visit…"></textarea>
            </div>
            <div v-if="bookError" class="alert alert-danger mb-0">{{ bookError }}</div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showBook=false">Cancel</button>
            <button class="btn btn-primary" @click="confirmBook" :disabled="booking">
              <span v-if="booking" class="spinner-border spinner-border-sm me-1"></span>
              Confirm Booking
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import ConflictChecker from '../shared/ConflictChecker.vue'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'PatientDoctors',
  components: { ConflictChecker },
  emits: ['booked'],
  data() {
    return {
      doctors: [], departments: [], loading: false,
      search: '', selectedDept: '',
      selectedDoctor: null, showProfile: false,
      showBook: false, bookDoctor: null,
      bookDays: [],
      bookForm: { date: '', time_slot: '', visit_type: 'In-person', notes: '' },
      bookError: '', booking: false,
    }
  },
  computed: {
    slotsForSelectedDate() {
      if (!this.bookForm.date) return []
      const day = this.bookDays.find(d => d.date === this.bookForm.date)
      return day ? day.freeSlots : []
    },
  },
  async mounted() {
    await Promise.all([this.fetchDoctors(), this.fetchDepts()])
  },
  methods: {
    async fetchDoctors() {
      this.loading = true
      try {
        const { data } = await axios.get(`${API}/patient/doctors`, {
          params: { q: this.search, department_id: this.selectedDept || undefined },
        })
        this.doctors = data
      } catch (e) { console.error(e) }
      finally { this.loading = false }
    },
    async fetchDepts() {
      try {
        const { data } = await axios.get(`${API}/patient/departments`)
        this.departments = data
      } catch (e) { console.error(e) }
    },
    clearSearch() { this.search = ''; this.selectedDept = ''; this.fetchDoctors() },

    async viewDoctor(d) {
      this.showProfile = true
      try {
        const { data } = await axios.get(`${API}/patient/doctors/${d.id}`)
        this.selectedDoctor = data
      } catch (e) { console.error(e) }
    },

    quickBook(doctor, dateStr, slot) {
      this.showProfile = false
      this.openBook(doctor)
      this.$nextTick(() => {
        this.bookForm.date      = dateStr
        this.bookForm.time_slot = slot
      })
    },

    async openBook(doctor) {
      this.showBook   = true
      this.bookDoctor = doctor
      this.bookError  = ''
      this.bookForm   = { date: '', time_slot: '', visit_type: 'In-person', notes: '' }
      this.showProfile = false
      try {
        const { data } = await axios.get(`${API}/patient/doctors/${doctor.id}`)
        this.bookDays = data.availability.map(day => ({
          date:      day.date,
          freeSlots: day.slots.filter(s => !s.is_booked).map(s => s.slot),
        }))
      } catch (e) { console.error(e) }
    },

    onDateChange() { this.bookForm.time_slot = '' },

    async confirmBook() {
      this.bookError = ''
      if (!this.bookForm.date)      { this.bookError = 'Please select a date.';      return }
      if (!this.bookForm.time_slot) { this.bookError = 'Please select a time slot.'; return }
      this.booking = true
      try {
        await axios.post(`${API}/patient/appointments`, {
          doctor_id:  this.bookDoctor.id,
          date:       this.bookForm.date,
          time_slot:  this.bookForm.time_slot,
          visit_type: this.bookForm.visit_type,
          notes:      this.bookForm.notes,
        })
        this.showBook = false
        this.$emit('booked')
      } catch (e) {
        this.bookError = e.response?.data?.error || 'Booking failed. Please try again.'
      } finally { this.booking = false }
    },
  },
}
</script>
