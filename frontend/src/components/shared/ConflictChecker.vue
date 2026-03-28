<template>
  <div>
    <!-- Slot selector with live conflict check -->
    <div class="mb-3">
      <label class="form-label fw-semibold">
        Select Time Slot
        <span v-if="checking" class="spinner-border spinner-border-sm ms-2 text-secondary"></span>
      </label>

      <div class="d-flex flex-wrap gap-2 mb-2" v-if="slots.length > 0">
        <button
          v-for="s in slots"
          :key="s"
          type="button"
          :class="slotClass(s)"
          :disabled="conflictMap[s] === true || checking"
          @click="select(s)"
        >
          {{ s }}
          <span v-if="conflictMap[s] === true"
                class="ms-1 badge bg-danger" style="font-size:9px;">Taken</span>
          <span v-else-if="conflictMap[s] === false && modelValue === s"
                class="ms-1 badge bg-success" style="font-size:9px;">Free</span>
        </button>
      </div>

      <div v-else class="text-muted small fst-italic">
        No slots available for this date.
      </div>

      <!-- Conflict warning -->
      <div v-if="conflictReason" class="alert alert-warning py-2 mt-2 mb-0 small">
        ⚠️ {{ conflictReason }}
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export default {
  name: 'ConflictChecker',
  props: {
    modelValue: { type: String,  default: '' },      // selected slot (v-model)
    slots:      { type: Array,   default: () => [] }, // available slot strings
    doctorId:   { type: Number,  default: null },
    date:       { type: String,  default: '' },
  },
  emits: ['update:modelValue', 'conflict-resolved'],
  data() {
    return {
      conflictMap:    {},   // { 'slot': true/false }
      conflictReason: '',
      checking:       false,
    }
  },
  watch: {
    // Re-check all slots when date or doctor changes
    date(newVal) { if (newVal) this.checkAll() },
    slots(newVal) { if (newVal.length) this.checkAll() },
  },
  methods: {
    async checkAll() {
      if (!this.doctorId || !this.date || !this.slots.length) return
      this.checking = true
      this.conflictMap = {}

      await Promise.all(this.slots.map(async slot => {
        try {
          const { data } = await axios.post(`${API}/appointments/check-conflict`, {
            doctor_id: this.doctorId,
            date:      this.date,
            time_slot: slot,
          })
          this.conflictMap = { ...this.conflictMap, [slot]: data.conflict }
        } catch (e) {
          this.conflictMap = { ...this.conflictMap, [slot]: false }
        }
      }))
      this.checking = false

      // Auto-deselect if currently selected slot is now conflicted
      if (this.modelValue && this.conflictMap[this.modelValue] === true) {
        this.$emit('update:modelValue', '')
        this.conflictReason = 'Your selected slot is no longer available. Please choose another.'
      } else {
        this.conflictReason = ''
      }
    },

    async select(slot) {
      if (this.conflictMap[slot]) return
      this.conflictReason = ''

      // Live single-slot check before confirming
      try {
        const { data } = await axios.post(`${API}/appointments/check-conflict`, {
          doctor_id: this.doctorId,
          date:      this.date,
          time_slot: slot,
        })
        if (data.conflict) {
          this.conflictMap = { ...this.conflictMap, [slot]: true }
          this.conflictReason = data.reason || 'This slot is already taken.'
          this.$emit('update:modelValue', '')
          return
        }
      } catch (e) { /* proceed */ }

      this.$emit('update:modelValue', slot)
      this.$emit('conflict-resolved')
    },

    slotClass(s) {
      const taken    = this.conflictMap[s] === true
      const selected = this.modelValue === s
      if (taken)    return 'btn btn-sm btn-danger opacity-50 disabled'
      if (selected) return 'btn btn-sm btn-primary'
      return 'btn btn-sm btn-outline-primary'
    },
  },
}
</script>
