# Hackathon Project

## Tech Stack
- Frontend: Next.js + TypeScript + Tailwind (Vercel)
- Backend: FastAPI + Python (Render)
- Auth: Clerk
- Database: Supabase

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env.local
# Fill in .env.local with actual keys
npm run dev
```

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with actual keys
uvicorn app.main:app --reload
```

## Project Structure
```
├── frontend/          # Next.js app
│   ├── app/          # App router
│   ├── components/   # React components
│   └── lib/          # Utilities
├── backend/          # FastAPI app
│   └── app/
│       ├── main.py   # Entry point
│       └── routers/  # API routes
└── README.md
```

## Development Workflow

1. Pull latest: `git pull origin main`
2. Create feature branch: `git checkout -b feature/your-feature`
3. Make changes, test locally
4. Commit: `git add . && git commit -m "description"`
5. Push: `git push origin feature/your-feature`
6. Create PR on GitHub

## Deployment

- **Frontend**: Auto-deploys from `main` via Vercel
- **Backend**: Auto-deploys from `main` via Render