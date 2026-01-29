# AI News Aggregator

An Agentic RAG (Retrieval-Augmented Generation) application that aggregates AI news from email newsletters, deduplicates using vector embeddings, and generates blog posts on demand.

## Architecture

### Three Agents

1. **Collector Agent**: Gmail integration, email parsing, link extraction
2. **Analyst Agent**: Playwright scraping, Vertex AI embeddings, pgvector deduplication, clustering
3. **Creator Agent**: Gemini 1.5 Pro blog generation, Imagen 3 header images

### Tech Stack

| Component | Technology | Local Dev | GCP Production |
|-----------|------------|-----------|----------------|
| Backend | Django + DRF + Celery | Docker | Cloud Run |
| Frontend | Next.js 14 (App Router) | Docker | Cloud Run |
| Database | PostgreSQL + pgvector | Docker | Cloud SQL |
| Queue | Celery + Redis | Docker | Cloud Memorystore |
| LLM | Gemini 1.5 Pro | Vertex AI SDK | Vertex AI |
| Embeddings | text-embedding-004 | Vertex AI SDK | Vertex AI |
| Auth | Google OAuth2 | Local OAuth | Identity Platform |

## Project Structure

```
/ai-news-aggregator
├── /backend                    # Django + DRF + Celery
│   ├── /config                 # Django settings
│   ├── /apps
│   │   ├── /core              # User model, utilities
│   │   ├── /emails            # Collector agent
│   │   ├── /articles          # Analyst agent
│   │   ├── /clusters          # Topic clustering
│   │   ├── /generation        # Creator agent
│   │   └── /api               # DRF viewsets
│   └── /services              # Business logic
├── /frontend                   # Next.js 14
│   ├── /app                   # App Router pages
│   ├── /components            # UI components
│   └── /lib                   # API client, utilities
├── /infra                      # Terraform
└── /docker                     # Docker Compose
```

## Local Development

### Prerequisites

- Docker and Docker Compose
- Node.js 20+
- Python 3.12+
- Google Cloud SDK (for Vertex AI)

### Setup

1. Clone the repository:
```bash
cd ai-news-aggregator
```

2. Copy environment files:
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

3. Configure environment variables in both `.env` files.

4. Start all services:
```bash
cd docker
docker compose up
```

5. Run migrations:
```bash
docker compose exec backend python manage.py migrate
```

6. Create a superuser:
```bash
docker compose exec backend python manage.py createsuperuser
```

### Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api/
- **Admin Panel**: http://localhost:8000/admin/

## Google Cloud Setup

### Prerequisites

1. Create a GCP project
2. Enable billing
3. Set up OAuth consent screen in Google Cloud Console

### Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  aiplatform.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  compute.googleapis.com \
  vpcaccess.googleapis.com \
  gmail.googleapis.com
```

### OAuth Setup

1. Go to Google Cloud Console > APIs & Services > Credentials
2. Create OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URIs:
   - `http://localhost:8000/api/auth/google/callback/`
   - `http://localhost:8000/api/auth/gmail/callback/`
   - `https://your-domain.com/api/auth/google/callback/`
   - `https://your-domain.com/api/auth/gmail/callback/`

### Gmail Label

Create a label called `AI-News` in your Gmail account to filter newsletters.

## Deployment

### Using Terraform

1. Navigate to terraform directory:
```bash
cd infra/terraform
```

2. Initialize Terraform:
```bash
terraform init
```

3. Create a `terraform.tfvars` file with your configuration.

4. Plan and apply:
```bash
terraform plan
terraform apply
```

### Using Cloud Build

Push to your repository to trigger automatic builds:
```bash
git push origin main
```

## API Endpoints

### Authentication
- `GET /api/auth/google/` - Start Google OAuth flow
- `GET /api/auth/gmail/` - Connect Gmail account
- `GET /api/auth/me/` - Get current user
- `POST /api/auth/logout/` - Log out

### Emails (Collector)
- `GET /api/emails/` - List newsletter emails
- `POST /api/emails/sync/` - Trigger Gmail sync

### Articles (Analyst)
- `GET /api/articles/` - List articles
- `GET /api/articles/{id}/` - Article details
- `POST /api/articles/{id}/rescrape/` - Re-scrape article
- `GET /api/articles/similar/?article_id={id}` - Find similar articles

### Clusters
- `GET /api/clusters/` - List topic clusters
- `GET /api/clusters/{id}/` - Cluster details
- `GET /api/clusters/{id}/articles/` - Articles in cluster
- `POST /api/clusters/{id}/generate_summary/` - Generate AI summary

### Blog Posts (Creator)
- `GET /api/posts/` - List blog posts
- `POST /api/posts/generate/` - Generate new post from cluster
- `POST /api/posts/{id}/publish/` - Publish post
- `POST /api/posts/{id}/generate_image/` - Generate header image

## Deduplication Logic

The Analyst Agent uses cosine similarity on embeddings:

- **>0.95 similarity**: Same article (merge as duplicate)
- **>0.85 similarity**: Same topic (cluster together)
- **<0.85 similarity**: New topic (create new cluster)

## Environment Variables

### Backend

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID |
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth client secret |
| `ENCRYPTION_KEY` | Key for encrypting OAuth tokens |
| `GMAIL_NEWSLETTER_LABEL` | Gmail label for newsletters |

### Frontend

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL |
| `NEXTAUTH_SECRET` | NextAuth secret |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |

## License

MIT
