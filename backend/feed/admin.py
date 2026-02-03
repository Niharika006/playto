from django.contrib import admin
from .models import Post, Comment, Like, KarmaTransaction


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'created_at', 'body_preview']
    list_filter = ['created_at', 'author']
    search_fields = ['body', 'author__username']
    
    def body_preview(self, obj):
        return obj.body[:50] + '...' if len(obj.body) > 50 else obj.body


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'post', 'parent', 'author', 'created_at']
    list_filter = ['created_at', 'author']
    search_fields = ['body', 'author__username']


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'post', 'comment', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username']


@admin.register(KarmaTransaction)
class KarmaTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'points', 'source_type', 'source_id', 'created_at']
    list_filter = ['source_type', 'created_at']
    search_fields = ['user__username']
