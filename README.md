# NYU Buildathon Project

**We won the Hackathon!** Check it out: [https://devpost.com/software/flipkit]

## Tech Stack
- **Frontend**: Next.js + TypeScript + Tailwind CSS (deployed on Vercel)
- **Backend**: FastAPI + Python (deployed on Render)
- **Auth**: Clerk
- **Database**: Supabase

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/jun229/nyu_buildathon.git
cd nyu_buildathon
```

### 2. Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env.local
# Ask team lead for environment variables and add them to .env.local
npm run dev
```
Frontend runs at: http://localhost:3000

### 3. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Ask team lead for environment variables and add them to .env
uvicorn app.main:app --reload
```
Backend runs at: http://localhost:8000  

**Never commit `.env` or `.env.local` files to git!**

## Git Workflow

### Starting Work
```bash
# 1. Get latest changes from main
git checkout main
git pull origin main

# 2. Create your feature branch
git checkout -b feature/your-feature-name
```

### While Working
```bash
# Sync with main periodically (every 1-2 hours)
git checkout main
git pull origin main
git checkout feature/your-feature-name
git merge main

# Resolve any conflicts if they appear
```

### Submitting Your Work
```bash
# 1. Commit your changes
git add .
git commit -m "Brief description of what you built"

# 2. Final sync with main
git checkout main
git pull origin main
git checkout feature/your-feature-name
git merge main

# 3. Push your branch
git push origin feature/your-feature-name

# 4. Create a Pull Request on GitHub
```

### After Your PR is Merged
```bash
# Everyone pulls the latest main
git checkout main
git pull origin main

# Delete your old feature branch
git branch -D feature/your-feature-name
```

## Handling Merge Conflicts

If you see a merge conflict:
```bash
# Git will show:
# CONFLICT (content): Merge conflict in filename.py

# 1. Open the conflicted file and look for:
<<<<<<< HEAD
your code here
=======
their code here
>>>>>>> main

# 2. Edit the file: keep what you need, remove the markers
# 3. Save the file, then:
git add .
git commit -m "Resolved merge conflicts"
```

**Tip**: Communicate with your team about who's working on which files to minimize conflicts!

## Communication & Coordination

- **Announce** what you're working on to everyone
- **Avoid** working on the same files simultaneously
- **Merge to main often** - don't let branches live more than a few hours
- **Pull from main frequently** to stay in sync

## Deployment

### Frontend (Vercel)
- Auto-deploys from `main` branch
- View deployment status in Vercel dashboard
- Production URL: [Will be added after first deploy]

### Backend (Render)
- Auto-deploys from `main` branch
- View deployment status in Render dashboard
- Production API URL: [Will be added after first deploy]


