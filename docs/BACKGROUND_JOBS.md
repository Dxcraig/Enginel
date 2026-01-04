# Background Job Monitoring Documentation

**Enginel - Engineering Intelligence Kernel**

Comprehensive monitoring and tracking system for Celery background tasks.

---

## Table of Contents

1. [Overview](#overview)
2. [Task Monitoring Architecture](#task-monitoring-architecture)
3. [API Endpoints](#api-endpoints)
4. [Task Lifecycle](#task-lifecycle)
5. [Progress Tracking](#progress-tracking)
6. [Metrics & Analytics](#metrics--analytics)
7. [Failure Analysis](#failure-analysis)
8. [Usage Examples](#usage-examples)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### Purpose

The background job monitoring system provides:
- **Real-time task status**: Track running, pending, and completed tasks
- **Progress tracking**: Monitor long-running operations with progress bars and percentage completion
- **Metrics collection**: Analyze success rates, durations, and failure patterns
- **Failure analysis**: Debug issues with detailed error tracking and stack traces
- **Task management**: Cancel, retry, or monitor active Celery tasks

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    Task Execution                       │
│  Celery Worker processes design files asynchronously   │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│              TaskMonitor Class                          │
│  • Query task status from Celery                       │
│  • Get results and error information                   │
│  • Cancel running tasks                                │
│  • List active/scheduled/reserved tasks                │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│            TaskMetrics Class                            │
│  • Record task start/completion                        │
│  • Calculate success rates and durations               │
│  • Aggregate metrics by job type                       │
│  • Analyze failure patterns                            │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│         TaskProgressTracker Class                       │
│  • Update progress during execution                    │
│  • Store progress in cache for quick retrieval         │
│  • Provide real-time updates to frontend               │
└─────────────────────────────────────────────────────────┘
```

---

## Task Monitoring Architecture

### TaskMonitor

**Location**: `designs/task_monitor.py`

Provides methods to query and manage Celery tasks:

```python
from designs.task_monitor import task_monitor

# Get task status
status = task_monitor.get_task_status(task_id)

# Get task result (blocking)
result = task_monitor.get_task_result(task_id, timeout=30)

# Cancel task
success = task_monitor.cancel_task(task_id, terminate=False)

# Get comprehensive task info
info = task_monitor.get_task_info(task_id)

# List active tasks
active = task_monitor.get_active_tasks()

# List scheduled tasks
scheduled = task_monitor.get_scheduled_tasks()

# List reserved tasks
reserved = task_monitor.get_reserved_tasks()
```

### TaskMetrics

Collects and analyzes task execution metrics:

```python
from designs.task_monitor import task_metrics

# Record task start
task_metrics.record_task_start(task_id, 'process_design_asset', 'PROCESSING')

# Record completion
task_metrics.record_task_completion(task_id, success=True)

# Record failure
task_metrics.record_task_completion(task_id, success=False, error='File not found')

# Get metrics by job type
metrics = task_metrics.get_task_metrics('GEOMETRY_EXTRACTION')

# Get recent task history
recent = task_metrics.get_recent_tasks(limit=50, status='FAILURE')

# Analyze failures
analysis = task_metrics.get_failure_analysis(days=7)
```

### TaskProgressTracker

Tracks progress for long-running tasks:

```python
from designs.task_monitor import TaskProgressTracker

# Update progress from task
TaskProgressTracker.update_progress(
    task_id=task_id,
    current=3,
    total=5,
    status='Extracting geometry...',
    metadata={'file': 'design.step'}
)

# Get current progress
progress = TaskProgressTracker.get_progress(task_id)
# Returns: {
#   'current': 3,
#   'total': 5,
#   'percent': 60,
#   'status': 'Extracting geometry...',
#   'updated_at': '2025-12-16T10:30:45Z'
# }
```

---

## API Endpoints

### List Analysis Jobs

Get paginated list of background jobs:

```bash
GET /api/analysis-jobs/

# Filtering
GET /api/analysis-jobs/?status=RUNNING
GET /api/analysis-jobs/?job_type=GEOMETRY_EXTRACTION
GET /api/analysis-jobs/?design_asset=550e8400-e29b-41d4-a716-446655440000

# Search
GET /api/analysis-jobs/?search=process

# Ordering
GET /api/analysis-jobs/?ordering=-created_at
```

**Response:**
```json
{
  "count": 42,
  "next": "http://localhost:8000/api/analysis-jobs/?page=2",
  "previous": null,
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "celery_task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "job_type": "GEOMETRY_EXTRACTION",
      "status": "SUCCESS",
      "design_asset": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2025-12-16T10:00:00Z",
      "started_at": "2025-12-16T10:00:05Z",
      "completed_at": "2025-12-16T10:02:30Z",
      "error_message": null
    }
  ]
}
```

### Get Job Detail

Get specific analysis job:

```bash
GET /api/analysis-jobs/{id}/
```

### Get Task Status

Get detailed Celery task status:

```bash
GET /api/analysis-jobs/{id}/status/
```

**Response:**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "state": "SUCCESS",
  "status_message": "Task completed successfully",
  "result": {
    "status": "success",
    "design_asset_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "error": null,
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "job_type": "GEOMETRY_EXTRACTION",
  "design_filename": "bracket.step",
  "started_at": "2025-12-16T10:00:05Z",
  "completed_at": "2025-12-16T10:02:30Z",
  "duration_seconds": 145.2
}
```

**Task States:**
- `PENDING`: Task waiting to be processed
- `STARTED`: Task execution has begun
- `PROGRESS`: Task is running (with progress updates)
- `SUCCESS`: Task completed successfully
- `FAILURE`: Task failed with error
- `RETRY`: Task is being retried
- `REVOKED`: Task was cancelled

### Get Task Progress

Get real-time progress for long-running tasks:

```bash
GET /api/analysis-jobs/{id}/progress/
```

**Response:**
```json
{
  "current": 3,
  "total": 5,
  "percent": 60,
  "status": "Extracting geometry metadata...",
  "updated_at": "2025-12-16T10:01:30Z",
  "metadata": {
    "step": "geometry_extraction",
    "file": "bracket.step"
  }
}
```

### Cancel Task

Cancel a running task:

```bash
POST /api/analysis-jobs/{id}/cancel/
Content-Type: application/json

{
  "terminate": false
}
```

**Parameters:**
- `terminate` (optional): If `true`, forcefully terminate task (SIGKILL)

**Response:**
```json
{
  "message": "Task cancelled successfully",
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "terminated": false
}
```

### Get Active Tasks

List all currently running tasks:

```bash
GET /api/analysis-jobs/active/
```

**Response:**
```json
{
  "count": 3,
  "tasks": [
    {
      "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "name": "designs.tasks.process_design_asset",
      "worker": "celery@worker1",
      "args": ["550e8400-e29b-41d4-a716-446655440000"],
      "started_at": "2025-12-16T10:00:05Z"
    }
  ]
}
```

### Get Task Metrics

Get aggregated task metrics:

```bash
# All job types
GET /api/analysis-jobs/metrics/

# Specific job type
GET /api/analysis-jobs/metrics/?job_type=GEOMETRY_EXTRACTION
```

**Response:**
```json
{
  "GEOMETRY_EXTRACTION": {
    "total_count": 150,
    "success_count": 142,
    "failure_count": 8,
    "success_rate": 94.67,
    "avg_duration": 87.3,
    "min_duration": 12.5,
    "max_duration": 450.2,
    "total_duration": 13095.0
  },
  "HASH_CALCULATION": {
    "total_count": 150,
    "success_count": 150,
    "failure_count": 0,
    "success_rate": 100.0,
    "avg_duration": 2.1
  }
}
```

### Get Failure Analysis

Analyze task failures over time:

```bash
# Last 7 days (default)
GET /api/analysis-jobs/failures/

# Last 30 days
GET /api/analysis-jobs/failures/?days=30
```

**Response:**
```json
{
  "total_failures": 23,
  "failures_by_type": {
    "GEOMETRY_EXTRACTION": {
      "count": 15,
      "errors": [
        "Failed to parse STEP file: Invalid syntax at line 345",
        "Geometry extraction timeout after 300 seconds"
      ]
    },
    "BOM_EXTRACTION": {
      "count": 8,
      "errors": [
        "No assembly structure found in file"
      ]
    }
  },
  "top_errors": [
    {
      "error": "Failed to parse STEP file: Invalid syntax at line 345",
      "count": 8
    },
    {
      "error": "Geometry extraction timeout after 300 seconds",
      "count": 5
    }
  ],
  "period_days": 7,
  "analyzed_at": "2025-12-16T10:30:00Z"
}
```

---

## Task Lifecycle

### 1. Task Creation

Task is created when design file is uploaded:

```python
# In views.py
design_asset = serializer.save(uploaded_by=request.user)
task = process_design_asset.delay(str(design_asset.id))

response_data = serializer.data
response_data['task_id'] = task.id
```

### 2. Task Execution

Task progresses through multiple stages:

```python
@shared_task(bind=True, max_retries=3)
def process_design_asset(self, design_asset_id):
    task_id = self.request.id
    
    # Record start for metrics
    task_metrics.record_task_start(task_id, 'process_design_asset', 'PROCESSING')
    
    # Step 1: Hash calculation
    TaskProgressTracker.update_progress(task_id, 1, 5, 'Calculating file hash...')
    file_hash = calculate_file_hash.delay(design_asset_id).get()
    
    # Step 2: Geometry extraction
    TaskProgressTracker.update_progress(task_id, 2, 5, 'Extracting geometry...')
    metadata = extract_geometry_metadata.delay(design_asset_id).get()
    
    # Step 3: Validation
    TaskProgressTracker.update_progress(task_id, 3, 5, 'Running validation...')
    validation = run_design_rule_checks.delay(design_asset_id).get()
    
    # Step 4: BOM extraction
    TaskProgressTracker.update_progress(task_id, 4, 5, 'Extracting BOM...')
    bom = extract_bom_from_assembly.delay(design_asset_id).get()
    
    # Step 5: Unit normalization
    TaskProgressTracker.update_progress(task_id, 5, 5, 'Complete!')
    
    # Record success
    task_metrics.record_task_completion(task_id, success=True)
```

### 3. Task Completion

Task finishes and records metrics:

```python
# Success
task_metrics.record_task_completion(task_id, success=True)

# Failure
task_metrics.record_task_completion(task_id, success=False, error=str(exc))
```

### 4. Status Querying

Frontend polls for status updates:

```javascript
async function pollTaskStatus(jobId) {
  const response = await fetch(`/api/analysis-jobs/${jobId}/status/`);
  const status = await response.json();
  
  if (status.state === 'PROGRESS') {
    // Update progress bar
    updateProgress(status.current, status.total, status.status_message);
    
    // Poll again in 2 seconds
    setTimeout(() => pollTaskStatus(jobId), 2000);
  }
  else if (status.state === 'SUCCESS') {
    showSuccess(status.result);
  }
  else if (status.state === 'FAILURE') {
    showError(status.error);
  }
}
```

---

## Progress Tracking

### Implementing Progress in Tasks

```python
from designs.task_monitor import TaskProgressTracker

@shared_task(bind=True)
def long_running_task(self, design_id):
    task_id = self.request.id
    
    # Start
    TaskProgressTracker.update_progress(
        task_id, 0, 100, 'Starting...'
    )
    
    # Process in chunks
    for i in range(100):
        # Do work
        process_chunk(i)
        
        # Update progress
        TaskProgressTracker.update_progress(
            task_id, i+1, 100, f'Processing chunk {i+1}/100'
        )
    
    return {'status': 'complete'}
```

### Frontend Progress Display

```javascript
async function showProgress(jobId) {
  const progressBar = document.getElementById('progress');
  const statusText = document.getElementById('status');
  
  const interval = setInterval(async () => {
    const response = await fetch(`/api/analysis-jobs/${jobId}/progress/`);
    const progress = await response.json();
    
    progressBar.value = progress.percent;
    statusText.textContent = progress.status;
    
    if (progress.percent >= 100) {
      clearInterval(interval);
    }
  }, 1000);
}
```

---

## Metrics & Analytics

### Success Rate Tracking

Monitor task success rates by job type:

```python
metrics = task_metrics.get_task_metrics('GEOMETRY_EXTRACTION')

print(f"Success rate: {metrics['success_rate']:.1f}%")
print(f"Total tasks: {metrics['total_count']}")
print(f"Failures: {metrics['failure_count']}")
```

### Duration Analysis

Analyze task performance:

```python
metrics = task_metrics.get_task_metrics('GEOMETRY_EXTRACTION')

print(f"Average duration: {metrics['avg_duration']:.1f}s")
print(f"Min duration: {metrics['min_duration']:.1f}s")
print(f"Max duration: {metrics['max_duration']:.1f}s")
```

### Historical Trends

Query recent task history:

```python
# Last 50 failed tasks
failures = task_metrics.get_recent_tasks(limit=50, status='FAILURE')

for task in failures:
    print(f"{task['job_type']}: {task['error']}")
```

---

## Failure Analysis

### Identifying Common Errors

```python
analysis = task_metrics.get_failure_analysis(days=7)

print(f"Total failures: {analysis['total_failures']}")

for error_info in analysis['top_errors']:
    print(f"{error_info['count']}x: {error_info['error']}")
```

### Debugging Failed Tasks

1. **Get task details**:
```bash
curl http://localhost:8000/api/analysis-jobs/{id}/status/
```

2. **Check error message**:
```json
{
  "state": "FAILURE",
  "error": "Failed to parse STEP file: Invalid syntax",
  "traceback": "Traceback (most recent call last)..."
}
```

3. **Review logs**:
```bash
docker logs enginel_celery_worker | grep {task_id}
```

---

## Usage Examples

### Example 1: Monitor Design Processing

```bash
# Upload design
curl -X POST http://localhost:8000/api/designs/ \
  -H "Authorization: Token $TOKEN" \
  -F "file=@bracket.step" \
  -F "series_id=series-uuid"

# Response includes job_id
{
  "id": "design-uuid",
  "job_id": "job-uuid",
  "status": "PROCESSING"
}

# Poll for progress
while true; do
  curl http://localhost:8000/api/analysis-jobs/job-uuid/progress/
  sleep 2
done

# Check final status
curl http://localhost:8000/api/analysis-jobs/job-uuid/status/
```

### Example 2: Cancel Long-Running Task

```bash
# Cancel gracefully
curl -X POST http://localhost:8000/api/analysis-jobs/job-uuid/cancel/ \
  -H "Authorization: Token $TOKEN" \
  -d '{"terminate": false}'

# Force terminate (SIGKILL)
curl -X POST http://localhost:8000/api/analysis-jobs/job-uuid/cancel/ \
  -H "Authorization: Token $TOKEN" \
  -d '{"terminate": true}'
```

### Example 3: Monitor System Health

```bash
# Check active tasks
curl http://localhost:8000/api/analysis-jobs/active/

# Get metrics
curl http://localhost:8000/api/analysis-jobs/metrics/

# Analyze failures
curl http://localhost:8000/api/analysis-jobs/failures/?days=30
```

---

## Best Practices

### 1. Progress Updates

✅ **DO:**
- Update progress at meaningful milestones
- Include descriptive status messages
- Keep updates frequent (every 1-5 seconds)

❌ **DON'T:**
- Update too frequently (< 100ms)
- Skip progress updates for long operations
- Use generic status messages

### 2. Error Handling

✅ **DO:**
- Record task failures in metrics
- Include detailed error messages
- Log stack traces for debugging

❌ **DON'T:**
- Swallow exceptions silently
- Use generic error messages
- Skip error recording

### 3. Metrics Collection

✅ **DO:**
- Record start and completion for all tasks
- Track success/failure rates
- Monitor duration trends

❌ **DON'T:**
- Skip metrics for "quick" tasks
- Ignore failed task metrics
- Clear metrics frequently

### 4. Task Cancellation

✅ **DO:**
- Allow graceful cancellation first
- Check task state before cancelling
- Update job status after cancellation

❌ **DON'T:**
- Force terminate without reason
- Cancel already-completed tasks
- Skip status updates

---

## Troubleshooting

### Task Stuck in PENDING

**Symptoms:** Task never starts, stays in PENDING state

**Causes:**
- Celery worker not running
- Worker crashed
- Queue backlog

**Solutions:**
```bash
# Check workers
docker logs enginel_celery_worker

# Restart workers
docker-compose restart celery_worker

# Check queue
docker exec enginel_redis redis-cli LLEN celery

# Inspect Celery
docker exec enginel_celery_worker celery -A enginel inspect active
```

### Progress Not Updating

**Symptoms:** Progress endpoint returns stale data

**Causes:**
- Task not calling `update_progress`
- Cache expired
- Worker disconnected

**Solutions:**
```python
# Verify task calls update_progress
TaskProgressTracker.update_progress(task_id, current, total, status)

# Check cache
from django.core.cache import cache
progress = cache.get(f'task_progress:{task_id}')
```

### High Failure Rate

**Symptoms:** Many tasks failing with errors

**Causes:**
- Invalid input files
- Resource constraints
- Code bugs

**Solutions:**
```bash
# Analyze failures
curl http://localhost:8000/api/analysis-jobs/failures/?days=7

# Check common errors
curl http://localhost:8000/api/analysis-jobs/?status=FAILURE&limit=10

# Review worker logs
docker logs enginel_celery_worker --tail 100
```

### Memory Issues

**Symptoms:** Workers crash, out of memory errors

**Causes:**
- Large file processing
- Memory leaks
- Too many concurrent tasks

**Solutions:**
```bash
# Monitor worker memory
docker stats enginel_celery_worker

# Reduce concurrency
# In docker-compose.yml:
celery_worker:
  command: celery -A enginel worker --concurrency=2

# Restart workers periodically
docker-compose restart celery_worker
```

---

## Appendix

### File Locations

- **Task monitor**: `designs/task_monitor.py`
- **Tasks**: `designs/tasks.py`
- **ViewSet**: `designs/views.py` (AnalysisJobViewSet)
- **Models**: `designs/models.py` (AnalysisJob)

### Related Documentation

- **Celery Configuration**: `enginel/celery.py`
- **Caching**: `CACHING.md`
- **Error Handling**: `ERROR_HANDLING.md`
- **Audit Logging**: `AUDIT_LOGGING.md`

---

**Last Updated**: December 2025  
**Enginel Version**: 1.0.0  
**Author**: AI Engineering Team
