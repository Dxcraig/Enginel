"""
URL configuration for enginel project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from designs.views import (
    OrganizationViewSet,
    CustomUserViewSet,
    DesignSeriesViewSet,
    DesignAssetViewSet,
    AssemblyNodeViewSet,
    AnalysisJobViewSet,
    ReviewSessionViewSet,
    MarkupViewSet,
    AuditLogViewSet,
    health_check,
    health_detailed,
    monitoring_dashboard,
    error_logs,
    performance_stats,
    notification_preferences,
    notification_history,
    notification_stats,
    test_notification,
    ValidationRuleViewSet,
    ValidationResultViewSet,
    ValidateFieldView,
    ValidateBatchView,
    ValidationReportView,
    ValidationStatisticsView,
)
from designs.auth_views import (
    login_view,
    logout_view,
    refresh_token_view,
    revoke_token_view,
    verify_token_view,
    list_sessions_view,
    revoke_api_key_view,
    APIKeyListCreateView,
    APIKeyDetailView,
)

# Create API router
router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'series', DesignSeriesViewSet, basename='series')
router.register(r'designs', DesignAssetViewSet, basename='design')
router.register(r'bom-nodes', AssemblyNodeViewSet, basename='bom-node')
router.register(r'analysis-jobs', AnalysisJobViewSet, basename='analysis-job')
router.register(r'reviews', ReviewSessionViewSet, basename='review')
router.register(r'markups', MarkupViewSet, basename='markup')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
router.register(r'validation/rules', ValidationRuleViewSet, basename='validation-rule')
router.register(r'validation/results', ValidationResultViewSet, basename='validation-result')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    
    # Authentication endpoints
    path('api/auth/login/', login_view, name='auth-login'),
    path('api/auth/logout/', logout_view, name='auth-logout'),
    path('api/auth/refresh/', refresh_token_view, name='auth-refresh'),
    path('api/auth/revoke/', revoke_token_view, name='auth-revoke'),
    path('api/auth/verify/', verify_token_view, name='auth-verify'),
    path('api/auth/sessions/', list_sessions_view, name='auth-sessions'),
    
    # API Key management
    path('api/auth/api-keys/', APIKeyListCreateView.as_view(), name='apikey-list-create'),
    path('api/auth/api-keys/<int:pk>/', APIKeyDetailView.as_view(), name='apikey-detail'),
    path('api/auth/api-keys/<int:pk>/revoke/', revoke_api_key_view, name='apikey-revoke'),
    
    # Health check endpoints
    path('api/health/', health_check, name='health-check'),
    path('api/health/detailed/', health_detailed, name='health-detailed'),
    
    # Monitoring endpoints (admin only)
    path('api/monitoring/dashboard/', monitoring_dashboard, name='monitoring-dashboard'),
    path('api/monitoring/errors/', error_logs, name='error-logs'),
    path('api/monitoring/performance/', performance_stats, name='performance-stats'),
    
    # Notification endpoints
    path('api/notifications/preferences/', notification_preferences, name='notification-preferences'),
    path('api/notifications/history/', notification_history, name='notification-history'),
    path('api/notifications/stats/', notification_stats, name='notification-stats'),
    path('api/notifications/test/', test_notification, name='test-notification'),
    
    # Validation endpoints
    path('api/validation/validate-field/', ValidateFieldView.as_view(), name='validate-field'),
    path('api/validation/validate-batch/', ValidateBatchView.as_view(), name='validate-batch'),
    path('api/validation/report/', ValidationReportView.as_view(), name='validation-report'),
    path('api/validation/statistics/', ValidationStatisticsView.as_view(), name='validation-statistics'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
