# Developer Guide
## Pass-Man Enterprise Password Management System

**Version**: 1.0  
**Date**: September 2025  
**Stack**: Django 5.x + HTMX + Alpine.js + PostgreSQL + Docker  

---

## 🚀 Welcome to Pass-Man Development!

Selamat datang di tim development Pass-Man! Guide ini akan membantu kamu untuk setup development environment, memahami codebase, dan mulai contributing ke project ini.

### What You'll Learn
- 🛠️ Development environment setup
- 🏗️ Project architecture overview
- 📝 Development workflow
- 🧪 Testing procedures
- 🚀 Deployment process
- 🤝 Contributing guidelines

---

## 📋 Prerequisites

Sebelum memulai, pastikan kamu sudah install tools berikut:

### Required Tools
- **Docker Desktop** (latest version)
- **Git** (2.30+)
- **VS Code** atau IDE favorit
- **Node.js** (18+) untuk frontend tooling
- **Python** (3.11+) untuk local development (optional)

### Recommended VS Code Extensions
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.flake8",
    "bradlc.vscode-tailwindcss",
    "formulahendry.auto-rename-tag",
    "ms-vscode.vscode-json",
    "redhat.vscode-yaml",
    "ms-azuretools.vscode-docker"
  ]
}
```

### System Requirements
- **RAM**: Minimum 8GB (16GB recommended)
- **Storage**: 10GB free space
- **OS**: macOS, Linux, atau Windows dengan WSL2

---

## 🛠️ Development Environment Setup

### 1. Clone Repository
```bash
# Clone the repository
git clone https://github.com/your-org/pass-man.git
cd pass-man

# Create your feature branch
git checkout -b feature/your-feature-name
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

**Environment Variables (.env)**:
```bash
# Django Settings
DEBUG=True
SECRET_KEY=your-super-secret-key-for-development
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database
DB_NAME=passmandb
DB_USER=postgres
DB_PASSWORD=postgres123
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# Email (for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Security (development only)
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
```

### 3. Docker Setup
```bash
# Build and start development environment
docker-compose -f docker-compose.dev.yml up --build

# In another terminal, run migrations
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate

# Create superuser
docker-compose -f docker-compose.dev.yml exec web python manage.py createsuperuser

# Load sample data (optional)
docker-compose -f docker-compose.dev.yml exec web python manage.py loaddata fixtures/sample_data.json
```

### 4. Verify Setup
```bash
# Check if all services are running
docker-compose -f docker-compose.dev.yml ps

# Access the application
# http://localhost:8000 - Main application
# http://localhost:8000/admin - Django admin
# http://localhost:8080 - Mailhog (email testing)
```

### 5. Frontend Development Setup
```bash
# Install Node.js dependencies (for Tailwind CSS)
npm install

# Start Tailwind CSS watcher (in separate terminal)
npm run dev

# Or build for production
npm run build
```

---

## 🏗️ Project Structure Deep Dive

### Directory Overview
```
pass_man/
├── 📁 apps/                    # Django applications
│   ├── 📁 users/              # User management
│   ├── 📁 groups/             # Group management  
│   ├── 📁 passwords/          # Password management
│   ├── 📁 directories/        # Directory organization
│   └── 📁 core/               # Shared utilities
├── 📁 config/                 # Django configuration
├── 📁 templates/              # HTML templates
├── 📁 static/                 # Static files (CSS, JS, images)
├── 📁 media/                  # User uploads
├── 📁 tests/                  # Integration tests
├── 📁 docs/                   # Documentation
├── 📁 fixtures/               # Sample data
├── 📁 scripts/                # Utility scripts
├── 🐳 docker-compose.yml      # Production Docker config
├── 🐳 docker-compose.dev.yml  # Development Docker config
├── 🐳 Dockerfile              # Docker image definition
├── 📦 requirements.txt        # Python dependencies
├── 📦 package.json            # Node.js dependencies
└── 🔧 manage.py               # Django management script
```

### Key Applications

#### 1. Users App (`apps/users/`)
```
users/
├── models.py          # User model dengan custom fields
├── views.py           # Authentication views
├── serializers.py     # API serializers
├── services.py        # Business logic
├── admin.py           # Django admin config
├── urls.py            # URL routing
└── tests/             # Unit tests
```

**Key Models**: `User` (extends AbstractUser)

#### 2. Groups App (`apps/groups/`)
```
groups/
├── models.py          # Group, UserGroup models
├── views.py           # Group management views
├── services.py        # Group business logic
├── permissions.py     # Custom permissions
└── tests/
```

**Key Models**: `Group`, `UserGroup`

#### 3. Passwords App (`apps/passwords/`)
```
passwords/
├── models.py          # Password, PasswordHistory models
├── views.py           # Password CRUD views
├── services.py        # Password business logic
├── encryption.py      # Encryption utilities
├── generators.py      # Password generation
└── tests/
```

**Key Models**: `Password`, `PasswordHistory`, `PasswordShare`

#### 4. Core App (`apps/core/`)
```
core/
├── models.py          # Base models
├── permissions.py     # Custom permissions
├── mixins.py          # View mixins
├── utils.py           # Utility functions
├── exceptions.py      # Custom exceptions
└── validators.py      # Custom validators
```

---

## 🔧 Development Workflow

### 1. Feature Development Process

#### Step 1: Pick a Task
```bash
# Check current backlog
cat docs/BACKLOG.md

# Create feature branch
git checkout -b feature/AUTH-001-user-registration
```

#### Step 2: Development
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up

# Make your changes
# Follow coding standards in docs/CODING_STANDARDS.md

# Run tests frequently
docker-compose -f docker-compose.dev.yml exec web python manage.py test

# Check code quality
docker-compose -f docker-compose.dev.yml exec web flake8 apps/
docker-compose -f docker-compose.dev.yml exec web black apps/
```

#### Step 3: Testing
```bash
# Run all tests
docker-compose -f docker-compose.dev.yml exec web python manage.py test

# Run specific app tests
docker-compose -f docker-compose.dev.yml exec web python manage.py test apps.users

# Run with coverage
docker-compose -f docker-compose.dev.yml exec web coverage run --source='.' manage.py test
docker-compose -f docker-compose.dev.yml exec web coverage report
```

#### Step 4: Code Review
```bash
# Commit your changes
git add .
git commit -m "feat(auth): implement user registration with email verification

- Add user registration form with validation
- Implement email verification workflow
- Add tests for registration process
- Update documentation

Closes #AUTH-001"

# Push to remote
git push origin feature/AUTH-001-user-registration

# Create Pull Request
# Follow PR template in .github/pull_request_template.md
```

### 2. Database Migrations

#### Creating Migrations
```bash
# Create migration after model changes
docker-compose -f docker-compose.dev.yml exec web python manage.py makemigrations

# Create empty migration for data migration
docker-compose -f docker-compose.dev.yml exec web python manage.py makemigrations --empty users

# Apply migrations
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate

# Check migration status
docker-compose -f docker-compose.dev.yml exec web python manage.py showmigrations
```

#### Migration Best Practices
```python
# ✅ Good - Data migration example
from django.db import migrations

def create_default_groups(apps, schema_editor):
    """Create default groups for existing users."""
    User = apps.get_model('users', 'User')
    Group = apps.get_model('groups', 'Group')
    
    for user in User.objects.all():
        if not Group.objects.filter(owner=user).exists():
            Group.objects.create(
                name=f"{user.full_name}'s Personal Vault",
                description="Personal password vault",
                owner=user
            )

def reverse_create_default_groups(apps, schema_editor):
    """Reverse the default groups creation."""
    Group = apps.get_model('groups', 'Group')
    Group.objects.filter(name__endswith="'s Personal Vault").delete()

class Migration(migrations.Migration):
    dependencies = [
        ('groups', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_default_groups,
            reverse_create_default_groups
        ),
    ]
```

### 3. Frontend Development

#### HTMX Development
```html
<!-- Example: Dynamic password list -->
<div id="password-container">
    <!-- Search form -->
    <form hx-get="{% url 'passwords:search' group.id %}"
          hx-target="#password-list"
          hx-trigger="input changed delay:300ms from:#search-input">
        <input type="text" 
               id="search-input"
               name="search"
               placeholder="Search passwords..."
               class="form-input">
    </form>
    
    <!-- Password list -->
    <div id="password-list">
        {% include 'passwords/partials/password_list.html' %}
    </div>
</div>
```

#### Alpine.js Components
```html
<!-- Example: Password item component -->
<div x-data="passwordItem({{ password.id }})" class="password-item">
    <div class="flex justify-between items-center">
        <div>
            <h3 x-text="password.title"></h3>
            <p x-text="password.username" class="text-gray-600"></p>
        </div>
        
        <div class="flex space-x-2">
            <button @click="copyPassword()" 
                    :disabled="copying"
                    class="btn btn-sm">
                <span x-show="!copying">Copy</span>
                <span x-show="copying">Copying...</span>
            </button>
        </div>
    </div>
</div>

<script>
function passwordItem(passwordId) {
    return {
        password: {},
        copying: false,
        
        async init() {
            // Load password data
            const response = await fetch(`/api/passwords/${passwordId}/`);
            this.password = await response.json();
        },
        
        async copyPassword() {
            this.copying = true;
            try {
                const response = await fetch(`/api/passwords/${passwordId}/decrypt/`);
                const data = await response.json();
                await navigator.clipboard.writeText(data.password);
                this.showNotification('Password copied!');
            } catch (error) {
                this.showNotification('Failed to copy password', 'error');
            } finally {
                this.copying = false;
            }
        }
    }
}
</script>
```

#### Tailwind CSS Development
```bash
# Watch for changes (development)
npm run dev

# Build for production
npm run build

# Purge unused CSS
npm run purge
```

---

## 🧪 Testing Guide

### 1. Running Tests

#### All Tests
```bash
# Run all tests
docker-compose -f docker-compose.dev.yml exec web python manage.py test

# Run with verbose output
docker-compose -f docker-compose.dev.yml exec web python manage.py test --verbosity=2

# Run specific test
docker-compose -f docker-compose.dev.yml exec web python manage.py test apps.users.tests.test_models.UserModelTest.test_create_user
```

#### Coverage Reports
```bash
# Install coverage
docker-compose -f docker-compose.dev.yml exec web pip install coverage

# Run tests with coverage
docker-compose -f docker-compose.dev.yml exec web coverage run --source='.' manage.py test

# Generate report
docker-compose -f docker-compose.dev.yml exec web coverage report

# Generate HTML report
docker-compose -f docker-compose.dev.yml exec web coverage html
# Open htmlcov/index.html in browser
```

### 2. Writing Tests

#### Unit Test Example
```python
# apps/passwords/tests/test_services.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.groups.models import Group
from apps.passwords.services import PasswordService
from apps.passwords.models import Password

User = get_user_model()

class PasswordServiceTest(TestCase):
    """Test cases for PasswordService."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        self.group = Group.objects.create(
            name='Test Group',
            owner=self.user
        )
    
    def test_create_password_success(self):
        """Test successful password creation."""
        password_data = {
            'title': 'Test Password',
            'username': 'testuser',
            'password': 'secret123',
            'url': 'https://example.com'
        }
        
        password = PasswordService.create_password(
            self.user, self.group, password_data
        )
        
        self.assertEqual(password.title, 'Test Password')
        self.assertEqual(password.group, self.group)
        self.assertTrue(password.password_encrypted)
    
    def test_create_password_invalid_data(self):
        """Test password creation with invalid data."""
        password_data = {
            'title': '',  # Empty title
            'password': 'secret123'
        }
        
        with self.assertRaises(ValidationError):
            PasswordService.create_password(
                self.user, self.group, password_data
            )
```

#### Integration Test Example
```python
# tests/test_integration.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class PasswordWorkflowTest(TestCase):
    """Integration tests for password workflow."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        self.client.login(email='test@example.com', password='testpass123')
    
    def test_complete_password_workflow(self):
        """Test complete password creation workflow."""
        # 1. Create group
        group_data = {
            'name': 'Test Group',
            'description': 'Test group description'
        }
        response = self.client.post(reverse('groups:create'), group_data)
        self.assertEqual(response.status_code, 302)
        
        group = Group.objects.get(name='Test Group')
        
        # 2. Create password
        password_data = {
            'title': 'Test Password',
            'username': 'testuser',
            'password': 'secret123',
            'url': 'https://example.com'
        }
        response = self.client.post(
            reverse('passwords:create', kwargs={'group_id': group.id}),
            password_data
        )
        self.assertEqual(response.status_code, 200)
        
        # 3. Verify password exists
        password = Password.objects.get(title='Test Password')
        self.assertEqual(password.group, group)
        
        # 4. Test password retrieval
        response = self.client.get(
            reverse('passwords:detail', kwargs={
                'group_id': group.id,
                'password_id': password.id
            })
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Password')
```

### 3. Frontend Testing

#### JavaScript Testing Setup
```bash
# Install Jest and testing utilities
npm install --save-dev jest @testing-library/jest-dom jsdom

# Add to package.json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage"
  },
  "jest": {
    "testEnvironment": "jsdom",
    "setupFilesAfterEnv": ["<rootDir>/tests/frontend/setup.js"]
  }
}
```

#### Frontend Test Example
```javascript
// tests/frontend/password-manager.test.js
import { passwordManager } from '../../static/js/components/password-manager.js';

describe('Password Manager', () => {
    let component;
    
    beforeEach(() => {
        component = passwordManager();
        component.passwords = [
            { id: '1', title: 'Gmail', username: 'test@gmail.com', favorite: false },
            { id: '2', title: 'Facebook', username: 'testuser', favorite: true }
        ];
    });
    
    test('should filter passwords by search query', () => {
        component.searchQuery = 'gmail';
        
        const filtered = component.filteredPasswords;
        
        expect(filtered).toHaveLength(1);
        expect(filtered[0].title).toBe('Gmail');
    });
    
    test('should handle copy password', async () => {
        // Mock clipboard API
        Object.assign(navigator, {
            clipboard: {
                writeText: jest.fn(() => Promise.resolve())
            }
        });
        
        // Mock fetch
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ password: 'secret123' })
            })
        );
        
        await component.copyPassword('1');
        
        expect(navigator.clipboard.writeText).toHaveBeenCalledWith('secret123');
    });
});
```

---

## 🚀 Deployment Guide

### 1. Local Production Testing
```bash
# Build production image
docker build -t pass-man:latest .

# Run production-like environment
docker-compose -f docker-compose.prod.yml up

# Test production build
curl http://localhost/health/
```

### 2. Environment Preparation

#### Production Environment Variables
```bash
# Production .env
DEBUG=False
SECRET_KEY=your-super-secure-production-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=passmandb_prod
DB_USER=passmanuser
DB_PASSWORD=super-secure-db-password
DB_HOST=your-db-host
DB_PORT=5432

# Redis
REDIS_URL=redis://your-redis-host:6379/0

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yourdomain.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=your-email-password

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
```

### 3. CI/CD Pipeline

#### GitHub Actions Workflow
```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_passmandb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run linting
      run: |
        flake8 apps/
        black --check apps/
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_passmandb
        REDIS_URL: redis://localhost:6379/0
      run: |
        python manage.py test
    
    - name: Run security checks
      run: |
        bandit -r apps/
        safety check
    
    - name: Build Docker image
      run: |
        docker build -t pass-man:${{ github.sha }} .
    
    - name: Run integration tests
      run: |
        docker-compose -f docker-compose.test.yml up --abort-on-container-exit
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Deploy to production
      run: |
        echo "Deploy to production server"
        # Add your deployment commands here
```

---

## 🤝 Contributing Guidelines

### 1. Code Contribution Process

#### Before You Start
1. Check existing issues dan backlog
2. Discuss major changes dalam GitHub Discussions
3. Follow coding standards dalam `docs/CODING_STANDARDS.md`
4. Write tests untuk new features

#### Pull Request Process
1. **Branch Naming**: `feature/TASK-ID-short-description`
2. **Commit Messages**: Follow conventional commits
3. **PR Description**: Use PR template
4. **Code Review**: Address all feedback
5. **Testing**: Ensure all tests pass

#### Commit Message Format
```
type(scope): short description

Longer description if needed

- List of changes
- Another change

Closes #TASK-ID
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### 2. Code Review Checklist

#### Security Review
- [ ] Input validation implemented
- [ ] No SQL injection vulnerabilities
- [ ] XSS prevention in place
- [ ] Authentication/authorization checks
- [ ] Sensitive data properly encrypted
- [ ] No hardcoded secrets

#### Code Quality
- [ ] Follows coding standards
- [ ] Proper error handling
- [ ] Meaningful names
- [ ] Adequate documentation
- [ ] No code duplication

#### Testing
- [ ] Unit tests written
- [ ] Integration tests for complex flows
- [ ] Edge cases covered
- [ ] Test coverage > 90%

### 3. Issue Reporting

#### Bug Report Template
```markdown
## Bug Description
Brief description of the bug

## Steps to Reproduce
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior
What you expected to happen

## Actual Behavior
What actually happened

## Environment
- OS: [e.g. macOS 12.0]
- Browser: [e.g. Chrome 95.0]
- Version: [e.g. v1.0.0]

## Additional Context
Add any other context about the problem here
```

#### Feature Request Template
```markdown
## Feature Description
Brief description of the feature

## Problem Statement
What problem does this solve?

## Proposed Solution
How should this feature work?

## Alternatives Considered
What other solutions did you consider?

## Additional Context
Any other context or screenshots
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Docker Issues
```bash
# Container won't start
docker-compose -f docker-compose.dev.yml logs web

# Database connection issues
docker-compose -f docker-compose.dev.yml exec db psql -U postgres -d passmandb

# Reset everything
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up --build
```

#### 2. Migration Issues
```bash
# Reset migrations (development only)
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate users zero
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate

# Fake migration
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate --fake users 0001

# Show migration status
docker-compose -f docker-compose.dev.yml exec web python manage.py showmigrations
```

#### 3. Frontend Issues
```bash
# Tailwind not updating
npm run build

# Clear browser cache
# Use hard refresh (Ctrl+Shift+R)

# Check console for JavaScript errors
# Open browser dev tools
```

#### 4. Permission Issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER .

# Docker permission issues
docker-compose -f docker-compose.dev.yml exec web chown -R app:app /app
```

### Getting Help

#### Internal Resources
1. **Documentation**: Check `docs/` folder
2. **Code Examples**: Look at existing implementations
3. **Tests**: Check test files for usage examples

#### External Resources
1. **Django Documentation**: https://docs.djangoproject.com/
2. **HTMX Documentation**: https://htmx.org/docs/
3. **Alpine.js Documentation**: https://alpinejs.dev/
4. **Tailwind CSS**: https://tailwindcss.com/docs

#### Team Communication
1. **Daily Standups**: Share blockers dan progress
2. **Code Reviews**: Ask questions dalam PR comments
3. **Slack/Discord**: Quick questions dan discussions
4. **GitHub Issues**: Bug reports dan feature requests

---

## 📚 Learning Resources

### Django Development
- [Django Best Practices](https://django-best-practices.readthedocs.io/)
- [Two Scoops of Django](https://www.feldroy.com/books/two-scoops-of-django-3-x)
- [Django Security Best Practices](https://docs.djangoproject.com/en/stable/topics/security/)

### Frontend Development
- [HTMX Examples](https://htmx.org/examples/)
- [Alpine.js Patterns](https://alpinejs.dev/patterns)
- [Tailwind CSS Components](https://tailwindui.com/components)

### Security
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Password Security Best Practices](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

---

## 🎯 Next Steps

Setelah setup development environment, kamu bisa:

1. **Explore Codebase**: Baca existing code untuk understand patterns
2. **Pick First Task**: Pilih task dari backlog yang sesuai skill level
3. **Join Team Meetings**: Participate dalam daily standups
4. **Ask Questions**: Jangan ragu untuk bertanya ke team members
5. **Contribute**: Start dengan small fixes atau improvements

### Recommended First Tasks
- **SETUP-003**: Setup Django project dengan Docker
- **AUTH-001**: Implement user registration
- **UI-001**: Create basic dashboard layout
- **TEST-001**: Add missing unit tests

---

**Welcome to the team! 🎉**

*Happy coding dan jangan lupa untuk always prioritize security dalam setiap code yang kamu tulis!*