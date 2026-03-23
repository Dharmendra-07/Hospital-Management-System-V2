<template>
  <div>
    <div class="alert alert-info border-0 shadow-sm">
      <strong>📌 Note:</strong> Set your available time slots for the next 7 days.
      Patients will be able to book appointments only during these slots.
      Slots already booked by patients cannot be removed.
    </div>

    <div v-if="alert.msg" :class="`alert alert-${alert.type} alert-dismissible`">
      {{ alert.msg }}
      <button type="button" class="btn-close" @click="alert.msg=''"></button>
    </div>

    <div v-if="loading" class="text-center py-4">
      <div class="spinner-border text-primary"></div>
    </div>

    <div v-else class="card border-0 shadow-sm">
      <div class="card-header bg-white fw-semibold border-bottom d-flex justify-content-between">
        <span>🗓️ Availability for Next 7 Days</span>
        <button class="btn btn-primary btn-sm" @click="saveAll" :disabled="saving">
          <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
          Save All
        </button>
      </div>

      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th style="width:160px;">Date</th>
                <th v-for="slot in SLOTS" :key="slot.val">
                  <div class="fw-semibold small">{{ slot.label }}</div>
                  <div class="text-muted" style="font-size:11px;">{{ slot.val }}</div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="day in availability" :key="day.date">
                <td>
                  <div class="fw-semibold small">{{ formatDate(day.date) }}</div>
                  <div class="text-muted" style="font-size:11px;">{{ day.date }}</div>
                </td>
                <td v-for="slot in SLOTS" :key="slot.val" class="text-center">
                  <div class="d-flex flex-column align-items-center gap-1">
                    <!-- Booked slot (locked) -->
                    <span v-if="isBooked(day, slot.val)"
                          class="badge bg-danger px-2 py-1">Booked</span>
                    <!-- Toggle checkbox -->
                    <div v-else class="form-check form-switch mb-0">
                      <input
                        class="form-check-input"
                        type="checkbox"
                        role="switch"
                        :id="`slot-${day.date}-${slot.val}`"
                        :checked="isSelected(day, slot.val)"
                        @change="toggleSlot(day, slot.val)"
                      />
                    </div>
                    <span v-if="isSelected(day, slot.val) && !isBooked(day, slot.val)"
                          class="badge bg-success" style="font-size:10px;">Available</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Quick select row -->
      <div class="card-footer bg-white d-flex gap-2 flex-wrap">
        <span class="text-muted small fw-semibold me-1 align-self-center">Quick select:</span>
        <button class="btn btn-outline-success btn-sm" @click="selectAll('08:00-12:00')">
          All Morning
        </button>
        <button class="btn btn-outline-warning btn-sm" @click="selectAll('16:00-21:00')">
          All Evening
        </button>
        <button class="btn btn-outline-primary btn-sm" @click="selectAllSlots">
          All Slots
        </button>
        <button class="btn btn-outline-danger btn-sm" @click="clearAll">
          Clear All
        </button>
      </div>
    </div>

    <!-- Legend -->
    <div class="d-flex gap-3 mt-3 flex-wrap">
      <div class="d-flex align-items-center gap-1">
        <span class="badge bg-success px-2">Available</span>
        <small class="text-muted">Slot is open for booking</small>
      </div>
      <div class="d-flex align-items-center gap-1">
        <span class="badge bg-danger px-2">Booked</span>
        <small class="text-muted">Patient already booked — cannot remove</small>
      </div>
      <div class="d-flex align-items-center gap-1">
        <div class="form-check form-switch mb-0">
          <input class="form-check-input" type="checkbox" disabled />
        </div>
        <small class="text-muted">Toggle to mark/unmark</small>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

const SLOTS = [
  { label: 'Morning',   val: '08:00-12:00' },
  { label: 'Afternoon', val: '12:00-16:00' },
  { label: 'Evening',   val: '16:00-21:00' },
]

export default {
  name: 'DoctorAvailability',
  data() {
    return {
      availability: [],   // [{ date, slots: [{ id, slot, is_booked }], selected: Set }]
      loading:      true,
      saving:       false,
      alert:        { msg: '', type: 'success' },
      SLOTS,
    }
  },
  async mounted() { await this.fetchAvailability() },
  methods: {
    async fetchAvailability() {
      this.loading = true
      try {
        const { data } = await axios.get(`${API}/doctor/availability`)
        // Attach a `selected` Set to each day for easy toggle tracking
        this.availability = data.map(day => ({
          ...day,
          selected: new Set(day.slots.map(s => s.slot)),
        }))
      } catch (e) { console.error(e) }
      finally { this.loading = false }
    },

    isBooked(day, slotVal) {
      return day.slots.some(s => s.slot === slotVal && s.is_booked)
    },
    isSelected(day, slotVal) {
      return day.selected.has(slotVal)
    },
    toggleSlot(day, slotVal) {
      if (this.isBooked(day, slotVal)) return
      if (day.selected.has(slotVal)) {
        day.selected.delete(slotVal)
      } else {
        day.selected.add(slotVal)
      }
      // Trigger reactivity
      day.selected = new Set(day.selected)
    },

    selectAll(slotVal) {
      this.availability.forEach(day => {
        if (!this.isBooked(day, slotVal)) day.selected.add(slotVal)
        day.selected = new Set(day.selected)
      })
    },
    selectAllSlots() {
      this.availability.forEach(day => {
        SLOTS.forEach(s => { if (!this.isBooked(day, s.val)) day.selected.add(s.val) })
        day.selected = new Set(day.selected)
      })
    },
    clearAll() {
      this.availability.forEach(day => {
        const keepBooked = new Set(day.slots.filter(s => s.is_booked).map(s => s.slot))
        day.selected = keepBooked
      })
    },

    async saveAll() {
      this.saving = true
      try {
        const payload = this.availability.map(day => ({
          date:  day.date,
          slots: [...day.selected],
        }))
        await axios.post(`${API}/doctor/availability`, payload)
        await this.fetchAvailability()
        this.showAlert('Availability saved successfully.', 'success')
      } catch (e) {
        this.showAlert('Failed to save availability.', 'danger')
      } finally { this.saving = false }
    },

    formatDate(dateStr) {
      const d = new Date(dateStr)
      return d.toLocaleDateString('en-IN', { weekday: 'short', month: 'short', day: 'numeric' })
    },
    showAlert(msg, type = 'success') {
      this.alert = { msg, type }
      setTimeout(() => { this.alert.msg = '' }, 3500)
    },
  },
}
</script>
