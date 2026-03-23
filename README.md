# 🏥 Hospital Management System V2 (MAD-II)

A full-stack web application built for managing hospital operations including patients, doctors, appointments, and treatments.

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask (Python) |
| Frontend | Vue.js |
| Database | SQLite |
| Caching | Redis |
| Background Jobs | Celery + Redis |
| Styling | Bootstrap 5 |

## 👥 Roles

- **Admin** — Manages doctors, patients, and appointments
- **Doctor** — Views appointments, updates patient treatment history
- **Patient** — Books/cancels appointments, views history

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Redis server

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Redis (required for caching & Celery)
```bash
redis-server
```

### Celery Worker
```bash
cd backend
celery -A celery_worker.celery worker --loglevel=info
```

## 📁 Project Structure

```
HMS-V2/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── models.py
│   ├── routes/
│   ├── tasks/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   ├── components/
│   │   └── router/
│   └── package.json
└── README.md
```

## 📌 Features

- Role-based access control (Admin / Doctor / Patient)
- Appointment booking with conflict prevention
- Daily reminders via email/webhook
- Monthly doctor activity reports (PDF/HTML)
- CSV export of patient treatment history
- Redis caching for performance

## 📄 License
Academic project — Modern Application Development II, IIT Madras.
