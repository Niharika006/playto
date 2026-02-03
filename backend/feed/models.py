"""
Models for the Community Feed application.

Design decisions:
1. Comments use self-referential FK for threading (no tree library needed)
2. Likes use unique_together constraint at DB level to prevent double-likes
3. KarmaTransaction stores all karma events for aggregation queries
4. Indexes are added for common query patterns (time-based filtering, FKs)

Performance considerations:
- No N+1 queries: Comments are fetched in one query and tree built in Python
- Karma is NEVER stored on User model - always computed from KarmaTransaction
- Unique constraints prevent race conditions at DB level
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Post(models.Model):
    """
    A post in the feed.
    
    Indexes:
    - created_at: For ordering posts by time
    - author: For filtering posts by user
    """
    body = models.TextField()
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='posts'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['author', '-created_at']),
        ]
    
    def __str__(self):
        return f"Post {self.id} by {self.author.username}"


class Comment(models.Model):
    """
    Threaded comment model with self-referential FK.
    
    Design: Using adjacency list pattern (parent FK) because:
    1. Simple to understand and maintain
    2. Efficient writes (just set parent_id)
    3. Can fetch ALL comments for a post in ONE query
    4. Tree is built in Python memory (O(n) time, O(n) space)
    
    Alternative considered: django-mptt or django-treebeard
    Rejected because:
    - Adds complexity with left/right/level fields
    - Requires tree rebuilds on modifications
    - Our use case (fetch all comments for one post) doesn't benefit much
    
    Indexes:
    - post + created_at: For fetching all comments for a post ordered by time
    - parent: For identifying root vs nested comments
    """
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='replies'
    )
    body = models.TextField()
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            # Composite index for fetching all comments for a post
            models.Index(fields=['post', 'created_at']),
            # Index for parent lookups when building tree
            models.Index(fields=['parent']),
        ]
    
    def __str__(self):
        return f"Comment {self.id} on Post {self.post_id}"


class Like(models.Model):
    """
    Like model supporting both posts and comments.
    
    CRITICAL: Uses unique_together constraint to prevent double-likes at DB level.
    This is the ONLY reliable way to prevent race conditions.
    Application-level checks are not sufficient due to TOCTOU vulnerabilities.
    
    Design: Using nullable FKs for post/comment (polymorphic association).
    Alternative: Generic relations (ContentType framework)
    Rejected because:
    - Less efficient queries (extra join to content_type table)
    - More complex to reason about
    - We only have 2 target types
    
    Constraint ensures exactly one of post/comment is set via clean() validation.
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='likes'
    )
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='likes'
    )
    comment = models.ForeignKey(
        Comment, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # DB-level constraint: one like per user per post
        # DB-level constraint: one like per user per comment
        # These constraints are enforced at the database level
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'post'],
                name='unique_user_post_like',
                condition=models.Q(post__isnull=False)
            ),
            models.UniqueConstraint(
                fields=['user', 'comment'],
                name='unique_user_comment_like',
                condition=models.Q(comment__isnull=False)
            ),
        ]
        indexes = [
            models.Index(fields=['post']),
            models.Index(fields=['comment']),
            models.Index(fields=['user']),
        ]
    
    def clean(self):
        """
        Validate that exactly one of post or comment is set.
        This is application-level validation; DB constraints handle uniqueness.
        """
        if self.post and self.comment:
            raise ValidationError("Like must be for either a post or comment, not both.")
        if not self.post and not self.comment:
            raise ValidationError("Like must be for either a post or a comment.")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        target = f"Post {self.post_id}" if self.post else f"Comment {self.comment_id}"
        return f"Like by {self.user.username} on {target}"


class KarmaTransaction(models.Model):
    """
    Immutable record of karma events.
    
    DESIGN PRINCIPLE: Karma is NEVER stored on User model.
    Total karma is always computed by SUM(points) GROUP BY user.
    
    Why not denormalize to User.karma field?
    1. Consistency: Single source of truth avoids sync issues
    2. Auditability: Can trace every point back to its source
    3. Time-based queries: Can compute karma for any time window
    4. No race conditions: Aggregation is always correct
    
    Tradeoff: Reading total karma requires aggregation query.
    Mitigation: Index on (user, created_at) makes this fast.
    For leaderboard, we only aggregate recent transactions anyway.
    
    source_type + source_id: Polymorphic reference to Like that triggered this.
    This allows tracing karma back to specific likes.
    """
    SOURCE_TYPE_CHOICES = [
        ('post_like', 'Post Like'),
        ('comment_like', 'Comment Like'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='karma_transactions',
        help_text="User who received the karma"
    )
    points = models.IntegerField(
        help_text="Karma points: +5 for post like, +1 for comment like"
    )
    source_type = models.CharField(
        max_length=20, 
        choices=SOURCE_TYPE_CHOICES,
        help_text="Type of action that generated this karma"
    )
    source_id = models.PositiveIntegerField(
        help_text="ID of the Like that generated this karma"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            # CRITICAL INDEX for leaderboard query:
            # Allows efficient filtering by created_at and grouping by user
            models.Index(fields=['created_at', 'user']),
            # Index for user's karma history
            models.Index(fields=['user', '-created_at']),
            # Index for deduplication checks
            models.Index(fields=['source_type', 'source_id']),
        ]
    
    def __str__(self):
        return f"{self.points} karma to {self.user.username} from {self.source_type}"
