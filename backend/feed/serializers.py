"""
Serializers for the Community Feed API.

Design decisions:
1. PostSerializer includes like_count as annotated field
2. CommentSerializer is recursive for nested structure
3. LeaderboardSerializer is read-only for aggregation results
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Post, Comment, Like, KarmaTransaction


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested representations."""
    
    class Meta:
        model = User
        fields = ['id', 'username']


class CommentSerializer(serializers.ModelSerializer):
    """
    Comment serializer with nested author and children.
    
    Note: 'children' is populated by the view after tree construction.
    This avoids recursive DB queries.
    """
    author = UserSerializer(read_only=True)
    like_count = serializers.IntegerField(read_only=True, default=0)
    children = serializers.SerializerMethodField()
    user_has_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'parent', 'body', 'author', 
            'created_at', 'like_count', 'children', 'user_has_liked'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'like_count']
    
    def get_children(self, obj):
        """
        Return pre-built children list.
        
        IMPORTANT: Children are attached by the view's build_comment_tree()
        function to avoid N+1 queries. This method just returns them.
        """
        # Children are attached dynamically by the view
        children = getattr(obj, '_children', [])
        return CommentSerializer(children, many=True, context=self.context).data
    
    def get_user_has_liked(self, obj):
        """Check if current user has liked this comment."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Uses prefetched likes if available
            user_id = request.user.id
            likes = getattr(obj, '_prefetched_likes', None)
            if likes is not None:
                return any(like.user_id == user_id for like in likes)
            return obj.likes.filter(user_id=user_id).exists()
        return False


class PostSerializer(serializers.ModelSerializer):
    """
    Post serializer with author details and like count.
    
    Performance: like_count is expected to be annotated by the view
    using Count() to avoid N+1 queries.
    """
    author = UserSerializer(read_only=True)
    like_count = serializers.IntegerField(read_only=True, default=0)
    comment_count = serializers.IntegerField(read_only=True, default=0)
    user_has_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'body', 'author', 'created_at', 
            'like_count', 'comment_count', 'user_has_liked'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'like_count', 'comment_count']
    
    def get_user_has_liked(self, obj):
        """Check if current user has liked this post."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user_id = request.user.id
            # Use prefetched data if available
            likes = getattr(obj, '_prefetched_likes', None)
            if likes is not None:
                return any(like.user_id == user_id for like in likes)
            return obj.likes.filter(user_id=user_id).exists()
        return False


class PostDetailSerializer(PostSerializer):
    """
    Extended post serializer including comments tree.
    
    The comments field contains the full nested comment tree,
    built efficiently in one query by the view.
    """
    comments = serializers.SerializerMethodField()
    
    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ['comments']
    
    def get_comments(self, obj):
        """
        Return pre-built comment tree.
        
        The comment tree is built by the view and attached to the post
        as _comment_tree to avoid N+1 queries.
        """
        comment_tree = getattr(obj, '_comment_tree', [])
        return CommentSerializer(
            comment_tree, 
            many=True, 
            context=self.context
        ).data


class LikeSerializer(serializers.ModelSerializer):
    """Serializer for like creation."""
    
    class Meta:
        model = Like
        fields = ['id', 'post', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        """Ensure exactly one of post or comment is provided."""
        post = data.get('post')
        comment = data.get('comment')
        
        if post and comment:
            raise serializers.ValidationError(
                "Provide either 'post' or 'comment', not both."
            )
        if not post and not comment:
            raise serializers.ValidationError(
                "Must provide either 'post' or 'comment'."
            )
        return data


class LeaderboardEntrySerializer(serializers.Serializer):
    """
    Serializer for leaderboard entries.
    
    This is a read-only serializer for aggregation results.
    Fields come from the annotated queryset in the view.
    """
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    total_karma = serializers.IntegerField()
    rank = serializers.IntegerField()
