# Technical Explainer

This document explains the key technical decisions and implementations in the Community Feed application.

## Table of Contents

1. [Nested Comments: Modeling and Fetching](#1-nested-comments-modeling-and-fetching)
2. [Leaderboard Query](#2-leaderboard-query)
3. [AI-Generated Code Fix Example](#3-ai-generated-code-fix-example)
4. [Additional Performance Decisions](#4-additional-performance-decisions)

---

## 1. Nested Comments: Modeling and Fetching

### The Problem

Comments can be nested infinitely (replies to replies to replies...). A naive implementation would result in **N+1 queries**:

```python
# BAD: N+1 query pattern
def get_comments_naive(post):
    comments = Comment.objects.filter(post=post, parent=None)  # 1 query
    for comment in comments:
        comment.replies = Comment.objects.filter(parent=comment)  # N queries!
        for reply in comment.replies:
            reply.replies = Comment.objects.filter(parent=reply)  # N² queries!!
```

For a post with 100 comments, this could result in 100+ database queries.

### The Solution: Adjacency List + In-Memory Tree Building

#### Model Design

```python
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', null=True, blank=True, 
                               on_delete=models.CASCADE, related_name='replies')
    body = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['post', 'created_at']),  # For fetching all comments
            models.Index(fields=['parent']),              # For tree building
        ]
```

#### Fetching Strategy

1. **Single Query**: Fetch ALL comments for a post in ONE query
2. **Build Tree in Python**: Construct the nested structure in O(n) time

```python
def retrieve(self, request, *args, **kwargs):
    post = self.get_object()
    
    # ONE query to get ALL comments for this post
    comments = Comment.objects.filter(post=post).select_related(
        'author'
    ).annotate(
        like_count=Count('likes', distinct=True)
    ).order_by('created_at')
    
    # Build tree in Python (O(n) time and space)
    comment_tree = self._build_comment_tree(list(comments))
    post._comment_tree = comment_tree
    
    return Response(PostDetailSerializer(post).data)

def _build_comment_tree(self, comments):
    """
    Algorithm: O(n) time, O(n) space
    
    1. Initialize empty _children list for each comment
    2. Create lookup dict: id -> comment
    3. Single pass: attach each comment to its parent
    4. Return only root comments (parent=None)
    """
    # Initialize children lists
    for comment in comments:
        comment._children = []
    
    # Build lookup dictionary
    comment_map = {comment.id: comment for comment in comments}
    
    # Build tree structure
    roots = []
    for comment in comments:
        if comment.parent_id is None:
            roots.append(comment)
        else:
            parent = comment_map.get(comment.parent_id)
            if parent:
                parent._children.append(comment)
    
    return roots
```

### Why Not Use django-mptt or django-treebeard?

**Considered:**
- `django-mptt`: Modified Preorder Tree Traversal
- `django-treebeard`: Nested sets, materialized paths

**Rejected because:**

1. **Added Complexity**: These libraries add `lft`, `rgt`, `tree_id`, `level` fields
2. **Write Overhead**: Tree must be rebuilt on every insert/delete/move
3. **Our Use Case is Simple**: We always fetch ALL comments for ONE post
4. **No Benefit**: These libraries optimize for "get all descendants of X" which we don't need

**Our approach**:
- 1 query regardless of nesting depth
- O(n) Python processing (fast in-memory)
- Simple model with self-referential FK
- Easy to understand and maintain

---

## 2. Leaderboard Query

### Requirements

- Top 5 users by karma earned in the **last 24 hours**
- Must be calculated dynamically (not cached)
- Must be efficient (< 50ms typical)

### The Query

```python
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum

def get(self, request):
    # Calculate 24-hour cutoff
    cutoff = timezone.now() - timedelta(hours=24)
    
    # Single aggregation query
    leaderboard = KarmaTransaction.objects.filter(
        created_at__gte=cutoff
    ).values(
        'user_id'
    ).annotate(
        total_karma=Sum('points')
    ).order_by(
        '-total_karma'
    )[:5]
    
    return Response(leaderboard)
```

### Equivalent SQL

```sql
SELECT 
    user_id, 
    SUM(points) as total_karma
FROM feed_karmatransaction
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY user_id
ORDER BY total_karma DESC
LIMIT 5;
```

### Index Design

```python
class KarmaTransaction(models.Model):
    # ...fields...
    
    class Meta:
        indexes = [
            # CRITICAL for leaderboard query
            # Enables efficient: WHERE created_at >= X GROUP BY user_id
            models.Index(fields=['created_at', 'user']),
            
            # For user karma history
            models.Index(fields=['user', '-created_at']),
        ]
```

### Query Plan Analysis

With the `(created_at, user)` index:

1. **Index Range Scan**: Filter rows where `created_at >= cutoff`
2. **HashAggregate**: Group by `user_id`, sum `points`
3. **Sort**: Order by `total_karma DESC`
4. **Limit**: Return top 5

Expected execution time: **5-20ms** for thousands of transactions.

### Why Not Cache?

We chose dynamic calculation because:
1. **Data is time-sensitive**: 24-hour window constantly shifts
2. **Freshness matters**: Users expect real-time leaderboard
3. **Query is fast enough**: With proper indexes, < 50ms is acceptable
4. **Simplicity**: No cache invalidation logic needed

For higher traffic, consider:
- 60-second cache with `django.core.cache`
- Background task that updates cached leaderboard

---

## 3. AI-Generated Code Fix Example

### The Bug: Recursive Serializer Causing Infinite Loop

**Initial AI-generated code:**

```python
class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    # BUG: This causes infinite recursion for deeply nested comments
    # and generates N+1 queries
    children = CommentSerializer(many=True, source='replies')
    
    class Meta:
        model = Comment
        fields = ['id', 'body', 'author', 'children']
```

**Problems:**
1. `replies` uses the related_name which triggers DB query per comment
2. Recursive serializer definition doesn't work properly in DRF
3. No control over query optimization

**Fixed code:**

```python
class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = ['id', 'body', 'author', 'children', 'like_count']
    
    def get_children(self, obj):
        """
        Return pre-built children list.
        
        Children are attached by the view's _build_comment_tree()
        method - NOT fetched via DB query here.
        """
        children = getattr(obj, '_children', [])
        return CommentSerializer(children, many=True, context=self.context).data
```

**Key insight:** The AI suggested using DRF's built-in related field handling, but this doesn't scale for tree structures. The fix separates:
1. **Data fetching** (one query in view)
2. **Tree building** (O(n) in Python)
3. **Serialization** (recursive but no DB calls)

---

## 4. Additional Performance Decisions

### Like Uniqueness via DB Constraints

**Why not application-level checks?**

```python
# BAD: Race condition vulnerable
def like_post(user, post):
    if Like.objects.filter(user=user, post=post).exists():  # Check
        return "Already liked"
    Like.objects.create(user=user, post=post)  # Create
    # Between check and create, another request could create the like!
```

**Solution: DB constraints + IntegrityError handling**

```python
class Like(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'post'],
                name='unique_user_post_like',
                condition=models.Q(post__isnull=False)
            ),
        ]

# In view:
try:
    with transaction.atomic():
        like = Like.objects.create(user=request.user, post=post)
        KarmaTransaction.objects.create(...)
except IntegrityError:
    return Response({'error': 'Already liked'}, status=409)
```

### Karma Not Stored on User Model

**Why avoid `User.karma` field?**

1. **Race conditions**: Two simultaneous likes could both read karma=10, add 5, write 15 (losing 5 karma)
2. **Time-based queries impossible**: Can't compute "karma in last 24h" from a single field
3. **Audit trail lost**: Can't trace karma back to source

**KarmaTransaction pattern:**
- Every karma event is a row
- Total = `SUM(points)` (always correct)
- Time-filtered totals = `SUM(points) WHERE created_at >= X`
- Full audit trail for debugging/disputes

### select_related vs prefetch_related

```python
# select_related: For ForeignKey/OneToOne (SQL JOIN)
Post.objects.select_related('author')  # 1 query with JOIN

# prefetch_related: For reverse FK/ManyToMany (separate query + Python join)
Post.objects.prefetch_related('comments')  # 2 queries, joined in Python
```

We use `select_related('author')` because:
- Author is a ForeignKey (single related object)
- Single JOIN is efficient
- Always need author data

We DON'T use `prefetch_related('comments')` on list view because:
- Comments are only needed on detail view
- Would fetch all comments for all posts in list

---

## Summary of Performance Guarantees

| Operation | Queries | Complexity |
|-----------|---------|------------|
| List posts | 1 | O(n) |
| Get post with comments | 2 | O(n + m) where m = comments |
| Like post/comment | 2 | O(1) |
| Get leaderboard | 2 | O(k log k) where k = users with karma |

All operations are designed to be **constant or linear** in database queries, never quadratic (N+1).
