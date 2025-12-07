"""
Tests for the directories app.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.directories.models import Directory
from apps.groups.models import Group

User = get_user_model()

class DirectoryModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            full_name='Test User'
        )
        self.group = Group.objects.create(
            name='Test Group',
            owner=self.user
        )
        from apps.groups.models import UserGroup
        UserGroup.objects.create(user=self.user, group=self.group, role=UserGroup.Role.OWNER)

    def test_create_directory(self):
        """Test creating a directory."""
        directory = Directory.objects.create(
            name='Test Directory',
            group=self.group,
            created_by=self.user
        )
        self.assertEqual(directory.name, 'Test Directory')
        self.assertEqual(directory.group, self.group)
        self.assertEqual(directory.created_by, self.user)

    def test_directory_hierarchy(self):
        """Test parent-child relationship."""
        parent = Directory.objects.create(
            name='Parent',
            group=self.group,
            created_by=self.user
        )
        child = Directory.objects.create(
            name='Child',
            parent=parent,
            group=self.group,
            created_by=self.user
        )
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.subdirectories.all())

    def test_circular_reference_validation(self):
        """Test that circular references are prevented."""
        directory = Directory.objects.create(
            name='Test Directory',
            group=self.group,
            created_by=self.user
        )
        directory.parent = directory
        with self.assertRaises(Exception): # ValidationError is raised in clean(), but save() calls full_clean()
            directory.save()

class DirectoryAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            full_name='Test User'
        )
        self.client.force_authenticate(user=self.user)
        self.group = Group.objects.create(
            name='Test Group',
            owner=self.user
        )
        from apps.groups.models import UserGroup
        UserGroup.objects.create(user=self.user, group=self.group, role=UserGroup.Role.OWNER)

    def test_list_directories(self):
        """Test listing directories."""
        Directory.objects.create(
            name='Dir 1',
            group=self.group,
            created_by=self.user
        )
        url = reverse('directories_api:directory-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_directory_api(self):
        """Test creating a directory via API."""
        url = reverse('directories_api:directory-list')
        data = {
            'name': 'New Directory',
            'group': self.group.id,
            'parent': None
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Directory.objects.count(), 1)
        self.assertEqual(Directory.objects.first().name, 'New Directory')

    def test_directory_tree_api(self):
        """Test the tree endpoint."""
        parent = Directory.objects.create(
            name='Parent',
            group=self.group,
            created_by=self.user
        )
        Directory.objects.create(
            name='Child',
            parent=parent,
            group=self.group,
            created_by=self.user
        )
        url = reverse('directories_api:directory-tree')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1) # Only root directories
        self.assertEqual(len(response.data[0]['children']), 1) # Child is nested
