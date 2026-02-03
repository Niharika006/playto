"""
Views for the Community Feed API.

Key performance optimizations:
1. Posts: Annotated with like_count and comment_count to avoid N+1
2. Comments: Fetched in ONE query, tree built in Python O(n)
3. Leaderboard: Single aggregation query with proper indexes
4. Likes: Wrapped in transaction.atomic() with IntegrityError handling
"""
from datetime import timedelta
from collections import defaultdict

from django.db import transaction, IntegrityError
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.contrib.auth.models import User

from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from .models import Post, Comment, Like, KarmaTransaction
from .serializers import (
    PostSerializer, PostDetailSerializer, CommentSerializer,
    LikeSerializer, LeaderboardEntrySerializer
)


class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for posts with optimized queries.
    
    List view: Annotates like_count and comment_count to avoid N+1.
    Detail view: Includes full comment tree built efficiently.
    """
    permission_classes = []  # Read: anyone, Write: checked in perform_create
    
    def perform_create(self, serializer):
        """Create post with authenticated user as author."""
        if not self.request.user.is_authenticated:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('You must be logged in to create a post')
        serializer.save(author=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PostDetailSerializer
        return PostSerializer
    
    def get_queryset(self):
        """
        Return posts with annotated counts.
        
        Query explanation:
        - select_related('author'): Single JOIN for author data
        - annotate(like_count): COUNT of related likes
        - annotate(comment_count): COUNT of related comments
        
        This produces ONE query regardless of result size.
        """
        return Post.objects.select_related('author').annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True)
        ).order_by('-created_at')
    
    def retrieve(self, request, *args, **kwargs):
        """
        Get single post with full comment tree.
        
        Performance strategy:
        1. Fetch post with annotations
        2. Fetch ALL comments for post in ONE query
        3. Build tree in Python (O(n) time and space)
        4. Attach tree to post for serialization
        """
        post = self.get_object()
        
        # Fetch all comments for this post in ONE query
        # This is the key optimization: no recursive queries
        comments = Comment.objects.filter(post=post).select_related(
            'author'
        ).annotate(
            like_count=Count('likes', distinct=True)
        ).order_by('created_at')
        
        # Build tree structure in Python
        comment_tree = self._build_comment_tree(list(comments))
        
        # Attach tree to post for serializer
        post._comment_tree = comment_tree
        
        serializer = self.get_serializer(post)
        return Response(serializer.data)
    
    def _build_comment_tree(self, comments):
        """
        Build nested comment tree from flat list.
        
        Algorithm: O(n) time and space complexity
        1. Create lookup dict: id -> comment
        2. Iterate once, attaching each comment to its parent
        3. Return only root comments (parent=None)
        
        Why not recursive queries?
        - Recursive queries = N+1 problem
        - This approach: 1 query + O(n) Python processing
        - For 1000 comments: 1 query vs potentially 1000 queries
        
        Why not use django-mptt or similar?
        - Adds complexity with left/right/depth fields
        - Requires tree rebuilds on modifications
        - Our read pattern (all comments for one post) is simple enough
        """
        # Initialize _children list for all comments
        for comment in comments:
            comment._children = []
        
        # Build lookup dictionary
        comment_map = {comment.id: comment for comment in comments}
        
        # Build tree structure
        roots = []
        for comment in comments:
            if comment.parent_id is None:
                # Root comment (no parent)
                roots.append(comment)
            else:
                # Child comment - attach to parent
                parent = comment_map.get(comment.parent_id)
                if parent:
                    parent._children.append(comment)
        
        return roots


class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for creating and managing comments.
    
    Note: Comment trees are fetched via PostDetailSerializer.
    This viewset is primarily for CRUD operations.
    """
    serializer_class = CommentSerializer
    permission_classes = []  # Read: anyone, Write: checked in perform_create
    
    def get_queryset(self):
        """Return comments with author and like count."""
        return Comment.objects.select_related('author').annotate(
            like_count=Count('likes', distinct=True)
        )
    
    def perform_create(self, serializer):
        """Create comment with authenticated user as author."""
        if not self.request.user.is_authenticated:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('You must be logged in to comment')
        serializer.save(author=self.request.user)


class LikeView(views.APIView):
    """
    API endpoint for liking/unliking posts and comments.
    
    CRITICAL: Uses transaction.atomic() and handles IntegrityError
    to prevent double-likes even under race conditions.
    
    Concurrency handling:
    1. DB unique constraint prevents duplicate likes
    2. transaction.atomic() ensures like + karma are atomic
    3. IntegrityError caught and returns appropriate response
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Create a like on a post or comment.
        
        Request body:
        - post: Post ID (optional, mutually exclusive with comment)
        - comment: Comment ID (optional, mutually exclusive with post)
        
        Concurrency safety:
        - Uses transaction.atomic() to ensure atomicity
        - DB constraint catches race conditions
        - IntegrityError indicates already liked
        """
        serializer = LikeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        post_id = serializer.validated_data.get('post')
        comment_id = serializer.validated_data.get('comment')
        
        try:
            with transaction.atomic():
                # Create the like
                like = Like.objects.create(
                    user=request.user,
                    post=post_id,
                    comment=comment_id
                )
                
                # Create karma transaction for content author
                # This is atomic with the like creation
                self._create_karma_transaction(like)
                
                return Response(
                    {'id': like.id, 'message': 'Liked successfully'},
                    status=status.HTTP_201_CREATED
                )
                
        except IntegrityError:
            # This catches the unique constraint violation
            # This is the CORRECT way to handle race conditions
            return Response(
                {'error': 'Already liked'},
                status=status.HTTP_409_CONFLICT
            )
    
    def delete(self, request):
        """
        Remove a like from a post or comment.
        
        Also removes the associated karma transaction.
        """
        post_id = request.data.get('post')
        comment_id = request.data.get('comment')
        
        if not post_id and not comment_id:
            return Response(
                {'error': 'Must provide post or comment'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Find and delete the like
                if post_id:
                    like = Like.objects.get(user=request.user, post_id=post_id)
                else:
                    like = Like.objects.get(user=request.user, comment_id=comment_id)
                
                like_id = like.id
                source_type = 'post_like' if post_id else 'comment_like'
                
                # Delete karma transaction first (referential integrity)
                KarmaTransaction.objects.filter(
                    source_type=source_type,
                    source_id=like_id
                ).delete()
                
                # Delete the like
                like.delete()
                
                return Response(status=status.HTTP_204_NO_CONTENT)
                
        except Like.DoesNotExist:
            return Response(
                {'error': 'Like not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def _create_karma_transaction(self, like):
        """
        Create karma transaction for the content author.
        
        Karma values:
        - Post like: +5 karma to post author
        - Comment like: +1 karma to comment author
        
        Note: This runs inside the same transaction as the like creation.
        If either fails, both are rolled back.
        """
        if like.post:
            # Post like gives +5 karma
            KarmaTransaction.objects.create(
                user=like.post.author,
                points=5,
                source_type='post_like',
                source_id=like.id
            )
        else:
            # Comment like gives +1 karma
            KarmaTransaction.objects.create(
                user=like.comment.author,
                points=1,
                source_type='comment_like',
                source_id=like.id
            )


class LeaderboardView(views.APIView):
    """
    API endpoint for karma leaderboard.
    
    Returns top 5 users by karma earned in the last 24 hours.
    
    Query optimization:
    - Uses index on (created_at, user) for efficient filtering
    - Single aggregation query with GROUP BY and ORDER BY
    - No application-level filtering or sorting
    """
    permission_classes = []  # Public endpoint
    
    def get(self, request):
        """
        Get top 5 users by karma in last 24 hours.
        
        SQL equivalent:
        SELECT user_id, SUM(points) as total_karma
        FROM karma_transaction
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY user_id
        ORDER BY total_karma DESC
        LIMIT 5
        
        The index on (created_at, user) makes this query efficient:
        1. Index scan filters by created_at >= cutoff
        2. Results grouped by user_id
        3. Sorted by total_karma descending
        4. Limited to 5 results
        
        Expected query plan: Index Scan + HashAggregate + Sort + Limit
        """
        # Calculate 24-hour cutoff
        cutoff = timezone.now() - timedelta(hours=24)
        
        # Single aggregation query
        # This leverages the index on (created_at, user)
        leaderboard = KarmaTransaction.objects.filter(
            created_at__gte=cutoff
        ).values(
            'user_id'
        ).annotate(
            total_karma=Sum('points')
        ).order_by(
            '-total_karma'
        )[:5]
        
        # Fetch usernames in one query
        user_ids = [entry['user_id'] for entry in leaderboard]
        users = User.objects.filter(id__in=user_ids).values('id', 'username')
        user_map = {u['id']: u['username'] for u in users}
        
        # Build response with rank
        result = []
        for rank, entry in enumerate(leaderboard, start=1):
            result.append({
                'rank': rank,
                'user_id': entry['user_id'],
                'username': user_map.get(entry['user_id'], 'Unknown'),
                'total_karma': entry['total_karma']
            })
        
        serializer = LeaderboardEntrySerializer(result, many=True)
        return Response(serializer.data)
