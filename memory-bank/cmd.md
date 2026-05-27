# 1. Start PostgreSQL
docker run -d --name sqlbot-pg -p 5432:5432 \
  -e POSTGRES_USER=root -e POSTGRES_PASSWORD=Password123@pg -e POSTGRES_DB=sqlbot \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v /Users/cuixianyun/IdeaProjects/sqlboot-plus/SQLBot/data/postgresql:/var/lib/postgresql/data \
  pgvector/pgvector:pg15


# 2 start backend
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 3. Start frontend (terminal 2)
cd frontend
npm install
npm run dev

# 4. test user
admin/SQLBot@123456
