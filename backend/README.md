# GraphMind – Backend API

A FastAPI backend for the GraphMind RAG chatbot, adding multi-turn conversations,
user authentication, and persistent conversation history.

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure .env
```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/graphmind
SECRET_KEY=<random secret>
GOOGLE_CLIENT_ID=<optional>
GOOGLE_CLIENT_SECRET=<optional>
FRONTEND_URL=http://localhost:5173
```

### 3. Create the PostgreSQL database
```sql
CREATE DATABASE graphmind;
```

### 4. Run the server
```bash
uvicorn backend.main:app --reload --port 8000
```
Tables are auto-created. Visit http://localhost:8000/docs for Swagger UI.
