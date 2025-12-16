"""
Background Job Monitoring for Celery Tasks.

Provides comprehensive monitoring, tracking, and analytics for async tasks:
- Task state tracking (pending, running, success, failure)
- Task result retrieval and caching
- Task metrics (duration, retry count, failure rate)
- Task history and audit trail
- Real-time task progress tracking
- Task queue statistics
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from celery import current_app
from celery.result import AsyncResult
from celery.exceptions import TimeoutError as CeleryTimeoutError
from designs.models import AnalysisJob, DesignAsset
from designs.cache import CacheManager, cache_result
import json

logger = logging.getLogger(__name__)


class TaskMonitor:
    """
    Monitor and track Celery task execution.
    
    Provides methods to query task status, retrieve results,
    and collect metrics about background job execution.
    """
    
    def __init__(self):
        """Initialize task monitor."""
        self.cache_manager = CacheManager('default')
        self.celery_app = current_app
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get current status of a Celery task.
        
        Args:
            task_id: Celery task ID
        
        Returns:
            Dictionary with task state, result, and metadata
        """
        # Try cache first
        cache_key = f"task_status:{task_id}"
        cached = self.cache_manager.get(cache_key)
        if cached and cached.get('state') in ['SUCCESS', 'FAILURE']:
            return cached
        
        # Query Celery
        result = AsyncResult(task_id, app=self.celery_app)
        
        status = {
            'task_id': task_id,
            'state': result.state,
            'current': 0,
            'total': 100,
            'status_message': '',
            'result': None,
            'error': None,
            'traceback': None,
            'started_at': None,
            'completed_at': None,
        }
        
        # Extract state-specific information
        if result.state == 'PENDING':
            status['status_message'] = 'Task is waiting to be processed'
        
        elif result.state == 'STARTED':
            status['status_message'] = 'Task has started execution'
            if result.info:
                status['started_at'] = result.info.get('started_at')
        
        elif result.state == 'PROGRESS':
            info = result.info or {}
            status['current'] = info.get('current', 0)
            status['total'] = info.get('total', 100)
            status['status_message'] = info.get('status', 'Processing...')
        
        elif result.state == 'SUCCESS':
            status['status_message'] = 'Task completed successfully'
            status['result'] = result.result
            status['completed_at'] = timezone.now().isoformat()
            # Cache successful results for 1 hour
            self.cache_manager.set(cache_key, status, timeout=3600)
        
        elif result.state == 'FAILURE':
            status['status_message'] = 'Task failed'
            status['error'] = str(result.info) if result.info else 'Unknown error'
            status['traceback'] = result.traceback
            # Cache failures for 10 minutes
            self.cache_manager.set(cache_key, status, timeout=600)
        
        elif result.state == 'RETRY':
            info = result.info or {}
            status['status_message'] = f"Task is being retried (attempt {info.get('retries', 0)})"
            status['error'] = str(info.get('exc'))
        
        elif result.state == 'REVOKED':
            status['status_message'] = 'Task was cancelled'
        
        return status
    
    def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """
        Get task result, waiting if necessary.
        
        Args:
            task_id: Celery task ID
            timeout: Maximum seconds to wait (None = wait forever)
        
        Returns:
            Task result or None if not ready
        
        Raises:
            CeleryTimeoutError: If timeout exceeded
        """
        result = AsyncResult(task_id, app=self.celery_app)
        
        try:
            if timeout:
                return result.get(timeout=timeout)
            else:
                # Don't wait, return immediately
                if result.ready():
                    return result.result
                return None
        except CeleryTimeoutError:
            logger.warning(f"Task {task_id} timed out after {timeout}s")
            raise
        except Exception as e:
            logger.error(f"Error getting task result: {e}")
            return None
    
    def cancel_task(self, task_id: str, terminate: bool = False) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Celery task ID
            terminate: If True, forcefully terminate (SIGKILL)
        
        Returns:
            True if cancelled successfully
        """
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            result.revoke(terminate=terminate)
            
            # Update AnalysisJob if exists
            try:
                job = AnalysisJob.objects.get(celery_task_id=task_id)
                job.status = 'CANCELLED'
                job.completed_at = timezone.now()
                job.save()
            except AnalysisJob.DoesNotExist:
                pass
            
            logger.info(f"Task {task_id} cancelled (terminate={terminate})")
            return True
        
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    def get_task_info(self, task_id: str) -> Dict[str, Any]:
        """
        Get comprehensive task information including metadata.
        
        Args:
            task_id: Celery task ID
        
        Returns:
            Dictionary with task details, status, and metadata
        """
        status = self.get_task_status(task_id)
        
        # Get additional info from AnalysisJob if available
        try:
            job = AnalysisJob.objects.select_related('design_asset').get(
                celery_task_id=task_id
            )
            
            status['job_id'] = str(job.id)
            status['job_type'] = job.job_type
            status['design_asset_id'] = str(job.design_asset_id)
            status['design_filename'] = job.design_asset.filename
            status['created_at'] = job.created_at.isoformat()
            
            if job.started_at:
                status['started_at'] = job.started_at.isoformat()
            if job.completed_at:
                status['completed_at'] = job.completed_at.isoformat()
                # Calculate duration
                duration = (job.completed_at - job.started_at).total_seconds()
                status['duration_seconds'] = duration
            
        except AnalysisJob.DoesNotExist:
            pass
        
        return status
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all currently running tasks.
        
        Returns:
            List of active task dictionaries
        """
        # Get from Celery inspect
        inspect = self.celery_app.control.inspect()
        active_tasks = []
        
        try:
            active = inspect.active()
            if active:
                for worker, tasks in active.items():
                    for task in tasks:
                        active_tasks.append({
                            'task_id': task['id'],
                            'name': task['name'],
                            'worker': worker,
                            'args': task.get('args', []),
                            'kwargs': task.get('kwargs', {}),
                            'started_at': task.get('time_start'),
                        })
        except Exception as e:
            logger.error(f"Failed to get active tasks: {e}")
        
        return active_tasks
    
    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all scheduled (pending) tasks.
        
        Returns:
            List of scheduled task dictionaries
        """
        inspect = self.celery_app.control.inspect()
        scheduled_tasks = []
        
        try:
            scheduled = inspect.scheduled()
            if scheduled:
                for worker, tasks in scheduled.items():
                    for task in tasks:
                        scheduled_tasks.append({
                            'task_id': task['request']['id'],
                            'name': task['request']['name'],
                            'worker': worker,
                            'eta': task.get('eta'),
                            'priority': task['request'].get('priority', 0),
                        })
        except Exception as e:
            logger.error(f"Failed to get scheduled tasks: {e}")
        
        return scheduled_tasks
    
    def get_reserved_tasks(self) -> List[Dict[str, Any]]:
        """
        Get tasks reserved by workers (not yet started).
        
        Returns:
            List of reserved task dictionaries
        """
        inspect = self.celery_app.control.inspect()
        reserved_tasks = []
        
        try:
            reserved = inspect.reserved()
            if reserved:
                for worker, tasks in reserved.items():
                    for task in tasks:
                        reserved_tasks.append({
                            'task_id': task['id'],
                            'name': task['name'],
                            'worker': worker,
                        })
        except Exception as e:
            logger.error(f"Failed to get reserved tasks: {e}")
        
        return reserved_tasks


class TaskMetrics:
    """
    Collect and analyze metrics about task execution.
    
    Tracks success rates, failure rates, average durations,
    and other performance metrics.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.cache_manager = CacheManager('default')
    
    def record_task_start(self, task_id: str, task_name: str, 
                          job_type: Optional[str] = None):
        """
        Record task start for metrics.
        
        Args:
            task_id: Celery task ID
            task_name: Task function name
            job_type: Type of job (GEOMETRY_EXTRACTION, etc.)
        """
        key = f"task_start:{task_id}"
        self.cache_manager.set(key, {
            'task_name': task_name,
            'job_type': job_type,
            'started_at': timezone.now().isoformat(),
        }, timeout=86400)  # 24 hours
    
    def record_task_completion(self, task_id: str, success: bool = True,
                               error: Optional[str] = None):
        """
        Record task completion for metrics.
        
        Args:
            task_id: Celery task ID
            success: Whether task succeeded
            error: Error message if failed
        """
        # Get start time
        start_key = f"task_start:{task_id}"
        start_data = self.cache_manager.get(start_key)
        
        if not start_data:
            return
        
        # Calculate duration
        started_at = datetime.fromisoformat(start_data['started_at'])
        duration = (timezone.now() - started_at).total_seconds()
        
        task_name = start_data['task_name']
        job_type = start_data.get('job_type', 'unknown')
        
        # Store completion data
        completion_key = f"task_completion:{task_id}"
        self.cache_manager.set(completion_key, {
            'task_name': task_name,
            'job_type': job_type,
            'success': success,
            'error': error,
            'duration': duration,
            'completed_at': timezone.now().isoformat(),
        }, timeout=86400)  # 24 hours
        
        # Update aggregate metrics
        self._update_aggregate_metrics(task_name, job_type, success, duration)
        
        # Clean up start record
        self.cache_manager.delete(start_key)
    
    def _update_aggregate_metrics(self, task_name: str, job_type: str,
                                   success: bool, duration: float):
        """Update rolling aggregate metrics."""
        # Metric key
        metric_key = f"task_metrics:{job_type}"
        
        # Get existing metrics
        metrics = self.cache_manager.get(metric_key, default={
            'total_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'total_duration': 0.0,
            'min_duration': float('inf'),
            'max_duration': 0.0,
        })
        
        # Update metrics
        metrics['total_count'] += 1
        if success:
            metrics['success_count'] += 1
        else:
            metrics['failure_count'] += 1
        
        metrics['total_duration'] += duration
        metrics['min_duration'] = min(metrics['min_duration'], duration)
        metrics['max_duration'] = max(metrics['max_duration'], duration)
        metrics['avg_duration'] = metrics['total_duration'] / metrics['total_count']
        metrics['success_rate'] = (metrics['success_count'] / metrics['total_count']) * 100
        
        # Store updated metrics (keep for 7 days)
        self.cache_manager.set(metric_key, metrics, timeout=604800)
    
    def get_task_metrics(self, job_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get aggregated task metrics.
        
        Args:
            job_type: Specific job type, or None for all
        
        Returns:
            Dictionary with metrics
        """
        if job_type:
            metric_key = f"task_metrics:{job_type}"
            return self.cache_manager.get(metric_key, default={
                'total_count': 0,
                'success_count': 0,
                'failure_count': 0,
                'success_rate': 0.0,
                'avg_duration': 0.0,
            })
        else:
            # Get all job types from AnalysisJob
            job_types = ['GEOMETRY_EXTRACTION', 'HASH_CALCULATION', 
                        'VALIDATION', 'BOM_EXTRACTION', 'UNIT_CONVERSION']
            
            all_metrics = {}
            for jt in job_types:
                all_metrics[jt] = self.get_task_metrics(jt)
            
            return all_metrics
    
    def get_recent_tasks(self, limit: int = 50, 
                        status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent task history from AnalysisJob.
        
        Args:
            limit: Maximum number of tasks to return
            status: Filter by status (SUCCESS, FAILURE, RUNNING, etc.)
        
        Returns:
            List of task dictionaries
        """
        queryset = AnalysisJob.objects.select_related('design_asset').all()
        
        if status:
            queryset = queryset.filter(status=status)
        
        queryset = queryset.order_by('-created_at')[:limit]
        
        tasks = []
        for job in queryset:
            task_data = {
                'job_id': str(job.id),
                'task_id': job.celery_task_id,
                'job_type': job.job_type,
                'status': job.status,
                'design_asset_id': str(job.design_asset_id),
                'design_filename': job.design_asset.filename,
                'created_at': job.created_at.isoformat(),
            }
            
            if job.started_at:
                task_data['started_at'] = job.started_at.isoformat()
            if job.completed_at:
                task_data['completed_at'] = job.completed_at.isoformat()
                duration = (job.completed_at - job.started_at).total_seconds()
                task_data['duration_seconds'] = duration
            
            if job.error_message:
                task_data['error'] = job.error_message
            
            tasks.append(task_data)
        
        return tasks
    
    def get_failure_analysis(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze task failures over time period.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Dictionary with failure statistics
        """
        since = timezone.now() - timedelta(days=days)
        
        failed_jobs = AnalysisJob.objects.filter(
            status='FAILURE',
            created_at__gte=since
        )
        
        total_failures = failed_jobs.count()
        
        # Group by job type
        failures_by_type = {}
        for job in failed_jobs:
            job_type = job.job_type
            if job_type not in failures_by_type:
                failures_by_type[job_type] = {
                    'count': 0,
                    'errors': []
                }
            failures_by_type[job_type]['count'] += 1
            if job.error_message:
                failures_by_type[job_type]['errors'].append(job.error_message)
        
        # Get most common errors
        all_errors = [job.error_message for job in failed_jobs if job.error_message]
        error_counts = {}
        for error in all_errors:
            # Truncate to first 100 chars for grouping
            error_key = error[:100]
            error_counts[error_key] = error_counts.get(error_key, 0) + 1
        
        top_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_failures': total_failures,
            'failures_by_type': failures_by_type,
            'top_errors': [{'error': err, 'count': cnt} for err, cnt in top_errors],
            'period_days': days,
            'analyzed_at': timezone.now().isoformat(),
        }


class TaskProgressTracker:
    """
    Track and report progress for long-running tasks.
    
    Allows tasks to report progress updates that can be
    queried by the frontend for progress bars, etc.
    """
    
    @staticmethod
    def update_progress(task_id: str, current: int, total: int, 
                       status: str = '', metadata: Optional[Dict] = None):
        """
        Update task progress.
        
        Args:
            task_id: Celery task ID
            current: Current progress value
            total: Total progress value (for percentage)
            status: Status message
            metadata: Additional progress metadata
        """
        from celery import current_task
        
        progress_data = {
            'current': current,
            'total': total,
            'percent': int((current / total) * 100) if total > 0 else 0,
            'status': status,
            'updated_at': timezone.now().isoformat(),
        }
        
        if metadata:
            progress_data['metadata'] = metadata
        
        # Update Celery task state
        if current_task:
            current_task.update_state(
                state='PROGRESS',
                meta=progress_data
            )
        
        # Also cache for quick retrieval
        cache_key = f"task_progress:{task_id}"
        cache.set(cache_key, progress_data, timeout=3600)
        
        logger.debug(f"Task {task_id} progress: {current}/{total} ({progress_data['percent']}%)")
    
    @staticmethod
    def get_progress(task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current task progress.
        
        Args:
            task_id: Celery task ID
        
        Returns:
            Progress dictionary or None
        """
        cache_key = f"task_progress:{task_id}"
        return cache.get(cache_key)


# Global instances
task_monitor = TaskMonitor()
task_metrics = TaskMetrics()
