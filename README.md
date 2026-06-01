# LibroVault 📚

A personal book tracking web app powered by the Google Books API. Search millions of books, build your personal library, track reading progress, and discover what's popular among other readers.

---

## Features

- **Google Books search** — query the Google Books API and add any book to your library in one click
- **Manual book entry** — add books not on Google Books with a custom form
- **Reading tracker** — log pages read; status auto-updates to `Completed` when you finish
- **Library management** — filter your collection by status (Reading, Completed, Wishlist), sort by title or date added, and toggle favourites
- **Popular books** — see which books other users have added most
- **User profiles** — profile picture (Cloudinary), bio, update username/email
- **Auth** — register, login, logout, and full password reset via email
- **Smart update forms** — Google Books entries only expose the `status` field for editing; manual entries expose full fields

---

## Tech Stack

- **Backend** — Django 4.x
- **Database** — SQLite (local) / PostgreSQL (production)
- **External API** — Google Books API
- **Media storage** — Cloudinary (profile pictures, with auto-crop and face detection)
- **Static files** — WhiteNoise
- **Frontend** — Django templates + Crispy Forms (Bootstrap 4)
- **Deployment** — Render

---

## Project Structure

```
django_practice/
├── bookcollection/          # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── library/                 # Core app — books, search, reading tracker
│   ├── models.py            # Book, BookLink
│   ├── views.py
│   ├── forms.py             # BookCreateForm, BookUpdateForm
│   ├── utils.py             # Google Books API query + save logic
│   └── urls.py
├── users/                   # Auth + user data
│   ├── models.py            # Profile, UserBook, UserFollow
│   ├── views.py
│   └── forms.py             # Registration, login, profile update
├── tests/
├── media/                   # Local media (dev only)
├── profile_pics/
├── .env
├── .gitignore
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
- PostgreSQL (production only)

### Setup

```bash
# Clone the repo
git clone https://github.com/your-username/librovault.git
cd librovault

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Fill in the values below

# Apply migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Run the dev server
python manage.py runserver
```

### Environment Variables

```env
SECRET_KEY=your-django-secret-key
DEBUG=True

GOOGLE_API_KEY=your-google-books-api-key

CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-cloudinary-api-key
CLOUDINARY_API_SECRET=your-cloudinary-api-secret

# Email (password reset)
EMAIL_ADDRESS=your-gmail-address
EMAIL_PASSWORD=your-gmail-app-password

# Production only (PostgreSQL on Render)
DATABASE_URL=your-render-postgres-url
```

> **Local dev** uses SQLite by default — no DB setup needed. Set `DATABASE_URL` only for production.

---

## URL Routes

| Method | URL | View | Description |
|--------|-----|------|-------------|
| GET | `/` | `homepage` | Landing page or redirect to library |
| GET | `/home/` | `BookListView` | User's library dashboard |
| GET | `/user/` | `book_view_status_filter` | Book collection with filters + sorting |
| GET | `/book/explore/` | `book_query` | Search Google Books |
| POST | `/book/add/` | `add_book` | Add a Google Books result to library |
| GET/POST | `/book/new/` | `BookCreateView` | Manually add a book |
| GET | `/book/<pk>/` | `BookDetailView` | Book detail page |
| GET/POST | `/book/<pk>/update/` | `BookUpdateView` | Update book / reading status |
| POST | `/book/<pk>/delete/` | `UserBookDeleteView` | Remove book from library |
| POST | `/book/pageupdate/<pk>/` | `update_book_page` | Log pages read |
| POST | `/book/favourite/<pk>/` | `favourite_toggle` | Toggle favourite |
| GET/POST | `/register/` | `register` | User registration |
| GET/POST | `/login/` | Django `LoginView` | Login |
| GET | `/logout/` | Django `LogoutView` | Logout |
| GET/POST | `/profile/` | `profile` | Update profile info + avatar |
| GET | `/account/` | `account` | Account info page |

---

## Roadmap

- [ ] Social features — follow users, see friends' libraries
- [ ] Reading statistics and charts
- [ ] Open Library / Internet Archive as additional book sources
- [ ] Book reviews and ratings
- [ ] Public/private library visibility
- [ ] REST API (DRF)

---

## License

Apache 2.0