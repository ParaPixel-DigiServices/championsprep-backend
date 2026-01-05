# StudyZen Backend API

Production-grade FastAPI backend for StudyZen educational platform with AI-powered learning features.

## 🚀 Tech Stack

- **Framework**: FastAPI 0.115.5 (Modern async Python web framework)
- **Database**: PostgreSQL via Supabase
- **Cache**: Redis
- **Auth**: Supabase Auth + JWT
- **AI**: Google Gemini 2.0
- **Email**: Resend
- **Monitoring**: Sentry
- **Python**: 3.11+

## 📁 Project Structure

```
studyzen-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API route handlers
│   │       ├── dependencies.py # Shared dependencies
│   │       └── router.py       # API router
│   ├── core/
│   │   ├── config.py          # Configuration & settings
│   │   ├── security.py        # Auth & security utilities
│   │   └── errors.py          # Error handlers
│   ├── models/                # Pydantic models & schemas
│   ├── services/              # Business logic layer
│   ├── db/
│   │   ├── supabase.py       # Supabase client
│   │   └── redis.py          # Redis client
│   ├── utils/                # Utility functions
│   └── main.py               # FastAPI application
├── tests/
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
├── alembic/                  # Database migrations
├── scripts/                  # Utility scripts
├── docs/                     # Documentation
├── requirements.txt          # Production dependencies
└── requirements-dev.txt      # Development dependencies
```

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.11 or higher
- PostgreSQL (via Supabase)
- Redis (local or cloud)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/studyzen-backend.git
   cd studyzen-backend
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start development server**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_auth.py

# Run integration tests
pytest tests/integration/
```

## 📝 Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy .

# Run all checks
black . && ruff check . && mypy . && pytest
```

## 🔐 Environment Variables

See `.env.example` for all required environment variables.

Key variables to set:
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `SECRET_KEY` (generate with: `openssl rand -hex 32`)
- `GEMINI_API_KEY`
- `RESEND_API_KEY`
- `REDIS_URL`

## 📚 API Documentation

Once the server is running:
- Interactive API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## 🚢 Deployment

### Production Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Set `DEBUG=false`
- [ ] Generate strong `SECRET_KEY`
- [ ] Configure production database
- [ ] Set up Redis (production instance)
- [ ] Configure CORS for production domain
- [ ] Enable Sentry error tracking
- [ ] Set up SSL/TLS certificates
- [ ] Configure rate limiting
- [ ] Review security settings

### Deploy to Render

```bash
# Build command
pip install -r requirements.txt

# Start command
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 📖 Development Guidelines

1. **Code Style**: Follow PEP 8, use Black for formatting
2. **Type Hints**: Always use type hints
3. **Testing**: Write tests for all new features
4. **Documentation**: Update docs for API changes
5. **Commits**: Use conventional commits format
6. **Branches**: Use feature branches, PR to main

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Write/update tests
4. Run code quality checks
5. Submit pull request

## 📄 License

Private - All Rights Reserved

## 📧 Support

For issues or questions, contact: support@studyzen.com

---

**Built with ❤️ for education**