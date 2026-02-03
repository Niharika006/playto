"""
Tests for the Community Feed application.

Key test coverage:
1. Leaderboard only counts karma from last 24 hours
2. Double-like prevention
3. Karma transaction creation
4. Comment tree building
"""
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Post, Comment, Like, KarmaTransaction
from .views import PostViewSet


class LeaderboardTimeFilterTest(APITestCase):
    """
    Test that leaderboard only counts karma from the last 24 hours.
    
    This is a CRITICAL test case - it verifies the time-based
    filtering that is central to the leaderboard feature.
    """
    
    def setUp(self):
        """Create test users and karma transactions."""
        self.user1 = User.objects.create_user(
            username='user1', password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2', password='testpass123'
        )
        self.user3 = User.objects.create_user(
            username='user3', password='testpass123'
        )
        
    def test_leaderboard_excludes_old_karma(self):
        """
        Verify that karma older than 24 hours is NOT included.
        
        Scenario:
        - user1: 100 karma from 25 hours ago (should NOT count)
        - user2: 10 karma from 1 hour ago (should count)
        - user3: 5 karma from 12 hours ago (should count)
        
        Expected: user2 (10) > user3 (5), user1 not on leaderboard
        """
        now = timezone.now()
        
        # Create old karma for user1 (25 hours ago - outside window)
        old_karma = KarmaTransaction.objects.create(
            user=self.user1,
            points=100,
            source_type='post_like',
            source_id=1
        )
        # Manually set created_at to 25 hours ago
        KarmaTransaction.objects.filter(pk=old_karma.pk).update(
            created_at=now - timedelta(hours=25)
        )
        
        # Create recent karma for user2 (1 hour ago - inside window)
        KarmaTransaction.objects.create(
            user=self.user2,
            points=10,
            source_type='post_like',
            source_id=2
        )
        
        # Create recent karma for user3 (12 hours ago - inside window)
        recent_karma = KarmaTransaction.objects.create(
            user=self.user3,
            points=5,
            source_type='comment_like',
            source_id=3
        )
        KarmaTransaction.objects.filter(pk=recent_karma.pk).update(
            created_at=now - timedelta(hours=12)
        )
        
        # Make API request
        response = self.client.get('/api/leaderboard/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should only have 2 users (user2 and user3)
        self.assertEqual(len(data), 2)
        
        # user2 should be first (10 karma)
        self.assertEqual(data[0]['username'], 'user2')
        self.assertEqual(data[0]['total_karma'], 10)
        self.assertEqual(data[0]['rank'], 1)
        
        # user3 should be second (5 karma)
        self.assertEqual(data[1]['username'], 'user3')
        self.assertEqual(data[1]['total_karma'], 5)
        self.assertEqual(data[1]['rank'], 2)
        
        # user1 should NOT appear (karma is too old)
        usernames = [entry['username'] for entry in data]
        self.assertNotIn('user1', usernames)
    
    def test_leaderboard_exactly_24_hours(self):
        """
        Test edge case: karma at exactly 24 hours ago.
        
        Due to >= comparison, karma at exactly 24 hours should be included.
        """
        now = timezone.now()
        
        # Create karma at exactly 24 hours ago
        karma = KarmaTransaction.objects.create(
            user=self.user1,
            points=10,
            source_type='post_like',
            source_id=1
        )
        KarmaTransaction.objects.filter(pk=karma.pk).update(
            created_at=now - timedelta(hours=24)
        )
        
        response = self.client.get('/api/leaderboard/')
        data = response.json()
        
        # Should include user1
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['username'], 'user1')


class DoubleLikePreventionTest(APITestCase):
    """
    Test that double-likes are prevented at the DB level.
    """
    
    def setUp(self):
        """Create test user and post."""
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.author = User.objects.create_user(
            username='author', password='testpass123'
        )
        self.post = Post.objects.create(
            body='Test post',
            author=self.author
        )
        self.client.force_authenticate(user=self.user)
    
    def test_double_like_returns_409(self):
        """
        Attempting to like the same post twice should return 409 Conflict.
        """
        # First like should succeed
        response1 = self.client.post('/api/like/', {'post': self.post.id})
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Second like should fail with 409
        response2 = self.client.post('/api/like/', {'post': self.post.id})
        self.assertEqual(response2.status_code, status.HTTP_409_CONFLICT)
    
    def test_db_constraint_prevents_double_like(self):
        """
        Test that DB constraint raises IntegrityError on double-like.
        """
        # Create first like
        Like.objects.create(user=self.user, post=self.post)
        
        # Attempt to create duplicate should raise IntegrityError
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Like.objects.create(user=self.user, post=self.post)


class KarmaTransactionTest(APITestCase):
    """
    Test karma transaction creation on likes.
    """
    
    def setUp(self):
        """Create test users and content."""
        self.liker = User.objects.create_user(
            username='liker', password='testpass123'
        )
        self.author = User.objects.create_user(
            username='author', password='testpass123'
        )
        self.post = Post.objects.create(
            body='Test post',
            author=self.author
        )
        self.comment = Comment.objects.create(
            post=self.post,
            body='Test comment',
            author=self.author
        )
        self.client.force_authenticate(user=self.liker)
    
    def test_post_like_creates_5_karma(self):
        """Liking a post should give author +5 karma."""
        response = self.client.post('/api/like/', {'post': self.post.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check karma transaction
        karma = KarmaTransaction.objects.get(user=self.author)
        self.assertEqual(karma.points, 5)
        self.assertEqual(karma.source_type, 'post_like')
    
    def test_comment_like_creates_1_karma(self):
        """Liking a comment should give author +1 karma."""
        response = self.client.post('/api/like/', {'comment': self.comment.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check karma transaction
        karma = KarmaTransaction.objects.get(user=self.author)
        self.assertEqual(karma.points, 1)
        self.assertEqual(karma.source_type, 'comment_like')


class CommentTreeBuildingTest(TestCase):
    """
    Test that comment trees are built correctly.
    """
    
    def setUp(self):
        """Create nested comment structure."""
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.post = Post.objects.create(
            body='Test post',
            author=self.user
        )
        
        # Create comment tree:
        # - comment1 (root)
        #   - comment2 (child of 1)
        #     - comment4 (child of 2)
        #   - comment3 (child of 1)
        # - comment5 (root)
        
        self.comment1 = Comment.objects.create(
            post=self.post, body='Comment 1', author=self.user
        )
        self.comment2 = Comment.objects.create(
            post=self.post, body='Comment 2', author=self.user, parent=self.comment1
        )
        self.comment3 = Comment.objects.create(
            post=self.post, body='Comment 3', author=self.user, parent=self.comment1
        )
        self.comment4 = Comment.objects.create(
            post=self.post, body='Comment 4', author=self.user, parent=self.comment2
        )
        self.comment5 = Comment.objects.create(
            post=self.post, body='Comment 5', author=self.user
        )
    
    def test_tree_building(self):
        """Test that _build_comment_tree produces correct structure."""
        viewset = PostViewSet()
        comments = list(Comment.objects.filter(post=self.post).order_by('created_at'))
        
        tree = viewset._build_comment_tree(comments)
        
        # Should have 2 root comments
        self.assertEqual(len(tree), 2)
        
        # First root should be comment1
        self.assertEqual(tree[0].id, self.comment1.id)
        # comment1 should have 2 children (comment2 and comment3)
        self.assertEqual(len(tree[0]._children), 2)
        
        # comment2 should have 1 child (comment4)
        comment2_in_tree = tree[0]._children[0]
        self.assertEqual(len(comment2_in_tree._children), 1)
        self.assertEqual(comment2_in_tree._children[0].id, self.comment4.id)
        
        # Second root should be comment5 with no children
        self.assertEqual(tree[1].id, self.comment5.id)
        self.assertEqual(len(tree[1]._children), 0)
