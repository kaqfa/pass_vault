from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse
from datetime import timedelta
from unittest.mock import patch, MagicMock
import json

from apps.passwords.models import Password, PasswordShare, PasswordHistory, PasswordAccessLog
from apps.passwords.services import PasswordService, PasswordGeneratorService
from apps.groups.models import Group, UserGroup
from apps.passwords.views import PasswordListView, PasswordDetailView, PasswordCreateView

User = get_user_model()

class PasswordSharingTests(TestCase):
    def setUp(self):
        # Create users
        self.owner = User.objects.create_user(email='owner@test.com', password='password', full_name='Owner User')
        self.user_a = User.objects.create_user(email='user_a@test.com', password='password', full_name='User A')
        self.user_b = User.objects.create_user(email='user_b@test.com', password='password', full_name='User B')
        
        # Create group and password
        self.group = Group.objects.create(name='Test Group', owner=self.owner)
        self.password = Password.objects.create(
            title='Secret Password',
            encrypted_password='encrypted_content',
            group=self.group,
            created_by=self.owner
        )
        # Mock encryption key
        self.group.encryption_key = 'test_key'
        self.group.save()

    def test_share_password(self):
        """Test sharing a password with another user."""
        share = PasswordShare.objects.create(
            password=self.password,
            shared_by=self.owner,
            shared_with=self.user_a,
            permission=PasswordShare.Permission.VIEW
        )
        
        self.assertEqual(share.permission, 'view')
        self.assertEqual(self.password.shares.count(), 1)
        self.assertEqual(share.shared_with, self.user_a)

    def test_share_unique_constraint(self):
        """Test that a password cannot be shared with the same user twice."""
        PasswordShare.objects.create(
            password=self.password,
            shared_by=self.owner,
            shared_with=self.user_a
        )
        
        with self.assertRaises(Exception):
            PasswordShare.objects.create(
                password=self.password,
                shared_by=self.owner,
                shared_with=self.user_a
            )

    def test_share_expiration(self):
        """Test share expiration logic."""
        share = PasswordShare.objects.create(
            password=self.password,
            shared_by=self.owner,
            shared_with=self.user_a,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        self.assertTrue(share.is_expired())
        
        share_active = PasswordShare.objects.create(
            password=self.password,
            shared_by=self.owner,
            shared_with=self.user_b,
            expires_at=timezone.now() + timedelta(hours=1)
        )
        self.assertFalse(share_active.is_expired())

    def test_share_permissions(self):
        """Test permission levels."""
        view_share = PasswordShare.objects.create(
            password=self.password,
            shared_by=self.owner,
            shared_with=self.user_a,
            permission=PasswordShare.Permission.VIEW
        )
        self.assertEqual(view_share.permission, 'view')
        
        edit_share = PasswordShare.objects.create(
            password=self.password,
            shared_by=self.owner,
            shared_with=self.user_b,
            permission='edit'
        )
        self.assertEqual(edit_share.permission, 'edit')

class PasswordCoreTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@test.com', password='password', full_name='Owner User')
        self.group = Group.objects.create(name='Test Group', owner=self.owner)
        self.group.encryption_key = 'test_key'
        self.group.save()
        
    def test_create_password(self):
        """Test password creation via service."""
        data = {
            'title': 'Test Password',
            'username': 'testuser',
            'password': 'Str0ngP@ssw0rd!X1',
            'url': 'https://example.com',
            'group_id': self.group.id
        }
        
        password = PasswordService.create_password(self.owner, data)
        
        self.assertEqual(password.title, 'Test Password')
        self.assertEqual(password.username, 'testuser')
        self.assertNotEqual(password.encrypted_password, 'Str0ngP@ssw0rd!X1') # Should be encrypted
        self.assertEqual(PasswordHistory.objects.count(), 1)
        
    def test_get_password_decryption(self):
        """Test retreiving and decrypting password."""
        data = {
            'title': 'Test Password',
            'password': 'Str0ngP@ssw0rd!X1',
            'group_id': self.group.id
        }
        password = PasswordService.create_password(self.owner, data)
        
        # Retrieve using service
        retrieved = PasswordService.get_password(self.owner, password.id)
        
        # Verify it's retrieved
        self.assertEqual(retrieved.id, password.id)
        
        # Verify we can decrypt it
        decrypted = retrieved.get_password()
        self.assertEqual(decrypted, 'Str0ngP@ssw0rd!X1')

    def test_update_password(self):
        """Test updating password."""
        data = {
            'title': 'Original Title',
            'password': 'oldPassw0rd!Secure',
            'group_id': self.group.id
        }
        password = PasswordService.create_password(self.owner, data)
        
        update_data = {
            'title': 'New Title',
            'password': 'NewP@ssw0rd!987'  # Changed from 999 to avoid repeated char validation
        }
        
        updated = PasswordService.update_password(self.owner, password.id, update_data)
        self.assertEqual(updated.title, 'New Title')
        self.assertEqual(PasswordHistory.objects.count(), 2) # Create + Update

    def test_delete_password(self):
        """Test soft deletion."""
        data = {
            'title': 'To Delete',
            'password': 'SecureP@ssw0rd!88',
            'group_id': self.group.id
        }
        password = PasswordService.create_password(self.owner, data)
        
        PasswordService.delete_password(self.owner, password.id)
        
        # Verify it's not in default manager (soft deleted)
        with self.assertRaises(Exception): # Service raises ServiceError if not found
             PasswordService.get_password(self.owner, password.id)
             
        # Verify it exists in all_objects
        self.assertTrue(Password.all_objects.filter(id=password.id).exists())

class PasswordValidationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@test.com', password='password', full_name='Owner User')
        self.group = Group.objects.create(name='Test Group', owner=self.owner)
        self.group.encryption_key = 'test_key'
        self.group.save()

    def test_title_required(self):
        """Ensure title is mandatory."""
        password = Password(
            title='',
            encrypted_password='enc',
            group=self.group,
            created_by=self.owner
        )
        with self.assertRaises(ValidationError):
            password.full_clean()

    def test_invalid_json_fields(self):
        """Ensure custom_fields and tags validation works."""
        # Test invalid custom_fields
        with self.assertRaises(ValidationError):
            p = Password(
                title='Test',
                encrypted_password='enc',
                group=self.group,
                created_by=self.owner,
                custom_fields='not_a_dict' # type: ignore
            )
            p.full_clean()
            
        # Test invalid tags
        with self.assertRaises(ValidationError):
            p = Password(
                title='Test',
                encrypted_password='enc',
                group=self.group,
                created_by=self.owner,
                tags='not_a_list' # type: ignore
            )
            p.full_clean()

class PasswordAccessLogTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@test.com', password='password', full_name='Owner User')
        self.group = Group.objects.create(name='Test Group', owner=self.owner)
        self.group.encryption_key = 'test_key'
        self.group.save()
        
        data = {
            'title': 'Log Test',
            'password': 'Str0ngP@ssw0rd!X1',
            'group_id': self.group.id
        }
        self.password = PasswordService.create_password(self.owner, data)

    def test_access_log_creation(self):
        """Verify PasswordAccessLog created on retrieval with record_access=True."""
        # Initial state
        self.assertEqual(PasswordAccessLog.objects.count(), 0)
        
        # Access password
        PasswordService.get_password(self.owner, self.password.id, record_access=True)
        
        # Verify log created
        self.assertEqual(PasswordAccessLog.objects.count(), 1)
        log = PasswordAccessLog.objects.first()
        self.assertEqual(log.password, self.password)
        self.assertEqual(log.user, self.owner)

class PasswordViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email='user@test.com', password='password', full_name='Test User')
        self.other_user = User.objects.create_user(email='other@test.com', password='password', full_name='Other User')
        
        self.group = Group.objects.create(name='User Group', owner=self.user)
        self.group.encryption_key = 'test_key'
        self.group.save()
        
        self.other_group = Group.objects.create(name='Other Group', owner=self.other_user)
        self.other_group.encryption_key = 'other_key'
        self.other_group.save()
        
        # Create some passwords
        self.p1 = PasswordService.create_password(self.user, {
            'title': 'User Password 1', 
            'password': 'Str0ngP@ssw0rd!X1', 
            'group_id': self.group.id
        })
        self.p2 = PasswordService.create_password(self.user, {
            'title': 'User Password 2', 
            'password': 'Str0ngP@ssw0rd!X2', 
            'group_id': self.group.id,
            'tags': ['work']
        })
        self.other_p = PasswordService.create_password(self.other_user, {
            'title': 'Other Password', 
            'password': 'Str0ngP@ssw0rd!X3', 
            'group_id': self.other_group.id
        })

    def test_password_list_view(self):
        """Verify list page loads and shows passwords."""
        request = self.factory.get(reverse('passwords:list'))
        request.user = self.user
        
        response = PasswordListView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Password 1')
        self.assertContains(response, 'User Password 2')
        self.assertNotContains(response, 'Other Password')

    def test_password_search(self):
        """Verify search query filters results."""
        request = self.factory.get(reverse('passwords:list') + '?q=Password 1')
        request.user = self.user
        
        response = PasswordListView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Password 1')
        self.assertNotContains(response, 'User Password 2')

    def test_password_create_view_post(self):
        """Verify creation via form POST."""
        data = {
            'title': 'New View Password',
            'username': 'newuser',
            'password': 'Str0ngP@ssw0rd!X4',
            'group_id': self.group.id,
            'priority': 'medium'
        }
        
        # Use simple RequestFactory + view call
        # Note: PasswordCreateView is complex, let's assume it redirects on success
        request = self.factory.post(reverse('passwords:create'), data)
        request.user = self.user

        # Need to handle messages framework which uses sessions
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        middleware = MessageMiddleware(lambda x: None)
        middleware.process_request(request)
        
        response = PasswordCreateView.as_view()(request)
        self.assertEqual(response.status_code, 302) # Redirect to detail or list
        self.assertTrue(Password.objects.filter(title='New View Password').exists())

    def test_password_access_control_view(self):
        """Verify users cannot see passwords from other groups they don't belong to."""
        from django.core.exceptions import PermissionDenied
        
        request = self.factory.get(reverse('passwords:detail', args=[self.other_p.id]))
        request.user = self.user
        
        # The service raises PermissionDenied, and the view (BaseView/Django) propagates it
        with self.assertRaises(PermissionDenied):
            PasswordDetailView.as_view()(request, password_id=self.other_p.id)
