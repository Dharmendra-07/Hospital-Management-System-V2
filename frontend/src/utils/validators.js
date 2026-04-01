/**
 * frontend/src/utils/validators.js
 * Reusable frontend validation rules.
 * Each validator returns null (valid) or an error string (invalid).
 */

// ── Primitives ──────────────────────────────────────────────

export const required = (label = 'This field') =>
  (v) => (!v || !String(v).trim()) ? `${label} is required.` : null

export const minLen = (n, label = 'Value') =>
  (v) => v && String(v).trim().length < n
    ? `${label} must be at least ${n} characters.`
    : null

export const maxLen = (n, label = 'Value') =>
  (v) => v && String(v).trim().length > n
    ? `${label} must be at most ${n} characters.`
    : null

export const isEmail = (v) =>
  v && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)
    ? 'Enter a valid email address.'
    : null

export const isPhone = (v) =>
  v && !/^[+\d\s\-()]{7,15}$/.test(v)
    ? 'Enter a valid phone number.'
    : null

export const isDate = (v) =>
  v && isNaN(Date.parse(v)) ? 'Enter a valid date.' : null

export const isFuture = (v) =>
  v && new Date(v) < new Date(new Date().toDateString())
    ? 'Date must be today or in the future.'
    : null

export const isPast = (v) =>
  v && new Date(v) > new Date() ? 'Date must be in the past.' : null

export const isNumber = (label = 'Value') =>
  (v) => v !== '' && v !== null && isNaN(Number(v))
    ? `${label} must be a number.`
    : null

export const min = (n, label = 'Value') =>
  (v) => v !== '' && Number(v) < n ? `${label} must be at least ${n}.` : null

export const max = (n, label = 'Value') =>
  (v) => v !== '' && Number(v) > n ? `${label} must be at most ${n}.` : null

export const matches = (otherVal, label = 'Fields') =>
  (v) => v !== otherVal ? `${label} do not match.` : null

export const noSpaces = (v) =>
  v && /\s/.test(v) ? 'No spaces allowed.' : null

// ── Composer — run multiple rules ───────────────────────────

/**
 * Run a list of validators against a value.
 * Returns the first error string, or null if all pass.
 *
 * @param {*} value
 * @param {...Function} rules  — validators from above
 * @returns {string|null}
 */
export function validate(value, ...rules) {
  for (const rule of rules) {
    const err = rule(value)
    if (err) return err
  }
  return null
}

// ── Form-level validator ────────────────────────────────────

/**
 * Validate an entire form object against a schema.
 *
 * @param {Object} form   — { fieldName: value, … }
 * @param {Object} schema — { fieldName: [rule1, rule2, …], … }
 * @returns {{ errors: Object, isValid: boolean }}
 *
 * Example:
 *   const { errors, isValid } = validateForm(form, {
 *     email:    [required('Email'), isEmail],
 *     password: [required('Password'), minLen(6, 'Password')],
 *   })
 */
export function validateForm(form, schema) {
  const errors = {}
  for (const [field, rules] of Object.entries(schema)) {
    const err = validate(form[field], ...rules)
    if (err) errors[field] = err
  }
  return { errors, isValid: Object.keys(errors).length === 0 }
}

// ── Pre-built schemas ────────────────────────────────────────

export const schemas = {
  patientRegister: {
    full_name: [required('Full name')],
    username:  [required('Username'), minLen(3, 'Username'), noSpaces],
    email:     [required('Email'), isEmail],
    password:  [required('Password'), minLen(6, 'Password')],
  },

  patientProfile: {
    full_name: [required('Full name')],
    email:     [isEmail],
    contact_number: [isPhone],
  },

  bookAppointment: {
    doctor_id:  [required('Doctor')],
    date:       [required('Date'), isFuture],
    time_slot:  [required('Time slot')],
    visit_type: [required('Visit type')],
  },

  addDoctor: {
    full_name:      [required('Full name')],
    username:       [required('Username'), minLen(3, 'Username'), noSpaces],
    email:          [required('Email'), isEmail],
    password:       [required('Password'), minLen(6, 'Password')],
    specialization: [required('Specialization')],
    experience_years: [isNumber('Experience'), min(0, 'Experience')],
  },

  treatment: {
    diagnosis: [required('Diagnosis')],
  },

  login: {
    username: [required('Username')],
    password: [required('Password')],
  },
}
