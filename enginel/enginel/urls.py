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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    
    # Health check endpoints
    path('api/health/', health_check, name='health-check'),
    path('api/health/detailed/', health_detailed, name='health-detailed'),
    
    # Monitoring endpoints (admin only)
    path('api/monitoring/dashboard/', monitoring_dashboard, name='monitoring-dashboard'),
    path('api/monitoring/errors/', error_logs, name='error-logs'),
    path('api/monitoring/performance/', performance_stats, name='performance-stats'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
