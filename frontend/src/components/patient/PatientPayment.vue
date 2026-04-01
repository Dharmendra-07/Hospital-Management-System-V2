<template>
  <div>
    <!-- Unpaid appointments -->
    <div class="hms-card mb-4">
      <div class="card-header">💳 Pay for Completed Appointments</div>
      <div class="card-body p-0">
        <div v-if="loading" class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-primary"></div>
        </div>
        <div v-else-if="unpaidAppts.length === 0"
             class="text-center py-5 text-muted">
          <div class="fs-1 mb-2">✅</div>
          <div class="fw-semibold">All clear!</div>
          <div class="small mt-1">No pending payments.</div>
        </div>
        <div v-else class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Doctor</th><th>Specialization</th><th>Date</th>
                <th>Amount</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in unpaidAppts" :key="a.id">
                <td class="fw-semibold">Dr. {{ a.doctor_name }}</td>
                <td>{{ a.specialization }}</td>
                <td>{{ a.date }}</td>
                <td class="fw-bold text-primary">₹{{ getFee(a) }}</td>
                <td>
                  <button class="btn btn-primary btn-sm" @click="startPayment(a)">
                    Pay Now
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Payment history -->
    <div class="hms-card">
      <div class="card-header d-flex justify-content-between">
        <span>🧾 Payment History</span>
        <span class="badge bg-success rounded-pill">
          ₹{{ totalPaid }} paid
        </span>
      </div>
      <div class="card-body p-0">
        <div v-if="payHistory.length === 0"
             class="text-center py-4 text-muted small">No payment records yet.</div>
        <div class="table-responsive" v-else>
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Receipt</th><th>Doctor</th><th>Date</th>
                <th>Amount</th><th>Method</th><th>Status</th><th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in payHistory" :key="p.id">
                <td class="small text-muted"><code>{{ p.id }}</code></td>
                <td>Dr. {{ p.doctor_name }}</td>
                <td>{{ p.appt_date }}</td>
                <td class="fw-bold">₹{{ p.amount }}</td>
                <td>{{ p.payment_method?.toUpperCase() }}</td>
                <td>
                  <span :class="statusBadge(p.status)">{{ p.status }}</span>
                </td>
                <td>
                  <button v-if="p.status === 'paid'"
                          class="btn btn-outline-secondary btn-sm"
                          @click="viewReceipt(p)">Receipt</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Payment Modal ─────────────────────── -->
    <div v-if="showPayModal" class="modal d-block" style="background:rgba(0,0,0,.5);">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">

          <!-- Step 1: Method selection -->
          <template v-if="payStep === 1">
            <div class="modal-header">
              <h5 class="modal-title">Choose Payment Method</h5>
              <button class="btn-close" @click="closePayModal"></button>
            </div>
            <div class="modal-body">
              <div class="text-center mb-4">
                <div class="fw-bold">Dr. {{ currentAppt?.doctor_name }}</div>
                <div class="text-muted small">{{ currentAppt?.specialization }} · {{ currentAppt?.date }}</div>
                <div class="display-6 fw-bold text-primary mt-2">₹{{ currentFee }}</div>
              </div>
              <div class="row g-2">
                <div class="col-6" v-for="m in methods" :key="m.value">
                  <button
                    :class="['btn w-100 py-3', payForm.method === m.value
                      ? 'btn-primary' : 'btn-outline-secondary']"
                    @click="payForm.method = m.value"
                  >
                    <div class="fs-4">{{ m.icon }}</div>
                    <div class="small mt-1">{{ m.label }}</div>
                  </button>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" @click="closePayModal">Cancel</button>
              <button class="btn btn-primary" @click="payStep = 2"
                      :disabled="!payForm.method">Continue</button>
            </div>
          </template>

          <!-- Step 2: Payment details -->
          <template v-else-if="payStep === 2">
            <div class="modal-header">
              <h5 class="modal-title">
                {{ methods.find(m=>m.value===payForm.method)?.label }} Details
              </h5>
              <button class="btn-close" @click="closePayModal"></button>
            </div>
            <div class="modal-body">

              <!-- Amount summary -->
              <div class="alert alert-light border mb-3 text-center">
                <div class="small text-muted">Total Amount</div>
                <div class="fw-bold fs-5 text-primary">₹{{ currentFee }}</div>
                <div class="small text-muted">Dr. {{ currentAppt?.doctor_name }}</div>
              </div>

              <!-- Card fields -->
              <div v-if="payForm.method === 'card'" class="row g-3">
                <div class="col-12">
                  <label class="form-label fw-semibold">Card Number</label>
                  <input v-model="payForm.card_number" type="text"
                         class="form-control" placeholder="1234 5678 9012 3456"
                         maxlength="19" @input="formatCard" />
                </div>
                <div class="col-12">
                  <label class="form-label fw-semibold">Card Holder Name</label>
                  <input v-model="payForm.card_holder" type="text"
                         class="form-control" placeholder="As on card" />
                </div>
                <div class="col-6">
                  <label class="form-label fw-semibold">Expiry (MM/YY)</label>
                  <input v-model="payForm.expiry" type="text"
                         class="form-control" placeholder="MM/YY" maxlength="5" />
                </div>
                <div class="col-6">
                  <label class="form-label fw-semibold">CVV</label>
                  <input v-model="payForm.cvv" type="password"
                         class="form-control" placeholder="•••" maxlength="4" />
                </div>
              </div>

              <!-- UPI fields -->
              <div v-else-if="payForm.method === 'upi'">
                <label class="form-label fw-semibold">UPI ID</label>
                <input v-model="payForm.upi_id" type="text"
                       class="form-control" placeholder="yourname@upi" />
                <div class="text-muted small mt-1">e.g. 9876543210@paytm</div>
              </div>

              <!-- Net Banking -->
              <div v-else-if="payForm.method === 'netbanking'">
                <label class="form-label fw-semibold">Select Bank</label>
                <select v-model="payForm.bank" class="form-select">
                  <option value="">Choose your bank</option>
                  <option v-for="b in banks" :key="b">{{ b }}</option>
                </select>
              </div>

              <!-- Cash -->
              <div v-else-if="payForm.method === 'cash'">
                <div class="alert alert-warning">
                  💵 Please pay ₹{{ currentFee }} at the hospital reception.
                  Confirm to mark as paid.
                </div>
              </div>

              <div v-if="payError" class="alert alert-danger mt-3 mb-0 small">
                {{ payError }}
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" @click="payStep = 1">Back</button>
              <button class="btn btn-success" @click="confirmPayment" :disabled="paying">
                <span v-if="paying" class="spinner-border spinner-border-sm me-1"></span>
                {{ paying ? 'Processing…' : `Pay ₹${currentFee}` }}
              </button>
            </div>
          </template>

          <!-- Step 3: Result -->
          <template v-else-if="payStep === 3">
            <div class="modal-header border-0 pb-0">
              <button class="btn-close ms-auto" @click="closePayModal"></button>
            </div>
            <div class="modal-body text-center py-4">
              <div v-if="payResult === 'success'">
                <div style="font-size:64px;">✅</div>
                <h5 class="fw-bold mt-3">Payment Successful!</h5>
                <div class="text-muted small">Transaction ID:</div>
                <code>{{ receiptData?.transaction_id }}</code>
                <div class="mt-3 p-3 bg-light rounded text-start" style="font-size:13px;">
                  <div><b>Amount:</b> ₹{{ receiptData?.amount }}</div>
                  <div><b>Method:</b> {{ receiptData?.payment_method }}</div>
                  <div><b>Doctor:</b> Dr. {{ receiptData?.doctor_name }}</div>
                  <div><b>Paid At:</b> {{ receiptData?.paid_at?.slice(0,19).replace('T',' ') }}</div>
                </div>
              </div>
              <div v-else>
                <div style="font-size:64px;">❌</div>
                <h5 class="fw-bold mt-3 text-danger">Payment Failed</h5>
                <p class="text-muted small">{{ payError }}</p>
              </div>
            </div>
            <div class="modal-footer justify-content-center">
              <button class="btn btn-primary" @click="closePayModal">Done</button>
            </div>
          </template>

        </div>
      </div>
    </div>

    <!-- Receipt Modal -->
    <div v-if="showReceipt" class="modal d-block" style="background:rgba(0,0,0,.5);">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">🧾 Receipt</h5>
            <button class="btn-close" @click="showReceipt=false"></button>
          </div>
          <div class="modal-body" v-if="receiptData">
            <div class="text-center mb-3">
              <div style="font-size:36px;">🏥</div>
              <div class="fw-bold">Hospital Management System</div>
              <div class="text-muted small">Official Payment Receipt</div>
            </div>
            <hr />
            <dl class="row mb-0" style="font-size:13px;">
              <dt class="col-5 text-muted">Receipt No.</dt>
              <dd class="col-7"><code>{{ receiptData.id }}</code></dd>
              <dt class="col-5 text-muted">Txn ID</dt>
              <dd class="col-7"><code>{{ receiptData.transaction_id }}</code></dd>
              <dt class="col-5 text-muted">Patient</dt>
              <dd class="col-7">{{ receiptData.patient_name }}</dd>
              <dt class="col-5 text-muted">Doctor</dt>
              <dd class="col-7">Dr. {{ receiptData.doctor_name }}</dd>
              <dt class="col-5 text-muted">Appointment</dt>
              <dd class="col-7">{{ receiptData.appt_date }}</dd>
              <dt class="col-5 text-muted">Amount</dt>
              <dd class="col-7 fw-bold text-primary">₹{{ receiptData.amount }}</dd>
              <dt class="col-5 text-muted">Method</dt>
              <dd class="col-7">{{ receiptData.payment_method?.toUpperCase() }}</dd>
              <dt class="col-5 text-muted">Status</dt>
              <dd class="col-7"><span class="badge bg-success">PAID</span></dd>
              <dt class="col-5 text-muted">Paid At</dt>
              <dd class="col-7">{{ receiptData.paid_at?.slice(0,19).replace('T',' ') }}</dd>
            </dl>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showReceipt=false">Close</button>
            <button class="btn btn-outline-primary" @click="printReceipt">🖨 Print</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

const FEE_MAP = {
  'Cardiology':1500,'Oncology':2000,'Neurology':1800,'Orthopedics':1200,
  'Gynecology':1000,'Pediatrics':800,'Dermatology':700,'General Medicine':500,
}

export default {
  name: 'PatientPayment',
  data() {
    return {
      allAppts:    [],
      payHistory:  [],
      loading:     true,
      showPayModal:false,
      showReceipt: false,
      payStep:     1,
      currentAppt: null,
      currentPaymentId: null,
      payForm:     { method:'', card_number:'', card_holder:'', expiry:'', cvv:'', upi_id:'', bank:'' },
      payError:    '',
      paying:      false,
      payResult:   null,
      receiptData: null,
      methods: [
        { value:'card',       label:'Credit / Debit Card', icon:'💳' },
        { value:'upi',        label:'UPI',                 icon:'📱' },
        { value:'netbanking', label:'Net Banking',         icon:'🏦' },
        { value:'cash',       label:'Cash (at counter)',   icon:'💵' },
      ],
      banks: ['SBI','HDFC','ICICI','Axis','Kotak','PNB','Bank of Baroda','Canara Bank'],
    }
  },
  computed: {
    unpaidAppts() {
      const paidIds = new Set(this.payHistory
        .filter(p => p.status === 'paid')
        .map(p => p.appointment_id))
      return this.allAppts.filter(a => a.status === 'Completed' && !paidIds.has(a.id))
    },
    currentFee() { return this.currentAppt ? this.getFee(this.currentAppt) : 0 },
    totalPaid()  { return this.payHistory.filter(p=>p.status==='paid').reduce((s,p)=>s+p.amount,0) },
  },
  async mounted() {
    await Promise.all([this.loadAppts(), this.loadHistory()])
  },
  methods: {
    async loadAppts() {
      this.loading = true
      try {
        const { data } = await axios.get(`${API}/patient/appointments`, { params:{ view:'all' } })
        this.allAppts = data
      } catch (e) { console.error(e) }
      finally { this.loading = false }
    },
    async loadHistory() {
      try {
        const { data } = await axios.get(`${API}/payments/history`)
        this.payHistory = data
      } catch (e) { console.error(e) }
    },
    getFee(appt) { return FEE_MAP[appt.specialization] || 800 },
    statusBadge(s) {
      return { paid:'badge bg-success', pending:'badge bg-warning text-dark',
               failed:'badge bg-danger' }[s] || 'badge bg-secondary'
    },

    async startPayment(appt) {
      this.currentAppt = appt
      this.payStep     = 1
      this.payForm     = { method:'', card_number:'', card_holder:'', expiry:'', cvv:'', upi_id:'', bank:'' }
      this.payError    = ''
      this.payResult   = null

      // Initiate on backend
      try {
        const { data } = await axios.post(`${API}/payments/initiate`, {
          appointment_id: appt.id,
          payment_method: 'card',
        })
        this.currentPaymentId = data.payment_id
      } catch (e) {
        const msg = e.response?.data?.error
        if (msg?.includes('already been paid')) {
          await this.loadHistory()
          return
        }
        this.payError = msg || 'Failed to initiate payment.'
        return
      }
      this.showPayModal = true
    },

    async confirmPayment() {
      this.payError = ''
      this.paying   = true

      // Update payment method on backend
      try {
        await axios.post(`${API}/payments/initiate`, {
          appointment_id: this.currentAppt.id,
          payment_method: this.payForm.method,
        })
      } catch (_) {}

      try {
        const { data } = await axios.post(
          `${API}/payments/${this.currentPaymentId}/confirm`,
          this.payForm
        )
        this.payResult  = 'success'
        this.receiptData = { ...data.receipt, patient_name: '' }
        await this.loadHistory()
      } catch (e) {
        this.payResult = 'failed'
        this.payError  = e.response?.data?.message || 'Payment failed.'
      } finally {
        this.paying  = false
        this.payStep = 3
      }
    },

    closePayModal() {
      this.showPayModal = false
      this.currentAppt  = null
    },
    viewReceipt(p) { this.receiptData = p; this.showReceipt = true },
    printReceipt()  { window.print() },
    formatCard()    {
      let v = this.payForm.card_number.replace(/\D/g,'').slice(0,16)
      this.payForm.card_number = v.match(/.{1,4}/g)?.join(' ') || v
    },
  },
}
</script>
