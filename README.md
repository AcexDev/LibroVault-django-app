# LibroVault API 📚

A personal book tracking REST API powered by the Google Books API. Search millions of books, build your personal library, track reading progress, and discover what's popular among other readers.

JSON in, JSON out — bring your own frontend.

---

## Features

- **Multi-source book search** — search Google Books, Open Library, or Internet Archive and add results to your library
- **Manual book entry** — add books not on Google Books
- **Reading tracker** — log pages read; status auto-updates to `completed` when you finish
- **Reading statistics** — track pages read and books finished, with a 30-day page activity chart
- **Library management** — filter your collection by status (`reading`, `completed`, `wishlist`), sort by title or date added, and toggle favourites
- **Popular books** — see which books other users have added most
- **Community** — discover readers, follow them, browse their libraries, and see recent shelf additions
- **Library visibility** — share with everyone, your followers, or mutual follows
- **Notifications** — get in-app alerts for new followers and books completed by readers you follow
- **User profiles** — profile picture (Cloudinary), bio, and email-based accounts
- **Auth** — JWT email/password login, Google and GitHub social login, plus password reset by email
- **Source-aware updates** — Google Books entries only expose `status` for editing; manual entries expose the full field set

---

## Tech Stack

- **Backend** — Django 6 + Django REST Framework
- **Frontend** — React + Vite, maintained as a separate app under `frontend/`
- **Auth** — `djangorestframework-simplejwt` (access/refresh tokens, refresh rotation + blacklist)
- **Database** — PostgreSQL (SQLite available locally via `USE_SQLITE=1`)
- **Cache and workers** — Redis + Celery (in-memory cache and eager tasks for simple local runs)
- **External API** — Google Books API
- **Media storage** — Cloudinary (profile pictures, with auto-crop and face detection)
- **CORS** — `django-cors-headers`
- **Filtering** — `django-filter`
- **API documentation** — OpenAPI 3 schema, Swagger UI, and ReDoc (`drf-spectacular`)
- **Static files** — WhiteNoise (admin + DRF browsable API)
- **Deployment** — Render

---

## Project Structure

```
django_practice/
├── frontend/                # Separate React app that consumes the API
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── bookcollection/          # Django project config
│   ├── settings.py          # DRF, SimpleJWT, CORS config
│   ├── celery.py            # Celery app and task discovery
│   ├── urls.py              # /admin/, /api/ + API root index
│   ├── asgi.py
│   └── wsgi.py
├── library/                 # Core app — books, search, reading tracker
│   ├── models.py            # Book, BookLink
│   ├── serializers.py
│   ├── views.py             # BookViewSet, LibraryViewSet, DashboardView
│   ├── filters.py           # status / favourite / sort query params
│   ├── utils.py             # Google Books query + save logic
│   ├── urls.py              # DRF router
│   └── tests.py
├── users/                   # Auth + user data
│   ├── models.py            # Profile, UserBook, UserFollow
│   ├── tasks.py             # Background email delivery
│   ├── serializers.py
│   ├── views.py             # register, JWT login/logout, me, password reset
│   ├── urls.py
│   └── tests.py
├── .env.example
├── build.sh
├── requirements.txt
└── manage.py
```

---

## Data Models

```
Book ──< UserBook ──> User
  |
  └── BookLink (Google Books URL)

User ──── Profile (bio, avatar)
User ──< UserFollow ──> User
```

- `Book` — shared across all users; sourced from Google Books or added manually. `unique_together` on `(title, author)`
- `UserBook` — join table between a `User` and a `Book`; holds `status`, `pages_read`, `favourite`, `added_at`. `unique_together` on `(user, book)`
- `Profile` — extends `User` with bio and Cloudinary profile picture (auto-cropped, face gravity)
- `BookLink` — stores the Google Books info URL for a book
- `UserFollow` — follower/following relationship between users (groundwork for social features)

---

## Getting Started

### Prerequisites

- Python 3.10+
- A [Google Books API key](https://developers.google.com/books/docs/v1/using#APIKey)
- A [Cloudinary](https://cloudinary.com/) account
- PostgreSQL (or `USE_SQLITE=1` for local development)

### Setup

```bash
# Clone the repo
git clone https://github.com/AcexDev/librovault.git
cd librovault

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Fill in the values

# Apply migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Run the dev server
python manage.py runserver
```

In a second terminal, start the frontend:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

The frontend runs at `http://localhost:3000` and calls the backend at
`http://localhost:8000/api`. Make sure `CORS_ALLOWED_ORIGINS` in the backend
environment includes `http://localhost:3000`.

To enable Google sign-in, set `GOOGLE_OAUTH_CLIENT_ID` in the backend `.env`
and the same value as `VITE_GOOGLE_CLIENT_ID` in `frontend/.env`. The Google
Identity Services web client must allow the frontend's origin. GitHub sign-in
is available through `POST /api/auth/social/` using a GitHub OAuth access token
with `read:user` and `user:email` scopes.

`GET /api/` returns an index of the entry points. With `DEBUG=True` the DRF browsable API is available in a browser, and `/api-auth/login/` gives you a session for it.

### Redis and background workers

External book search responses are cached for one hour by default. Open Library
and Internet Archive requests include a descriptive application `User-Agent`;
set `BOOKS_API_CONTACT_EMAIL` to a monitored contact address for Open Library.
Searches are per-user queries, not bulk catalog harvesting. Password reset
emails run as Celery tasks. A basic local run uses in-memory caching and
synchronous tasks; set `REDIS_URL` and `CELERY_BROKER_URL` to use Redis.

For a local Redis, API, and worker stack, copy `.env.example` to `.env`, fill in
the required values, then run:

```bash
docker compose up --build
```

The API is served at `http://localhost:8000`; the worker consumes queued email
tasks. In production, set `REDIS_URL` and `CELERY_BROKER_URL` to your Redis
service and run a Celery worker alongside the Django web process:

```bash
celery -A bookcollection worker --loglevel=info
```

Interactive API documentation is available at `/api/docs/` (Swagger UI), with
the OpenAPI schema at `/api/schema/` and ReDoc at `/api/redoc/`. In Swagger UI,
use **Authorize** to enter a JWT access token as `Bearer <token>` before trying
authenticated endpoints.

### Running tests

```bash
USE_SQLITE=1 python manage.py test
```

---

## Authentication

All endpoints require a bearer token except registration, login, token refresh, password reset, and the read-only book endpoints (`list`, `retrieve`, `popular`, `search`, `meta`).

```bash
# 1. Get a token pair
curl -X POST http://localhost:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email": "ada@example.com", "password": "your-password"}'

# 2. Send the access token on subsequent requests
curl http://localhost:8000/api/dashboard/ \
  -H 'Authorization: Bearer <access-token>'
```

Access tokens last 60 minutes, refresh tokens 7 days. Refreshing rotates the refresh token and blacklists the old one, so store the new value each time.

---

## API Routes

### Auth — `/api/auth/`

| Method | URL | Body | Description |
|--------|-----|------|-------------|
| POST | `register/` | `email`, `password`, `password2`, optional `first_name`, `last_name` | Create an account |
| POST | `login/` | `email`, `password` | Access + refresh tokens and the user |
| POST | `social/` | `provider`, `token` | Sign in with a Google ID token or GitHub access token |
| POST | `refresh/` | `refresh` | New access token |
| POST | `verify/` | `token` | Check a token is valid |
| POST | `logout/` | `refresh` | Blacklist a refresh token |
| GET | `me/` | — | Signed-in user with profile |
| PATCH | `me/` | `username`, `email`, `first_name`, `last_name`, `bio`, `image`, `library_visibility` | Update account and profile (all optional) |
| POST | `password-reset/` | `email` | Email a reset link to `FRONTEND_URL/reset-password/<uid>/<token>` |
| POST | `password-reset/confirm/` | `uid`, `token`, `new_password` | Set a new password |

`PATCH me/` accepts `multipart/form-data` when uploading an `image`.
`library_visibility` accepts `everyone`, `followers`, or `mutuals`.

### Books — `/api/books/`

The shared catalogue. Reads are public.

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/books/` | Paginated catalogue. Supports `?search=`, `?genre=`, `?source=`, `?ordering=` |
| POST | `/api/books/` | Add a book manually; also creates your library entry (requires `status`) |
| GET | `/api/books/{id}/` | Book detail, plus your `pages_read` and `library_entry` when signed in |
| PATCH | `/api/books/{id}/` | Update a book you hold. `source: Manual` → full edit; otherwise `status` only |
| GET | `/api/books/popular/` | Ten most widely held books with `book_count` (excludes manual additions) |
| GET | `/api/books/search/` | Search one provider. `?q=`, `?source=google\|openlib\|archive`, and `?startIndex=` |
| POST | `/api/books/add/` | Add a search result to the catalogue and your library as `wishlist` |
| GET | `/api/books/meta/` | Genre, source, status and sort choices |

`GET /api/books/search/` returns normalized results from the selected provider
alongside paging offsets. Google Books remains the default source. Open Library
searches use its work search API; Internet Archive searches are limited to text
items. Their source links open the provider's own page, where reading or lending
availability is determined by that provider and the specific item.

Each result has `source` and `external_id`. The add endpoint stores these as
provider-specific links while keeping a single LibroVault book entry when an
ISBN or title/author already matches:

```json
{
  "query": "dune",
  "source": "google",
  "source_display": "Google Books",
  "count": 40,
  "start_index": 0,
  "next_index": 40,
  "prev_index": 0,
  "results": [
    {
      "google_id": "B1hSG45JCX4C",
      "external_id": "B1hSG45JCX4C",
      "source": "google",
      "title": "Dune",
      "subtitle": "A novel",
      "authors": "Frank Herbert",
      "isbn": "9780441013593",
      "cover": "https://…",
      "categories": "Fiction",
      "description": "…",
      "link": "https://…",
      "viewability": "PARTIAL",
      "page_count": 412,
      "published_year": 1965
    }
  ]
}
```

A result object from `results` can be POSTed straight to `/api/books/add/`.

### Library — `/api/library/`

Your own collection. Entries are addressed by **book id**, so the same id works against `/api/books/`.

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/library/` | Your entries. Supports `?status=`, `?favourite=`, `?sort=` |
| GET | `/api/library/{book_id}/` | One entry |
| PATCH | `/api/library/{book_id}/` | Update `status`, `pages_read` or `favourite` |
| DELETE | `/api/library/{book_id}/` | Remove the book from your library (the catalogue entry stays) |
| POST | `/api/library/{book_id}/progress/` | `{"pages_read": n}` — sets `completed` at the last page, `reading` below it |
| POST | `/api/library/{book_id}/favourite/` | Toggle favourite |

`?sort=` accepts `title_asc`, `title_desc`, `date_old`, `date_new`. Default order is newest added first.

### Dashboard — `/api/dashboard/`

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/dashboard/` | `book_count`, `favourites_count`, `reading_count`, `books`, `popular_books` |
| GET | `/api/auth/community/` | Suggested readers, followed readers, and recent additions from your circle |
| GET | `/api/auth/community/readers/{id}/` | Reader profile and public library |
| POST | `/api/auth/community/readers/{id}/` | Follow a reader |
| DELETE | `/api/auth/community/readers/{id}/` | Unfollow a reader |
| GET | `/api/auth/notifications/` | Recent notifications and `unread_count` |
| POST | `/api/auth/notifications/{id}/read/` | Mark one notification read |
| POST | `/api/auth/notifications/read-all/` | Mark all notifications read |

---

## Management Commands

Backfill helpers that call Google Books for existing rows:

```bash
python manage.py assign_google_id
python manage.py assign_booklinks
python manage.py assign_pageCounts
python manage.py assign_publishedYears
```

---

## Roadmap

- [x] Community — discover and follow readers, browse their libraries, and view a followed-reader activity feed
- [x] Reading statistics and charts
- [x] Open Library / Internet Archive as additional book sources
- [ ] Book reviews and ratings
- [x] Library visibility — choose whether everyone, followers, or mutual follows can view your books
- [x] OpenAPI schema + Swagger UI

---

## License

Apache 2.0
