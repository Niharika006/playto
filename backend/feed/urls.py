"""
URL configuration for the Feed API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import PostViewSet, CommentViewSet, LikeView, LeaderboardView
from .auth_views import RegisterView, LoginView, MeView, LogoutView

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
    path('like/', LikeView.as_view(), name='like'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    
    # Authentication endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
