# CLAUDE.md - Pass-Man Project Instructions

## 🚨 IMPORTANT: Containerized Application

**Pass-Man adalah FULLY CONTAINERIZED application.** Semua operasi development, testing, dan management commands WAJIB dijalankan melalui Docker container yang didefinisikan dalam [`pass_man/docker-compose.dev.yml`](pass_man/docker-compose.dev.yml).

Docker Compose configuration:
- **Development**: [`pass_man/docker-compose.dev.yml`](pass_man/docker-compose.dev.yml) - Environment development lengkap dengan PostgreSQL, Redis, dan Mailhog
- **Production**: `pass_man/docker-compose.yml` - Production deployment

Services yang tersedia dalam container:
- **web** - Django application container
- **db** - PostgreSQL database (port 15432 di host)
- **redis** - Redis cache (port 16379 di host)
- **mailhog** - Email testing (port 18025 untuk web UI)
- **nginx** - Static files server (optional, port 18080)

## Project Context
Pass-Man adalah **Enterprise Password Management System** yang dibangun dengan Django + HTMX + Alpine.js + PostgreSQL. Seluruh aplikasi di-dockerize untuk konsistensi di development dan production.

## Directory Structure
- `docs/` - Dokumentasi teknis proyek (SRS, PRD, Architecture, dll)
- `pass_man/` - Aplikasi Django utama

## Docker-Centric Development Environment

### Container Access Pattern

**🚨 CRITICAL: ALL commands MUST be executed via Docker container.**

JANGAN menjalankan perintah Python/Django langsung di host machine. Selalu gunakan `docker-compose` dengan flag `-f` untuk menentukan file konfigurasi yang benar:

```bash
# Dari root direktori pass_man/
docker-compose -f pass_man/docker-compose.dev.yml exec web <command>

# Masuk ke container web
docker-compose -f pass_man/docker-compose.dev.yml exec web bash

# Django management commands
docker-compose -f pass_man/docker-compose.dev.yml exec web python manage.py <command>
```

**Working directory**: Semua perintah docker-compose harus dijalankan dari root direktori proyek (tempat `pass_man/` folder berada), bukan dari dalam `pass_man/` directory.

### Common Development Commands

#### Environment Setup
```bash
# Build dan start development environment (dari root proyek)
docker-compose -f pass_man/docker-compose.dev.yml up --build

# Stop semua services
docker-compose -f pass_man/docker-compose.dev.yml down

# Hapus volumes (reset database)
docker-compose -f pass_man/docker-compose.dev.yml down -v
```

#### Database Operations
```bash
# Run migrations
docker-compose -f pass_man/docker-compose.dev.yml exec web python manage.py migrate

# Create migrations
docker-compose -f pass_man/docker-compose.dev.yml exec web python manage.py makemigrations

# Create superuser
docker-compose -f pass_man/docker-compose.dev.yml exec web python manage.py createsuperuser

# Reset database (development only)
docker-compose -f pass_man/docker-compose.dev.yml exec web python manage.py flush
```

#### Development Server
```bash
# Start development (already running dengan up command)
# Access di http://localhost:18000

# View logs
docker-compose -f pass_man/docker-compose.dev.yml logs -f web
```

#### Testing
```bash
# Run all tests
docker-compose -f pass_man/docker-compose.dev.yml exec web python manage.py test

# Run specific app tests
docker-compose -f pass_man/docker-compose.dev.yml exec web python manage.py test apps.users

# Run with coverage
docker-compose -f pass_man/docker-compose.dev.yml exec web coverage run --source='.' manage.py test
docker-compose -f pass_man/docker-compose.dev.yml exec web coverage report
```

#### Code Quality
```bash
# Linting
docker-compose -f pass_man/docker-compose.dev.yml exec web flake8 apps/

# Format code
docker-compose -f pass_man/docker-compose.dev.yml exec web black apps/

# Sort imports
docker-compose -f pass_man/docker-compose.dev.yml exec web isort apps/
```

#### Static Files & Frontend
```bash
# Collect static files
docker-compose -f pass_man/docker-compose.dev.yml exec web python manage.py collectstatic --noinput

# Build Tailwind (run di host dari pass_man/ directory)
npm run build

# Watch Tailwind changes (run di host dari pass_man/ directory)
npm run dev
```

## Project Specific Guidelines

### Architecture Patterns
- **Django Apps Structure**: `users`, `groups`, `passwords`, `directories`, `core`
- **HTMX for dynamic interactions** - gunakan partial templates
- **Alpine.js untuk client-side reactivity**
- **Encryption**: Password di-encrypt per-group menggunakan Fernet

### Security First Approach
```python
# Encryption pattern
from apps.passwords.services import PasswordEncryptionService

# Encrypt password
encrypted = PasswordEncryptionService.encrypt_password(password, group_id)

# Decrypt password
decrypted = PasswordEncryptionService.decrypt_password(encrypted, group_id)
```

### HTMX Integration Pattern
```html
<!-- Search dengan HTMX -->
<form hx-get="{% url 'passwords:list' group.id %}"
      hx-target="#password-list"
      hx-trigger="input changed delay:300ms">
    <input type="text" name="search" placeholder="Search...">
</form>
```

### Alpine.js Component Pattern
```html
<div x-data="passwordManager()">
    <button @click="copyPassword(password.id)"
            :disabled="copying"
            x-text="copying ? 'Copying...' : 'Copy'">
    </button>
</div>
```

## Code Style & Standards

### Django Models
```python
# Gunakan UUID primary keys
class Password(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    # ... fields

    class Meta:
        indexes = [
            models.Index(fields=['group', '-updated_at']),
        ]
```

### Services Layer
- Business logic di services, bukan di views
- Encryption logic di dedicated service
- Validation di models & serializers

### Views Pattern
- Gunakan HTMX headers untuk partial responses
- Permission checks di awal function
- Generic views untuk CRUD sederhana

## File Location Guidelines

### Models
`apps/<appname>/models.py`

### Services
`apps/<appname>/services.py`

### Views
`apps/<appname>/views.py`

### Templates
- Main: `templates/<appname>/<template_name>.html`
- Partials: `templates/<appname>/partials/<partial_name>.html`

### Static Files
- CSS: `static/css/`
- JS: `static/js/components/`
- Images: `static/img/`

## Common Tasks

### Create New Django App
```bash
docker-compose -f pass_man/docker-compose.dev.yml exec web python manage.py startapp newapp apps/
```

### Add New Model
1. Edit `apps/<app>/models.py`
2. Create migration: `docker-compose -f pass_man/docker-compose.dev.yml exec web python manage.py makemigrations`
3. Apply migration: `docker-compose -f pass_man/docker-compose.dev.yml exec web python manage.py migrate`

### Create New View
1. Edit `apps/<app>/views.py`
2. Add URL di `apps/<app>/urls.py`
3. Create template jika needed

### API Endpoints
- Gunakan Django REST Framework
- Serializers di `apps/<app>/serializers.py`
- API URLs di `apps/<app>/api_urls.py`

## Environment Variables
Development configuration di `.env`:
```bash
DEBUG=True
SECRET_KEY=<development-key>
DB_NAME=passmandb
DB_USER=postgres
DB_PASSWORD=postgres123
DB_HOST=db
DB_PORT=5432
REDIS_URL=redis://redis:6379/0
```

## Production Deployment
Gunakan `pass_man/docker-compose.yml`:
```bash
# Masuk ke pass_man directory dulu
cd pass_man

# Production build
docker-compose up --build -d

# Run migrations di production
docker-compose exec web python manage.py migrate
```

## Troubleshooting

### Container Issues
```bash
# View container logs
docker-compose -f pass_man/docker-compose.dev.yml logs web

# Restart container
docker-compose -f pass_man/docker-compose.dev.yml restart web

# Rebuild jika ada changes
docker-compose -f pass_man/docker-compose.dev.yml up --build
```

### Database Issues
```bash
# Connect ke database container
docker-compose -f pass_man/docker-compose.dev.yml exec db psql -U postgres -d passmandb

# Reset migrations (development only)
docker-compose -f pass_man/docker-compose.dev.yml exec web python manage.py migrate <app> zero
```

### Static Files Issues
```bash
# Clear static files
docker-compose -f pass_man/docker-compose.dev.yml exec web python manage.py collectstatic --clear --noinput

# Rebuild static assets
npm run build
```

---

**🚨 IMPORTANT**: Selalu gunakan Docker container untuk semua operasi development. Jangan install Python dependencies atau database di host machine. Semua perintah Django/Python harus dijalankan melalui `docker-compose -f pass_man/docker-compose.dev.yml exec web ...` dari root direktori proyek.