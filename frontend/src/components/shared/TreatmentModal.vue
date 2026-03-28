<template>
  <div v-if="show" class="modal d-block" style="background:rgba(0,0,0,.5);">
    <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
      <div class="modal-content">

        <!-- Header -->
        <div class="modal-header">
          <div>
            <h5 class="modal-title mb-0">
              {{ appointment?.treatment ? 'Edit Treatment' : 'Add Treatment' }}
            </h5>
            <div class="text-muted small" v-if="appointment">
              Appt #{{ appointment.id }} ·
              {{ appointment.patient_name }} ·
              {{ appointment.date }} · {{ appointment.time_slot }}
            </div>
          </div>
          <button type="button" class="btn-close" @click="$emit('close')"></button>
        </div>

        <!-- Body -->
        <div class="modal-body">
          <div class="row g-3">

            <!-- Diagnosis -->
            <div class="col-12">
              <label class="form-label fw-semibold">
                Diagnosis <span class="text-danger">*</span>
              </label>
              <textarea v-model="form.diagnosis" class="form-control" rows="3"
                        placeholder="Enter diagnosis details…"
                        :class="{ 'is-invalid': errors.diagnosis }"></textarea>
              <div class="invalid-feedback">{{ errors.diagnosis }}</div>
            </div>

            <!-- Prescription -->
            <div class="col-12">
              <label class="form-label fw-semibold">Prescription</label>
              <textarea v-model="form.prescription" class="form-control" rows="2"
                        placeholder="Enter prescription…"></textarea>
            </div>

            <!-- Tests Done -->
            <div class="col-md-6">
              <label class="form-label fw-semibold">Tests Done</label>
              <input v-model="form.tests_done" type="text" class="form-control"
                     placeholder="e.g. ECG, Blood Test, X-Ray" />
            </div>

            <!-- Next Visit -->
            <div class="col-md-6">
              <label class="form-label fw-semibold">Next Visit Date</label>
              <input v-model="form.next_visit" type="date" class="form-control" />
            </div>

            <!-- Medicines -->
            <div class="col-12">
              <label class="form-label fw-semibold d-flex justify-content-between align-items-center">
                <span>Medicines</span>
                <button type="button" class="btn btn-outline-primary btn-sm"
                        @click="addMedicine">+ Add Medicine</button>
              </label>

              <div v-if="form.medicines.length === 0"
                   class="text-muted small fst-italic py-2">
                No medicines added yet. Click "+ Add Medicine" to start.
              </div>

              <div v-for="(med, idx) in form.medicines" :key="idx"
                   class="d-flex gap-2 mb-2 align-items-center">
                <input v-model="med.name" type="text"
                       class="form-control form-control-sm"
                       placeholder="Medicine name" style="flex:2;" />
                <input v-model="med.dosage" type="text"
                       class="form-control form-control-sm"
                       placeholder="Dosage (e.g. 1-0-1)" style="flex:1;" />
                <input v-model="med.duration" type="text"
                       class="form-control form-control-sm"
                       placeholder="Days" style="max-width:80px;" />
                <button type="button" class="btn btn-outline-danger btn-sm"
                        @click="removeMedicine(idx)">✕</button>
              </div>
            </div>

            <!-- Doctor Notes -->
            <div class="col-12">
              <label class="form-label fw-semibold">
                Doctor Notes
                <span class="text-muted small fw-normal">(internal — not shown to patient)</span>
              </label>
              <textarea v-model="form.doctor_notes" class="form-control" rows="2"
                        placeholder="Internal observations or follow-up notes…"></textarea>
            </div>

          </div>

          <!-- Status preview -->
          <div class="alert alert-info small mt-3 mb-0 d-flex align-items-center gap-2">
            <span>ℹ️</span>
            <span>Saving this treatment will automatically mark the appointment as
              <strong>Completed</strong>.</span>
          </div>

          <!-- Error -->
          <div v-if="submitError" class="alert alert-danger mt-3 mb-0">
            {{ submitError }}
          </div>
        </div>

        <!-- Footer -->
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="$emit('close')">
            Cancel
          </button>
          <button type="button" class="btn btn-primary" @click="submit" :disabled="saving">
            <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
            {{ saving ? 'Saving…' : 'Save Treatment' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

const emptyForm = () => ({
  diagnosis:    '',
  prescription: '',
  tests_done:   '',
  next_visit:   '',
  doctor_notes: '',
  medicines:    [],
})

export default {
  name: 'TreatmentModal',
  props: {
    show:        { type: Boolean, default: false },
    appointment: { type: Object,  default: null  },
  },
  emits: ['close', 'saved'],
  data() {
    return {
      form:        emptyForm(),
      errors:      {},
      submitError: '',
      saving:      false,
    }
  },
  watch: {
    // Pre-fill when opening with an existing treatment
    appointment: {
      immediate: true,
      handler(appt) {
        if (!appt) { this.form = emptyForm(); return }
        if (appt.treatment) {
          const t = appt.treatment
          this.form = {
            diagnosis:    t.diagnosis    || '',
            prescription: t.prescription || '',
            tests_done:   t.tests_done   || '',
            next_visit:   t.next_visit   || '',
            doctor_notes: t.doctor_notes || '',
            medicines:    t.medicines    || [],
          }
        } else {
          this.form = emptyForm()
        }
        this.errors      = {}
        this.submitError = ''
      },
    },
  },
  methods: {
    addMedicine()       { this.form.medicines.push({ name: '', dosage: '', duration: '' }) },
    removeMedicine(idx) { this.form.medicines.splice(idx, 1) },

    validate() {
      this.errors = {}
      if (!this.form.diagnosis.trim()) {
        this.errors.diagnosis = 'Diagnosis is required.'
      }
      // Remove blank medicine rows
      this.form.medicines = this.form.medicines.filter(m => m.name.trim())
      return Object.keys(this.errors).length === 0
    },

    async submit() {
      this.submitError = ''
      if (!this.validate()) return
      this.saving = true
      try {
        const { data } = await axios.post(
          `${API}/appointments/${this.appointment.id}/treatment`,
          this.form
        )
        this.$emit('saved', data)
      } catch (e) {
        this.submitError = e.response?.data?.error || 'Failed to save treatment. Please try again.'
      } finally {
        this.saving = false
      }
    },
  },
}
</script>
