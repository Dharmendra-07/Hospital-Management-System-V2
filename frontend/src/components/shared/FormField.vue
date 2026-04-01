<template>
  <div class="mb-3">
    <label v-if="label" :for="id" class="form-label">
      {{ label }}
      <span v-if="required" class="text-danger ms-1">*</span>
      <span v-if="hint" class="text-muted fw-normal ms-1" style="font-size:11px;">({{ hint }})</span>
    </label>

    <!-- Textarea -->
    <textarea
      v-if="type === 'textarea'"
      :id="id"
      v-model="innerValue"
      :class="['form-control', validationClass]"
      :placeholder="placeholder"
      :rows="rows"
      :disabled="disabled"
      :aria-describedby="error ? `${id}-error` : undefined"
      @blur="handleBlur"
    ></textarea>

    <!-- Select -->
    <select
      v-else-if="type === 'select'"
      :id="id"
      v-model="innerValue"
      :class="['form-select', validationClass]"
      :disabled="disabled"
      :aria-describedby="error ? `${id}-error` : undefined"
      @blur="handleBlur"
    >
      <option value="">{{ placeholder || 'Select…' }}</option>
      <option v-for="opt in options" :key="optVal(opt)" :value="optVal(opt)">
        {{ optLabel(opt) }}
      </option>
    </select>

    <!-- Password with toggle -->
    <div v-else-if="type === 'password'" class="input-group">
      <input
        :id="id"
        v-model="innerValue"
        :type="showPw ? 'text' : 'password'"
        :class="['form-control', validationClass]"
        :placeholder="placeholder"
        :disabled="disabled"
        :aria-describedby="error ? `${id}-error` : undefined"
        @blur="handleBlur"
      />
      <button class="btn btn-outline-secondary" type="button"
              @click="showPw = !showPw" :aria-label="showPw ? 'Hide password' : 'Show password'">
        {{ showPw ? '🙈' : '👁️' }}
      </button>
    </div>

    <!-- Default input -->
    <input
      v-else
      :id="id"
      v-model="innerValue"
      :type="type || 'text'"
      :class="['form-control', validationClass]"
      :placeholder="placeholder"
      :disabled="disabled"
      :min="min"
      :max="max"
      :aria-describedby="error ? `${id}-error` : undefined"
      @blur="handleBlur"
    />

    <!-- Error message -->
    <div v-if="error && touched" :id="`${id}-error`"
         class="invalid-feedback d-block" role="alert">
      {{ error }}
    </div>

    <!-- Helper text -->
    <div v-if="helperText && !error" class="form-text text-muted">{{ helperText }}</div>
  </div>
</template>

<script>
let counter = 0

export default {
  name: 'FormField',
  props: {
    modelValue:  { default: '' },
    label:       { type: String,  default: '' },
    type:        { type: String,  default: 'text' },
    placeholder: { type: String,  default: '' },
    required:    { type: Boolean, default: false },
    disabled:    { type: Boolean, default: false },
    error:       { type: String,  default: '' },
    hint:        { type: String,  default: '' },
    helperText:  { type: String,  default: '' },
    rows:        { type: Number,  default: 3 },
    min:         { default: undefined },
    max:         { default: undefined },
    options:     { type: Array,   default: () => [] },   // [string] or [{value, label}]
    optionValue: { type: String,  default: 'value' },
    optionLabel: { type: String,  default: 'label' },
  },
  emits: ['update:modelValue', 'blur'],
  data() {
    return {
      id:      `hms-field-${++counter}`,
      touched: false,
      showPw:  false,
    }
  },
  computed: {
    innerValue: {
      get() { return this.modelValue },
      set(v) { this.$emit('update:modelValue', v) },
    },
    validationClass() {
      if (!this.touched) return ''
      return this.error ? 'is-invalid' : 'is-valid'
    },
  },
  methods: {
    handleBlur() {
      this.touched = true
      this.$emit('blur')
    },
    optVal(opt) { return typeof opt === 'object' ? opt[this.optionValue] : opt },
    optLabel(opt) { return typeof opt === 'object' ? opt[this.optionLabel] : opt },
  },
}
</script>
