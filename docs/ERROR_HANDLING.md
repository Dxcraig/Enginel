# Error Handling & Monitoring

This document describes the comprehensive error handling and monitoring system in Enginel, providing production-grade observability for tracking errors, performance, and system health.

## Overview

The monitoring system provides:

1. **Error Tracking**: Centralized error logging with context, stack traces, and error aggregation
2. **Performance Monitoring**: Track operation duration and detect slow endpoints
3. **Health Checks**: Component status monitoring for load balancers and orchestration
4. **Metrics Collection**: Application-level metrics for dashboards and alerting
5. **Request Logging**: Detailed API request/response logging with user context
6. **Celery Task Monitoring**: Background task performance tracking with duration and failure metrics

## Architecture

### Core Components

#### 1. Exception Classes (`designs/exceptions.py`)

Custom exception hierarchy with HTTP status codes:

```python
from designs.exceptions import (
    GeometryProcessingError,      # 422 - CAD file parsing failed
    FileValidationError,           # 400 - Invalid file
    OrganizationLimitExceeded,     # 403 - Resource quota exceeded
    InsufficientPermissions,       # 403 - Insufficient role
    ITARViolation,                 # 403 - ITAR compliance violation
    StorageQuotaExceeded,          # 413 - Storage limit hit
    DesignNotReady,                # 409 - Design still processing
    TaskTimeoutError,              # 504 - Celery task timeout
    ExternalServiceError,          # 503 - S3/external service down
)
```

#### 2. Monitoring Utilities (`designs/monitoring.py`)

**ErrorTracker**: Centralized error logging
```python
from designs.monitoring import ErrorTracker

# Log error with context
ErrorTracker.log_error(
    error=exception,
    context={'design_id': design_id, 'step': 'geometry_extraction'},
    user_id=user.id,
    request_path='/api/designs/upload/',
    severity='ERROR'  # or 'CRITICAL', 'WARNING'
)

# Get recent errors
recent_errors = ErrorTracker.get_recent_errors(limit=50)
```

**PerformanceMonitor**: Track operation duration
```python
from designs.monitoring import PerformanceMonitor

# Decorator to track performance
@PerformanceMonitor.track_duration('geometry_extraction')
def extract_geometry(file_path):
    # ... processing ...
    pass

# Get stats
stats = PerformanceMonitor.get_operation_stats('geometry_extraction')
# Returns: {'count': 150, 'avg_duration': 12.5, 'max_duration': 45.2, 'error_rate': 0.02}
```

**MetricsCollector**: Application metrics
```python
from designs.monitoring import MetricsCollector

# Track counters
MetricsCollector.increment_counter('uploads_total')
MetricsCollector.increment_counter('uploads_step')

# Track gauges
MetricsCollector.record_gauge('active_users', 42)

# Get metrics snapshot
metrics = MetricsCollector.get_metrics()
```

**HealthChecker**: System health status
```python
from designs.monitoring import HealthChecker

# Check individual components
db_status = HealthChecker.check_database()
redis_status = HealthChecker.check_redis()
celery_status = HealthChecker.check_celery()

# Get full health report
health = HealthChecker.get_full_health_status()
```

#### 3. Middleware (`designs/middleware.py`)

Automatically applied to all requests:

- **ErrorTrackingMiddleware**: Catches and logs all exceptions
- **RequestLoggingMiddleware**: Logs API requests with duration
- **PerformanceMonitoringMiddleware**: Tracks endpoint performance
- **MetricsMiddleware**: Collects request metrics

## API Endpoints

### Health Check

Basic health check for load balancers:

```http
GET /api/health/
```

**Response:**
```json
{
    "status": "ok",
    "service": "enginel"
}
```

**Status Codes:**
- `200 OK`: Service is healthy

### Detailed Health Check

Comprehensive component status:

```http
GET /api/health/detailed/
```

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-12-16T10:30:00Z",
    "checks": {
        "database": {
            "status": "healthy",
            "message": "Database connection OK"
        },
        "redis": {
            "status": "healthy",
            "message": "Redis connection OK"
        },
        "celery": {
            "status": "healthy",
            "message": "16 worker(s) active",
            "workers": ["celery@worker1", "celery@worker2"]
        },
        "storage": {
            "status": "healthy",
            "message": "Storage accessible"
        }
    }
}
```

**Status Codes:**
- `200 OK`: All components healthy
- `503 Service Unavailable`: One or more components unhealthy

### Monitoring Dashboard

Comprehensive monitoring data (admin only):

```http
GET /api/monitoring/dashboard/
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
    "health": {
        "status": "healthy",
        "checks": {...}
    },
    "recent_errors": [
        {
            "timestamp": "2025-12-16T10:25:00Z",
            "error_type": "GeometryProcessingError",
            "error_message": "Failed to parse STEP file",
            "severity": "ERROR",
            "user_id": 5,
            "request_path": "/api/designs/123/finalize/",
            "context": {
                "design_id": "550e8400-e29b-41d4-a716-446655440000",
                "step": "geometry_extraction"
            },
            "traceback": "..."
        }
    ],
    "performance": {
        "geometry_extraction": {
            "count": 150,
            "avg_duration": 12.5,
            "max_duration": 45.2,
            "min_duration": 3.1,
            "error_count": 3,
            "error_rate": 0.02
        },
        "bom_extraction": {
            "count": 89,
            "avg_duration": 8.3,
            "max_duration": 25.7,
            "min_duration": 2.4,
            "error_count": 1,
            "error_rate": 0.011
        }
    },
    "metrics": {
        "timestamp": "2025-12-16T10:30:00Z",
        "uploads_total": 1247,
        "total_bytes_uploaded": 5368709120
    }
}
```

### Error Logs

Get recent error logs (admin only):

```http
GET /api/monitoring/errors/?limit=50
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
    "count": 15,
    "errors": [
        {
            "timestamp": "2025-12-16T10:25:00Z",
            "error_type": "GeometryProcessingError",
            "error_message": "Failed to parse STEP file",
            "severity": "ERROR",
            "user_id": 5,
            "request_path": "/api/designs/123/finalize/",
            "context": {...},
            "traceback": "..."
        }
    ]
}
```

### Performance Stats

Get performance statistics (admin only):

```http
GET /api/monitoring/performance/
Authorization: Bearer <admin_token>
```

## Usage Examples

### Raising Custom Exceptions

```python
from designs.exceptions import (
    GeometryProcessingError,
    OrganizationLimitExceeded,
    raise_geometry_error,
    raise_validation_error,
    raise_permission_error
)

# Direct raise
if not valid_step_file:
    raise GeometryProcessingError("Invalid STEP file format")

# Helper functions with context
try:
    parse_cad_file(file_path)
except Exception as e:
    raise_geometry_error("Failed to parse CAD file", original_exception=e)

# Validation error
if file_size > max_size:
    raise_validation_error("File too large", field="file")

# Permission error
if membership.role != 'ADMIN':
    raise_permission_error(required_role='ADMIN', current_role=membership.role)
```

### Tracking Errors in Views

```python
from rest_framework.views import APIView
from designs.monitoring import ErrorTracker
from designs.exceptions import GeometryProcessingError

class ProcessDesignView(APIView):
    def post(self, request, design_id):
        try:
            # Process design
            result = process_geometry(design_id)
            return Response(result)
        
        except GeometryProcessingError as e:
            # Error is automatically logged by ErrorTrackingMiddleware
            # But you can add extra context if needed
            ErrorTracker.log_error(
                error=e,
                context={
                    'design_id': design_id,
                    'organization': request.user.organization,
                },
                user_id=request.user.id,
                severity='ERROR'
            )
            raise  # Re-raise to return proper error response
```

### Monitoring Celery Tasks

```python
from celery import shared_task
from designs.monitoring import PerformanceMonitor, ErrorTracker, MetricsCollector
import time

@shared_task
@PerformanceMonitor.track_duration('custom_processing')
def custom_processing_task(design_id):
    start_time = time.time()
    status = 'SUCCESS'
    
    try:
        # Task processing
        result = do_processing(design_id)
        return result
    
    except Exception as e:
        status = 'FAILED'
        ErrorTracker.log_error(
            e,
            context={'design_id': design_id, 'task': 'custom_processing'},
            severity='ERROR'
        )
        raise
    
    finally:
        duration = time.time() - start_time
        MetricsCollector.track_celery_task(
            task_name='custom_processing',
            duration=duration,
            status=status
        )
```

### Manual Performance Tracking

```python
from designs.monitoring import PerformanceMonitor
import time

def complex_operation():
    start_time = time.time()
    error_occurred = False
    
    try:
        # ... complex processing ...
        result = process_data()
        return result
    
    except Exception as e:
        error_occurred = True
        raise
    
    finally:
        duration = time.time() - start_time
        PerformanceMonitor._record_duration(
            'complex_operation',
            duration,
            error_occurred
        )
```

## Exception Hierarchy

```
Exception
└── APIException (DRF)
    └── EnginelBaseException (500)
        ├── GeometryProcessingError (422)
        ├── FileValidationError (400)
        │   ├── InvalidFileFormat
        │   ├── FileSizeExceeded
        │   └── CorruptedFile
        ├── OrganizationLimitExceeded (403)
        ├── InsufficientPermissions (403)
        ├── ITARViolation (403)
        ├── ClearanceLevelInsufficient (403)
        ├── UnitConversionError (422)
        ├── BOMExtractionError (422)
        ├── StorageQuotaExceeded (413)
        ├── UserLimitExceeded (403)
        ├── DesignNotReady (409)
        ├── DuplicatePartNumber (409)
        ├── TaskTimeoutError (504)
        └── ExternalServiceError (503)
```

## Logging Configuration

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical errors requiring immediate attention

### Structured Logging

All errors are logged in JSON format for easy parsing:

```json
{
    "timestamp": "2025-12-16T10:30:00Z",
    "error_type": "GeometryProcessingError",
    "error_message": "Failed to parse STEP file",
    "severity": "ERROR",
    "user_id": 5,
    "request_path": "/api/designs/123/finalize/",
    "context": {
        "design_id": "550e8400-e29b-41d4-a716-446655440000",
        "file_format": "step"
    },
    "traceback": "Traceback (most recent call last):\n  File..."
}
```

## Metrics

### Available Metrics

#### Request Metrics
- `http_requests_total`: Total API requests
- `http_status_200`, `http_status_400`, etc.: Requests by status code
- `endpoint_designs`, `endpoint_series`, etc.: Requests by endpoint
- `api_requests_total`: Total API requests

#### Upload Metrics
- `uploads_total`: Total file uploads
- `uploads_step`, `uploads_iges`: Uploads by file type
- `total_bytes_uploaded`: Total bytes uploaded

#### Celery Metrics
- `celery_task_<task_name>`: Task execution count
- `celery_task_<task_name>_SUCCESS`: Successful executions
- `celery_task_<task_name>_FAILED`: Failed executions

### Metrics Retention

Metrics are stored in Redis with TTL:
- Counters: 24 hours
- Gauges: 5 minutes
- Recent errors: 1 hour (last 100 errors)
- Performance stats: 1 hour

## Performance Thresholds

### Slow Operation Detection

Operations are flagged as slow if they exceed:
- API requests: 5 seconds
- Geometry extraction: 30 seconds
- BOM extraction: 30 seconds
- File uploads: 60 seconds

Slow operations are automatically logged with WARNING level.

### Performance Stats

For each tracked operation, the system maintains:
- **Count**: Number of executions
- **Total Duration**: Sum of all execution times
- **Average Duration**: Mean execution time
- **Max Duration**: Longest execution
- **Min Duration**: Shortest execution
- **Error Count**: Number of failures
- **Error Rate**: Percentage of failed executions

## Health Check Integration

### Load Balancer Configuration

Configure your load balancer to use the basic health check:

**NGINX:**
```nginx
upstream enginel_backend {
    server web:8000;
    
    # Health check
    check interval=10000 rise=2 fall=3 timeout=3000 type=http;
    check_http_send "GET /api/health/ HTTP/1.0\r\n\r\n";
    check_http_expect_alive http_2xx;
}
```

**AWS Application Load Balancer:**
```yaml
HealthCheck:
  Path: /api/health/
  Protocol: HTTP
  Matcher:
    HttpCode: 200
  HealthyThresholdCount: 2
  UnhealthyThresholdCount: 3
  Timeout: 5
  Interval: 30
```

### Kubernetes Liveness/Readiness Probes

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: enginel-web
    livenessProbe:
      httpGet:
        path: /api/health/
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
      
    readinessProbe:
      httpGet:
        path: /api/health/detailed/
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 5
      failureThreshold: 3
```

## Monitoring Dashboard Setup

### Grafana Dashboard

Example Prometheus queries for Grafana:

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_status_500[5m]) / rate(http_requests_total[5m])

# Average response time
rate(api_request_duration_sum[5m]) / rate(api_request_duration_count[5m])

# Celery task success rate
rate(celery_task_SUCCESS[5m]) / rate(celery_task_total[5m])
```

### Alert Rules

Example alert rules:

```yaml
groups:
  - name: enginel_alerts
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(http_status_500[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          
      # Slow responses
      - alert: SlowResponses
        expr: histogram_quantile(0.95, rate(api_request_duration_bucket[5m])) > 5
        for: 10m
        annotations:
          summary: "95th percentile response time > 5s"
          
      # Celery workers down
      - alert: CeleryWorkersDown
        expr: celery_workers_active == 0
        for: 2m
        annotations:
          summary: "No Celery workers available"
          
      # Storage quota warning
      - alert: StorageQuotaWarning
        expr: storage_used_gb / storage_quota_gb > 0.9
        for: 15m
        annotations:
          summary: "Organization approaching storage limit"
```

## Production Recommendations

### 1. Centralized Logging

Integrate with logging services:
- **Sentry**: Automatic error tracking and alerting
- **DataDog**: APM and log aggregation
- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **CloudWatch Logs**: AWS-native logging

### 2. Metrics Backend

Use a proper metrics backend instead of Redis cache:
- **Prometheus**: Time-series metrics database
- **InfluxDB**: Time-series database
- **DataDog**: Full observability platform
- **CloudWatch Metrics**: AWS-native metrics

### 3. Distributed Tracing

Add distributed tracing for microservices:
- **Jaeger**: Open-source distributed tracing
- **Zipkin**: Distributed tracing system
- **DataDog APM**: Application performance monitoring

### 4. Error Aggregation

Configure error aggregation and deduplication:
- Group similar errors together
- Track error frequency over time
- Set up alerts for error spikes
- Auto-create tickets for critical errors

### 5. Performance Profiling

Enable performance profiling:
- Django Debug Toolbar (development only)
- Py-Spy for production profiling
- cProfile for detailed function profiling
- Memory profilers for leak detection

## Troubleshooting

### High Error Rate

1. Check monitoring dashboard: `/api/monitoring/dashboard/`
2. Review recent errors: `/api/monitoring/errors/`
3. Check component health: `/api/health/detailed/`
4. Review logs in production logging service
5. Check Celery worker status

### Slow Performance

1. Check performance stats: `/api/monitoring/performance/`
2. Identify slow operations (> 30s)
3. Review database query performance
4. Check Celery task queue length
5. Monitor system resources (CPU, memory, disk I/O)

### Component Failures

1. Database issues:
   - Check PostgreSQL connection pool
   - Verify database disk space
   - Review slow query logs

2. Redis issues:
   - Check Redis memory usage
   - Verify Redis connection limits
   - Monitor eviction rate

3. Celery issues:
   - Check worker logs
   - Verify broker connection (Redis)
   - Monitor task queue depth
   - Check for stuck tasks

## Testing

### Testing Error Handling

```python
from designs.exceptions import GeometryProcessingError
import pytest

def test_geometry_error_handling():
    with pytest.raises(GeometryProcessingError) as exc_info:
        process_invalid_file()
    
    assert exc_info.value.status_code == 422
    assert "Failed to parse" in str(exc_info.value)
```

### Testing Health Checks

```python
from django.test import TestCase

class HealthCheckTests(TestCase):
    def test_basic_health_check(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
    
    def test_detailed_health_check(self):
        response = self.client.get('/api/health/detailed/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('checks', data)
        self.assertIn('database', data['checks'])
        self.assertIn('redis', data['checks'])
```

## References

- `designs/exceptions.py`: Custom exception classes (150 lines)
- `designs/monitoring.py`: Monitoring utilities (350 lines)
- `designs/middleware.py`: Monitoring middleware (100 lines)
- `designs/views.py`: Health check and monitoring endpoints (120 lines)
- `enginel/settings.py`: Middleware configuration
- `enginel/urls.py`: Monitoring URL routes

## Revision History

- **v1.0** (2025-12-16): Initial error handling and monitoring implementation
  - 18 custom exception classes with HTTP status codes
  - Comprehensive error tracking with context
  - Performance monitoring for operations and tasks
  - Health check endpoints for load balancers
  - Metrics collection for dashboards
  - 4 monitoring middleware components
  - Admin-only monitoring dashboard
