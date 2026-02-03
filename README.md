# Community Feed

A Reddit-style community feed with nested comments, likes, karma, and a real-time leaderboard.

## Tech Stack

- **Backend**: Django 5.0 + Django REST Framework
- **Frontend**: React 18 + Tailwind CSS + Vite
- **Database**: PostgreSQL 15
- **Containerization**: Docker + Docker Compose

## Features

- 📝 **Posts** - Create and view posts with like counts
- 💬 **Threaded Comments** - Unlimited nesting depth, efficiently loaded
- ❤️ **Likes** - Like posts (+5 karma) and comments (+1 karma)
- 🏆 **Leaderboard** - Top 5 users by karma in last 24 hours
- 🔒 **Concurrency Safe** - DB constraints prevent double-likes

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git

### 1. Clone and Start

```bash
# Clone the repository
git clone <repository-url>
cd playto

# Start all services
docker compose up
```

This will:
- Start PostgreSQL database
- Run Django migrations automatically
- Start Django backend on http://localhost:8000
- Start React frontend on http://localhost:3000

### 2. Create a Superuser

```bash
# In a new terminal, create an admin user
docker compose exec backend python manage.py createsuperuser
```

Follow the prompts to create your admin account.

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api/
- **Admin Panel**: http://localhost:8000/admin/

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/posts/` | GET | List all posts |
| `/api/posts/` | POST | Create a new post |
| `/api/posts/{id}/` | GET | Get post with comment tree |
| `/api/comments/` | POST | Create a comment |
| `/api/like/` | POST | Like a post or comment |
| `/api/like/` | DELETE | Unlike a post or comment |
| `/api/leaderboard/` | GET | Top 5 users (24h karma) |

## Running Tests

```bash
# Run all tests
docker compose exec backend python manage.py test

# Run specific test file
docker compose exec backend python manage.py test feed.tests.LeaderboardTimeFilterTest

# Run with verbosity
docker compose exec backend python manage.py test -v 2
```

## Development

### Backend Development

```bash
# Enter backend container
docker compose exec backend bash

# Make migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Django shell
python manage.py shell
```

### Frontend Development

```bash
# Enter frontend container
docker compose exec frontend sh

# Install new packages
npm install <package-name>
```

### Database Access

```bash
# PostgreSQL CLI
docker compose exec db psql -U postgres -d community_feed

# Useful queries
\dt                          # List tables
SELECT * FROM feed_post;     # View posts
SELECT * FROM feed_karmatransaction;  # View karma history
```

## Production Deployment

```bash
# Set environment variables
export DJANGO_SECRET_KEY=your-production-secret-key
export POSTGRES_PASSWORD=secure-database-password
export ALLOWED_HOSTS=yourdomain.com

# Start with production overrides
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Project Structure

```
playto/
├── backend/
│   ├── config/           # Django settings
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── feed/             # Main application
│   │   ├── models.py     # Post, Comment, Like, KarmaTransaction
│   │   ├── views.py      # API views
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── tests.py
│   ├── manage.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── utils/        # Helper functions
│   │   ├── api.js        # API client
│   │   └── App.jsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── README.md
└── EXPLAINER.md
```

## Troubleshooting

### Database connection errors

```bash
# Check if database is running
docker compose ps

# Restart just the database
docker compose restart db

# Wait and restart backend
docker compose restart backend
```

### Frontend not loading

```bash
# Check frontend logs
docker compose logs frontend

# Reinstall node modules
docker compose exec frontend rm -rf node_modules
docker compose exec frontend npm install
docker compose restart frontend
```

### Reset everything

```bash
# Stop and remove all containers and volumes
docker compose down -v

# Start fresh
docker compose up --build
```

## License

MIT License
