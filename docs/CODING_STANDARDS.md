# Coding Standards & Best Practices
## Pass-Man Development Guidelines

**Version**: 1.0  
**Date**: September 2025  
**Stack**: Django + HTMX + Alpine.js + PostgreSQL  

---

## 🎯 Overview

Dokumen ini mendefinisikan coding standards, best practices, dan conventions yang harus diikuti dalam pengembangan Pass-Man. Tujuannya adalah memastikan code quality, consistency, maintainability, dan security di seluruh codebase.

### Core Principles
- **Security First**: Setiap code harus mempertimbangkan security implications
- **Readability**: Code harus mudah dibaca dan dipahami
- **Consistency**: Mengikuti conventions yang telah ditetapkan
- **Performance**: Optimized untuk speed dan efficiency
- **Testability**: Code harus mudah di-test

---

## 🐍 Python & Django Standards

### 1. Code Style & Formatting

#### PEP 8 Compliance
```python
# ✅ Good
def create_password(user, group, password_data):
    """Create new password entry with encryption."""
    if not password_data.get('title'):
        raise ValueError("Password title is required")
    
    encrypted_password = encrypt_password(
        password_data['password'], 
        str(group.id)
    )
    
    return Password.objects.create(
        title=password_data['title'],
        password_encrypted=encrypted_password,
        group=group,
        created_by=user
    )

# ❌ Bad
def createPassword(user,group,passwordData):
    if not passwordData.get('title'):raise ValueError("Password title is required")
    encryptedPassword=encryptPassword(passwordData['password'],str(group.id))
    return Password.objects.create(title=passwordData['title'],password_encrypted=encryptedPassword,group=group,created_by=user)
```

#### Import Organization
```python
# ✅ Good - Organized imports
# Standard library
import uuid
import hashlib
from datetime import datetime

# Third-party
from django.db import models
from django.contrib.auth.models import AbstractUser
from cryptography.fernet import Fernet

# Local imports
from apps.core.models import BaseModel
from apps.core.utils import generate_key

# ❌ Bad - Unorganized imports
from apps.core.models import BaseModel
import uuid
from django.db import models
from cryptography.fernet import Fernet
import hashlib
```

### 2. Django Best Practices

#### Model Design
```python
# ✅ Good - Proper model design
class Password(BaseModel):
    """Password entry model with encryption support."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, help_text="Password entry title")
    username = models.CharField(max_length=255, blank=True)
    password_encrypted = models.TextField(help_text="AES-256 encrypted password")
    
    # Foreign keys with proper related_name
    group = models.ForeignKey(
        'groups.Group', 
        on_delete=models.CASCADE,
        related_name='passwords'
    )
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='created_passwords'
    )
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['group', '-updated_at']),
            models.Index(fields=['title']),
        ]
        verbose_name = "Password Entry"
        verbose_name_plural = "Password Entries"
    
    def __str__(self):
        return f"{self.title} ({self.group.name})"
    
    def clean(self):
        """Custom validation."""
        if not self.title.strip():
            raise ValidationError("Title cannot be empty")

# ❌ Bad - Poor model design
class Password(models.Model):
    title = models.CharField(max_length=255)
    password = models.TextField()  # Not encrypted!
    group_id = models.IntegerField()  # Should use ForeignKey
    user_id = models.IntegerField()   # Should use ForeignKey
```

#### View Design
```python
# ✅ Good - Class-based view with proper structure
class PasswordListView(LoginRequiredMixin, View):
    """List passwords in a group with search functionality."""
    
    def get(self, request, group_id):
        group = self.get_group_or_404(group_id, request.user)
        passwords = self.get_filtered_passwords(group, request.GET)
        
        context = {
            'group': group,
            'passwords': passwords,
            'search_query': request.GET.get('search', ''),
        }
        
        template = 'passwords/partials/list.html' if self.is_htmx_request(request) else 'passwords/list.html'
        return render(request, template, context)
    
    def get_group_or_404(self, group_id, user):
        """Get group with permission check."""
        group = get_object_or_404(Group, id=group_id)
        if not group.has_member(user):
            raise PermissionDenied("You don't have access to this group")
        return group
    
    def get_filtered_passwords(self, group, params):
        """Get filtered passwords based on search parameters."""
        passwords = group.passwords.all()
        
        search_query = params.get('search', '').strip()
        if search_query:
            passwords = passwords.filter(
                Q(title__icontains=search_query) |
                Q(username__icontains=search_query) |
                Q(url__icontains=search_query)
            )
        
        return passwords.select_related('created_by', 'directory')
    
    def is_htmx_request(self, request):
        """Check if request is from HTMX."""
        return request.headers.get('HX-Request') == 'true'

# ❌ Bad - Function-based view without proper structure
def password_list(request, group_id):
    group = Group.objects.get(id=group_id)  # No error handling
    passwords = Password.objects.filter(group=group)  # No permission check
    return render(request, 'passwords/list.html', {'passwords': passwords})
```

#### Service Layer Pattern
```python
# ✅ Good - Service layer for business logic
class PasswordService:
    """Service class for password-related business logic."""
    
    @staticmethod
    def create_password(user: User, group: Group, data: dict) -> Password:
        """
        Create new password entry with proper validation and encryption.
        
        Args:
            user: User creating the password
            group: Group where password belongs
            data: Password data dictionary
            
        Returns:
            Created Password instance
            
        Raises:
            ValidationError: If data is invalid
            PermissionError: If user doesn't have permission
        """
        # Validate permissions
        if not group.has_member(user):
            raise PermissionError("User is not a member of this group")
        
        # Validate data
        validator = PasswordValidator(data)
        if not validator.is_valid():
            raise ValidationError(validator.errors)
        
        # Encrypt sensitive data
        encrypted_password = EncryptionService.encrypt(
            data['password'], 
            group.encryption_key
        )
        
        encrypted_notes = ''
        if data.get('notes'):
            encrypted_notes = EncryptionService.encrypt(
                data['notes'], 
                group.encryption_key
            )
        
        # Create password entry
        password = Password.objects.create(
            title=data['title'],
            username=data.get('username', ''),
            password_encrypted=encrypted_password,
            url=data.get('url', ''),
            notes_encrypted=encrypted_notes,
            tags=data.get('tags', []),
            custom_fields=data.get('custom_fields', []),
            group=group,
            created_by=user,
            directory_id=data.get('directory_id')
        )
        
        # Log activity
        ActivityLogger.log_password_created(user, password)
        
        return password
    
    @staticmethod
    def get_decrypted_password(password: Password, user: User) -> dict:
        """Get password with decrypted sensitive fields."""
        if not password.group.has_member(user):
            raise PermissionError("User doesn't have access to this password")
        
        # Update last accessed
        password.last_accessed = timezone.now()
        password.save(update_fields=['last_accessed'])
        
        # Decrypt sensitive data
        decrypted_password = EncryptionService.decrypt(
            password.password_encrypted,
            password.group.encryption_key
        )
        
        decrypted_notes = ''
        if password.notes_encrypted:
            decrypted_notes = EncryptionService.decrypt(
                password.notes_encrypted,
                password.group.encryption_key
            )
        
        return {
            'id': str(password.id),
            'title': password.title,
            'username': password.username,
            'password': decrypted_password,
            'url': password.url,
            'notes': decrypted_notes,
            'tags': password.tags,
            'custom_fields': password.custom_fields,
            'favorite': password.favorite,
            'created_at': password.created_at.isoformat(),
            'updated_at': password.updated_at.isoformat(),
        }
```

### 3. Security Best Practices

#### Input Validation
```python
# ✅ Good - Proper input validation
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

class PasswordValidator:
    """Validator for password data."""
    
    def __init__(self, data):
        self.data = data
        self.errors = {}
    
    def is_valid(self):
        """Validate all fields."""
        self._validate_title()
        self._validate_password()
        self._validate_url()
        self._validate_email_fields()
        return len(self.errors) == 0
    
    def _validate_title(self):
        title = self.data.get('title', '').strip()
        if not title:
            self.errors['title'] = "Title is required"
        elif len(title) > 255:
            self.errors['title'] = "Title too long (max 255 characters)"
    
    def _validate_password(self):
        password = self.data.get('password', '')
        if not password:
            self.errors['password'] = "Password is required"
        elif len(password) > 1000:  # Reasonable limit
            self.errors['password'] = "Password too long"
    
    def _validate_url(self):
        url = self.data.get('url', '').strip()
        if url:
            try:
                URLValidator()(url)
            except ValidationError:
                self.errors['url'] = "Invalid URL format"
    
    def _validate_email_fields(self):
        """Validate email in custom fields."""
        custom_fields = self.data.get('custom_fields', [])
        for field in custom_fields:
            if field.get('type') == 'email' and field.get('value'):
                try:
                    validate_email(field['value'])
                except ValidationError:
                    self.errors['custom_fields'] = f"Invalid email: {field['value']}"

# ❌ Bad - No validation
def create_password(data):
    return Password.objects.create(**data)  # Direct creation without validation
```

#### SQL Injection Prevention
```python
# ✅ Good - Using Django ORM
passwords = Password.objects.filter(
    title__icontains=search_query,
    group=group
).select_related('created_by')

# ✅ Good - If raw SQL needed, use parameters
from django.db import connection

def get_password_stats(group_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*), AVG(EXTRACT(days FROM NOW() - updated_at))
            FROM passwords_password 
            WHERE group_id = %s
        """, [group_id])
        return cursor.fetchone()

# ❌ Bad - SQL injection vulnerability
def search_passwords(query):
    return Password.objects.extra(
        where=[f"title LIKE '%{query}%'"]  # Vulnerable to SQL injection
    )
```

#### XSS Prevention
```python
# ✅ Good - Proper escaping in templates
<!-- templates/passwords/detail.html -->
<h1>{{ password.title|escape }}</h1>
<p>{{ password.notes|escape|linebreaks }}</p>

<!-- For HTML content, use |safe only when content is trusted -->
<div>{{ password.description|escape|linebreaks }}</div>

# ✅ Good - Escaping in views when needed
from django.utils.html import escape

def password_detail_json(request, password_id):
    password = get_object_or_404(Password, id=password_id)
    return JsonResponse({
        'title': escape(password.title),
        'notes': escape(password.notes),
    })

# ❌ Bad - No escaping
<h1>{{ password.title|safe }}</h1>  <!-- Dangerous if title contains HTML -->
```

---

## 🎨 Frontend Standards (HTMX + Alpine.js)

### 1. HTMX Best Practices

#### Proper HTMX Usage
```html
<!-- ✅ Good - Proper HTMX attributes -->
<form hx-post="{% url 'passwords:create' group.id %}"
      hx-target="#password-list"
      hx-swap="afterbegin"
      hx-indicator="#loading"
      hx-on::after-request="resetForm()">
    
    <input type="text" name="title" required>
    <input type="password" name="password" required>
    
    <button type="submit">
        <span class="htmx-indicator" id="loading">Creating...</span>
        <span>Create Password</span>
    </button>
</form>

<!-- ✅ Good - Search with debouncing -->
<input type="text" 
       name="search"
       hx-get="{% url 'passwords:search' group.id %}"
       hx-target="#search-results"
       hx-trigger="input changed delay:300ms"
       placeholder="Search passwords...">

<!-- ❌ Bad - No proper targeting or indicators -->
<form hx-post="/create-password/">
    <input type="text" name="title">
    <button type="submit">Create</button>
</form>
```

#### Error Handling
```html
<!-- ✅ Good - Proper error handling -->
<div id="error-container" class="hidden">
    <div class="alert alert-error" role="alert">
        <span id="error-message"></span>
    </div>
</div>

<form hx-post="{% url 'passwords:create' group.id %}"
      hx-target="#password-list"
      hx-on::response-error="handleError(event)">
    <!-- form fields -->
</form>

<script>
function handleError(event) {
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    
    errorMessage.textContent = event.detail.xhr.responseJSON?.error || 'An error occurred';
    errorContainer.classList.remove('hidden');
    
    setTimeout(() => {
        errorContainer.classList.add('hidden');
    }, 5000);
}
</script>
```

### 2. Alpine.js Best Practices

#### Component Structure
```html
<!-- ✅ Good - Well-structured Alpine component -->
<div x-data="passwordManager()" class="password-manager">
    <!-- Search -->
    <div class="mb-4">
        <input type="text" 
               x-model="searchQuery"
               @input.debounce.300ms="search()"
               placeholder="Search passwords..."
               class="w-full px-4 py-2 border rounded">
    </div>
    
    <!-- Password List -->
    <div class="space-y-2">
        <template x-for="password in filteredPasswords" :key="password.id">
            <div class="password-item p-4 border rounded">
                <div class="flex justify-between items-center">
                    <div>
                        <h3 x-text="password.title" class="font-semibold"></h3>
                        <p x-text="password.username" class="text-gray-600"></p>
                    </div>
                    
                    <div class="flex space-x-2">
                        <button @click="copyPassword(password.id)"
                                :disabled="copying"
                                class="btn btn-sm">
                            <span x-show="!copying">Copy</span>
                            <span x-show="copying">Copying...</span>
                        </button>
                        
                        <button @click="toggleFavorite(password.id)"
                                :class="password.favorite ? 'text-yellow-500' : 'text-gray-400'"
                                class="btn btn-sm">
                            ★
                        </button>
                    </div>
                </div>
            </div>
        </template>
    </div>
    
    <!-- Empty State -->
    <div x-show="filteredPasswords.length === 0" class="text-center py-8">
        <p class="text-gray-500">No passwords found</p>
    </div>
</div>

<script>
function passwordManager() {
    return {
        passwords: [],
        searchQuery: '',
        copying: false,
        
        get filteredPasswords() {
            if (!this.searchQuery) return this.passwords;
            
            return this.passwords.filter(password => 
                password.title.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                password.username.toLowerCase().includes(this.searchQuery.toLowerCase())
            );
        },
        
        async copyPassword(passwordId) {
            this.copying = true;
            
            try {
                const response = await fetch(`/api/passwords/${passwordId}/decrypt/`);
                const data = await response.json();
                
                await navigator.clipboard.writeText(data.password);
                this.showNotification('Password copied to clipboard');
            } catch (error) {
                this.showNotification('Failed to copy password', 'error');
            } finally {
                this.copying = false;
            }
        },
        
        async toggleFavorite(passwordId) {
            try {
                const response = await fetch(`/api/passwords/${passwordId}/favorite/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.getCsrfToken(),
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    const password = this.passwords.find(p => p.id === passwordId);
                    if (password) {
                        password.favorite = !password.favorite;
                    }
                }
            } catch (error) {
                this.showNotification('Failed to update favorite', 'error');
            }
        },
        
        getCsrfToken() {
            return document.querySelector('[name=csrfmiddlewaretoken]').value;
        },
        
        showNotification(message, type = 'success') {
            // Implementation for showing notifications
            console.log(`${type}: ${message}`);
        }
    }
}
</script>

<!-- ❌ Bad - Unstructured Alpine usage -->
<div x-data="{ passwords: [], query: '' }">
    <input x-model="query">
    <div x-show="passwords.length > 0">
        <!-- No proper structure or error handling -->
    </div>
</div>
```

### 3. CSS/Tailwind Standards

#### Consistent Styling
```html
<!-- ✅ Good - Consistent component classes -->
<div class="card">
    <div class="card-header">
        <h2 class="card-title">Password Details</h2>
    </div>
    <div class="card-body">
        <div class="form-group">
            <label class="form-label">Title</label>
            <input type="text" class="form-input">
        </div>
    </div>
    <div class="card-footer">
        <button class="btn btn-primary">Save</button>
        <button class="btn btn-secondary">Cancel</button>
    </div>
</div>

<!-- Custom CSS for consistent components -->
<style>
.card {
    @apply bg-white rounded-lg shadow border;
}

.card-header {
    @apply px-6 py-4 border-b;
}

.card-title {
    @apply text-lg font-semibold text-gray-900;
}

.card-body {
    @apply px-6 py-4;
}

.card-footer {
    @apply px-6 py-4 border-t bg-gray-50 flex justify-end space-x-2;
}

.btn {
    @apply px-4 py-2 rounded font-medium transition-colors;
}

.btn-primary {
    @apply bg-blue-600 text-white hover:bg-blue-700;
}

.btn-secondary {
    @apply bg-gray-200 text-gray-900 hover:bg-gray-300;
}

.form-group {
    @apply mb-4;
}

.form-label {
    @apply block text-sm font-medium text-gray-700 mb-1;
}

.form-input {
    @apply w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500;
}
</style>
```

---

## 🧪 Testing Standards

### 1. Unit Testing
```python
# ✅ Good - Comprehensive unit tests
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.passwords.services import PasswordService, PasswordEncryptionService
from apps.groups.models import Group

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
            'url': 'https://example.com',
            'notes': 'Test notes'
        }
        
        password = PasswordService.create_password(
            self.user, self.group, password_data
        )
        
        self.assertEqual(password.title, 'Test Password')
        self.assertEqual(password.username, 'testuser')
        self.assertEqual(password.group, self.group)
        self.assertEqual(password.created_by, self.user)
        self.assertTrue(password.password_encrypted)  # Should be encrypted
    
    def test_create_password_invalid_data(self):
        """Test password creation with invalid data."""
        password_data = {
            'title': '',  # Empty title should fail
            'password': 'secret123'
        }
        
        with self.assertRaises(ValidationError):
            PasswordService.create_password(
                self.user, self.group, password_data
            )
    
    def test_create_password_no_permission(self):
        """Test password creation without group permission."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            full_name='Other User'
        )
        
        password_data = {
            'title': 'Test Password',
            'password': 'secret123'
        }
        
        with self.assertRaises(PermissionError):
            PasswordService.create_password(
                other_user, self.group, password_data
            )
    
    def test_encryption_decryption(self):
        """Test password encryption and decryption."""
        original_password = "super_secret_password"
        group_id = str(self.group.id)
        
        # Encrypt
        encrypted = PasswordEncryptionService.encrypt_password(
            original_password, group_id
        )
        
        # Should be different from original
        self.assertNotEqual(encrypted, original_password)
        
        # Decrypt
        decrypted = PasswordEncryptionService.decrypt_password(
            encrypted, group_id
        )
        
        # Should match original
        self.assertEqual(decrypted, original_password)
    
    def test_get_decrypted_password(self):
        """Test getting decrypted password data."""
        # Create password
        password_data = {
            'title': 'Test Password',
            'password': 'secret123',
            'notes': 'Secret notes'
        }
        
        password = PasswordService.create_password(
            self.user, self.group, password_data
        )
        
        # Get decrypted data
        decrypted_data = PasswordService.get_decrypted_password(
            password, self.user
        )
        
        self.assertEqual(decrypted_data['title'], 'Test Password')
        self.assertEqual(decrypted_data['password'], 'secret123')
        self.assertEqual(decrypted_data['notes'], 'Secret notes')
```

### 2. Integration Testing
```python
# ✅ Good - Integration tests
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class PasswordViewsIntegrationTest(TestCase):
    """Integration tests for password views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        self.group = Group.objects.create(
            name='Test Group',
            owner=self.user
        )
        self.client.login(email='test@example.com', password='testpass123')
    
    def test_password_list_view(self):
        """Test password list view."""
        url = reverse('passwords:list', kwargs={'group_id': self.group.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Group')
        self.assertContains(response, 'Add Password')
    
    def test_create_password_via_post(self):
        """Test password creation via POST."""
        url = reverse('passwords:create', kwargs={'group_id': self.group.id})
        data = {
            'title': 'New Password',
            'username': 'newuser',
            'password': 'newsecret123',
            'url': 'https://newsite.com'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)  # HTMX returns 200
        
        # Check password was created
        password = Password.objects.get(title='New Password')
        self.assertEqual(password.username, 'newuser')
        self.assertEqual(password.group, self.group)
    
    def test_search_passwords(self):
        """Test password search functionality."""
        # Create test passwords
        PasswordService.create_password(self.user, self.group, {
            'title': 'Gmail Account',
            'username': 'test@gmail.com',
            'password': 'secret123'
        })
        
        PasswordService.create_password(self.user, self.group, {
            'title': 'Facebook Account',
            'username': 'testuser',
            'password': 'secret456'
        })
        
        # Search for Gmail
        url = reverse('passwords:list', kwargs={'group_id': self.group.id})
        response = self.client.get(url, {'search': 'gmail'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gmail Account')
        self.assertNotContains(response, 'Facebook Account')
```

### 3. Frontend Testing
```javascript
// ✅ Good - Frontend testing with Jest
// tests/frontend/password-manager.test.js

/**
 * @jest-environment jsdom
 */

import { passwordManager } from '../static/js/components/password-manager.js';

describe('Password Manager Component', () => {
    let component;
    
    beforeEach(() => {
        // Setup DOM
        document.body.innerHTML = `
            <div id="app" x-data="passwordManager()">
                <input x-model="searchQuery" id="search">
                <div id="results"></div>
            </div>
        `;
        
        // Initialize component
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
    
    test('should toggle favorite status', async () => {
        // Mock fetch
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ success: true })
            })
        );
        
        await component.toggleFavorite('1');
        
        expect(component.passwords[0].favorite).toBe(true);
        expect(fetch).toHaveBeenCalledWith('/api/passwords/1/favorite/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': expect.any(String),
                'Content-Type': 'application/json'
            }
        });
    });
    
    test('should handle copy password error gracefully', async () => {
        // Mock fetch to fail
        global.fetch = jest.fn(() => Promise.reject(new Error('Network error')));
        
        const consoleSpy = jest.spyOn(console, 'log');
        
        await component.copyPassword('1');
        
        expect(consoleSpy).toHaveBeenCalledWith('error: Failed to copy password');
    });
});
```

---

## 📊 Performance Standards

### 1. Database Optimization
```python
# ✅ Good - Optimized queries
def get_group_passwords(group_id, user):
    """Get group passwords with optimized queries."""
    return Password.objects.filter(
        group_id=group_id
    ).select_related(
        'created_by', 'directory'
    ).prefetch_related(
        'shares__shared_with'
    ).order_by('-updated_at')

# ✅ Good - Using indexes
class Password(models.Model):
    # ... fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['group', '-updated_at']),  # For listing
            models.Index(fields=['title']),                 # For search
            models.Index(fields=['created_by', '-created_at']),  # For user's passwords
            models.Index(fields=['group', 'favorite']),     # For favorites
        ]

# ❌ Bad - N+1 queries
def get_passwords_with_creators(group_id):
    passwords = Password.objects.filter(group_id=group_id)
    for password in passwords:
        print(password.created_by.full_name)  # N+1 query problem
```

### 2. Caching Strategy
```python
# ✅ Good - Strategic caching
from django.core.cache import cache
from django.views.decorators.cache import cache_page

class GroupService:
    @staticmethod
    def get_user_groups(user_id):
        """Get user groups with caching."""
        cache_key = f"user_groups:{user_id}"
        groups = cache.get(cache_key)
        
        if groups is None:
            groups = list(Group.objects.filter(
                models.Q(owner_id=user_id) |
                models.Q(usergroup__user_id=user_id)
            ).distinct().values('id', 'name', 'description'))
            
            cache.set(cache_key, groups, timeout=300)  # 5 minutes
        
        return groups
    
    @staticmethod
    def invalidate_user_groups_cache(user_id):
        """Invalidate user groups cache."""
        cache_key = f"user_groups:{user_id}"
        cache.delete(cache_key)

# ✅ Good - Template fragment caching
<!-- templates/passwords/list.html -->
{% load cache %}

{% cache 300 password_list group.id user.id %}
    <div class="password-list">
        {% for password in passwords %}
            {% include 'passwords/partials/password_item.html' %}
        {% endfor %}
    </div>
{% endcache %}
```

---

## 🔍 Code Review Guidelines

### 1. Review Checklist
```markdown
## Security Review
- [ ] Input validation implemented
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection
- [ ] Authentication/authorization checks
- [ ] Sensitive data encryption
- [ ] No hardcoded secrets

## Code Quality
- [ ] Follows PEP 8 style guide
- [ ] Proper error handling
- [ ] Meaningful variable/function names
- [ ] Adequate comments/docstrings
- [ ] No code duplication
- [ ] Proper separation of concerns

## Performance
- [ ] Database queries optimized
- [ ] No N+1 query problems
- [ ] Appropriate caching
- [ ] Efficient algorithms
- [ ] Proper indexing

## Testing
- [ ] Unit tests written
- [ ] Integration tests for complex flows
- [ ] Edge cases covered
- [ ] Test coverage > 90%
- [ ] Tests are maintainable

## Documentation
- [ ] API documentation updated
- [ ] README updated if needed
- [ ] Inline comments for complex logic
- [ ] Migration files reviewed
```

### 2. Common Issues to Watch For
```python
# ❌ Common security issues
def get_password(request, password_id):
    password = Password.objects.get(id=password_id)  # No permission check
    return JsonResponse({'password': password.password_encrypted})  # Returning encrypted data

# ❌ Performance issues
def get_all_passwords(request):
    passwords = []
    for group in Group.objects.all():  # N+1 query
        for password in group.passwords.all():  # Another N+1
            passwords.append({
                'title': password.title,
                'creator': password.created_by.full_name  # Yet another N+1
            })
    return JsonResponse({'passwords': passwords})

# ❌ Code quality issues
def create_pwd(u, g, d):  # Unclear parameter names
    if d['title']:  # No proper validation
        p = Password()  # Should use create()
        p.title = d['title']
        p.password_encrypted = encrypt(d['password'])  # No error handling
        p.save()
        return p
```

---

## 📝 Documentation Standards

### 1. Code Documentation
```python
# ✅ Good - Proper docstrings
class PasswordEncryptionService:
    """Service for encrypting and decrypting password data.
    
    This service handles all encryption/decryption operations for password
    entries using AES-256-GCM encryption with group-specific keys.
    """
    
    @staticmethod
    def encrypt_password(password: str, group_id: str) -> str:
        """
        Encrypt a password using group-specific encryption key.
        
        Args:
            password (str): Plain text password to encrypt
            group_id (str): UUID of the group for key derivation
            
        Returns:
            str: Base64 encoded encrypted password
            
        Raises:
            EncryptionError: If encryption fails
            ValueError: If password or group_id is invalid
            
        Example:
            >>> encrypted = PasswordEncryptionService.encrypt_password(
            ...     "my_secret_password", 
            ...     "550e8400-e29b-41d4-a716-446655440000"
            ... )
            >>> isinstance(encrypted, str)
            True
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        if not group_id:
            raise ValueError("Group ID is required")
        
        try:
            key = self._generate_key(group_id)
            fernet = Fernet(key)
            encrypted = fernet.encrypt(password.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            raise EncryptionError(f"Failed to encrypt password: {str(e)}")
```

### 2. API Documentation
```python
# ✅ Good - API documentation with examples
class PasswordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing password entries.
    
    Provides CRUD operations for password entries within groups.
    All operations require group membership.
    """
    
    def create(self, request, *args, **kwargs):
        """
        Create a new password entry.
        
        **Request Body:**
        ```json
        {
            "title": "Gmail Account",
            "username": "user@gmail.com",
            "password": "secret123",
            "url": "https://gmail.com",
            "notes": "Personal email account",
            "tags": ["email", "personal"],
            "custom_fields": [
                {
                    "name": "Recovery Email",
                    "value": "backup@gmail.com",
                    "type": "email"
                }
            ],
            "directory_id": "uuid-here"
        }
        ```
        
        **Response (201 Created):**
        ```json
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Gmail Account",
            "username": "user@gmail.com",
            "url": "https://gmail.com",
            "tags": ["email", "personal"],
            "favorite": false,
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T12:00:00Z"
        }
        ```
        
        **Error Responses:**
        - `400 Bad Request`: Invalid data
        - `403 Forbidden`: Not a group member
        - `422 Unprocessable Entity`: Validation errors
        """
        pass
```

---

## 🚀 Deployment Standards

### 1. Environment Configuration
```python
# ✅ Good - Environment-based settings
# config/settings/base.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security settings
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")

DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'passmandb'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# ❌ Bad - Hardcoded values
SECRET_KEY = 'hardcoded-secret-key'  # Security risk
DEBUG = True  # Should be environment-based
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'passmandb',
        'USER': 'postgres',
        'PASSWORD': 'password123',  # Hardcoded password
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 2. Docker Best Practices
```dockerfile
# ✅ Good - Multi-stage Docker build
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

---

*This coding standards document should be followed by all team members dan akan diupdate seiring dengan perkembangan project. Regular code reviews dan automated linting tools akan membantu enforce standards ini.*