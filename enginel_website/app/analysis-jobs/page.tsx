'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import ApiClient from '@/lib/api/client';

interface AnalysisJob {
    id: string;
    design_asset: string;
    job_type: string;
    status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'RETRY';
    celery_task_id: string;
    result: any;
    error_message: string;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
    duration: number | null;
}

interface JobMetrics {
    total_jobs: number;
    pending: number;
    running: number;
    success: number;
    failed: number;
    avg_duration: number;
}

export default function AnalysisJobsPage() {
    const { user } = useAuth();
    const router = useRouter();
    const [jobs, setJobs] = useState<AnalysisJob[]>([]);
    const [metrics, setMetrics] = useState<JobMetrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filter, setFilter] = useState<string>('all');
    const [jobTypeFilter, setJobTypeFilter] = useState<string>('all');
    const [autoRefresh, setAutoRefresh] = useState(true);

    useEffect(() => {
        if (!user) {
            router.push('/login');
            return;
        }
        fetchJobs();
    }, [user, router, filter, jobTypeFilter]);

    // Auto-refresh every 5 seconds if enabled
    useEffect(() => {
        if (!autoRefresh) return;

        const interval = setInterval(() => {
            fetchJobs(true);
        }, 5000);

        return () => clearInterval(interval);
    }, [autoRefresh, filter, jobTypeFilter]);

    const fetchJobs = async (silent = false) => {
        try {
            if (!silent) setLoading(true);
            setError(null);

            let url = '/analysis-jobs/?ordering=-created_at';

            if (filter !== 'all') {
                url += `&status=${filter}`;
            }

            if (jobTypeFilter !== 'all') {
                url += `&job_type=${jobTypeFilter}`;
            }

            const data = await ApiClient.get<AnalysisJob[]>(url);
            setJobs(Array.isArray(data) ? data : []);

            // Calculate metrics from fetched jobs
            calculateMetrics(Array.isArray(data) ? data : []);
        } catch (err: any) {
            console.error('Failed to load analysis jobs:', err);
            setError(err.message || 'Failed to load analysis jobs');
            setJobs([]);
        } finally {
            if (!silent) setLoading(false);
        }
    };

    const calculateMetrics = (jobsList: AnalysisJob[]) => {
        const total = jobsList.length;
        const pending = jobsList.filter(j => j.status === 'PENDING').length;
        const running = jobsList.filter(j => j.status === 'RUNNING').length;
        const success = jobsList.filter(j => j.status === 'SUCCESS').length;
        const failed = jobsList.filter(j => j.status === 'FAILED').length;

        const completedWithDuration = jobsList.filter(j => j.duration !== null);
        const avgDuration = completedWithDuration.length > 0
            ? completedWithDuration.reduce((sum, j) => sum + (j.duration || 0), 0) / completedWithDuration.length
            : 0;

        setMetrics({
            total_jobs: total,
            pending,
            running,
            success,
            failed,
            avg_duration: avgDuration,
        });
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'PENDING':
                return 'bg-gray-100 text-gray-800 border-gray-300';
            case 'RUNNING':
                return 'bg-blue-100 text-blue-800 border-blue-300';
            case 'SUCCESS':
                return 'bg-green-100 text-green-800 border-green-300';
            case 'FAILED':
                return 'bg-red-100 text-red-800 border-red-300';
            case 'RETRY':
                return 'bg-yellow-100 text-yellow-800 border-yellow-300';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-300';
        }
    };

    const getJobTypeIcon = (jobType: string) => {
        switch (jobType) {
            case 'GEOMETRY_EXTRACTION':
                return (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                    </svg>
                );
            case 'BOM_PARSING':
                return (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                    </svg>
                );
            case 'VALIDATION':
                return (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                );
            case 'MASS_PROPERTIES':
                return (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
                    </svg>
                );
            case 'INTERFERENCE_CHECK':
                return (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                );
            default:
                return (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                );
        }
    };

    const formatJobType = (type: string) => {
        return type.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase());
    };

    const formatDuration = (seconds: number | null) => {
        if (seconds === null) return 'N/A';
        if (seconds < 1) return '<1s';
        if (seconds < 60) return `${seconds.toFixed(1)}s`;
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}m ${remainingSeconds}s`;
    };

    const formatTimestamp = (timestamp: string | null) => {
        if (!timestamp) return 'N/A';
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d ago`;
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading analysis jobs...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900">Analysis Jobs</h1>
                            <p className="text-gray-600 mt-2">Monitor background processing tasks and job status</p>
                        </div>
                        <div className="flex items-center gap-3">
                            <label className="flex items-center gap-2 text-sm text-gray-700">
                                <input
                                    type="checkbox"
                                    checked={autoRefresh}
                                    onChange={(e) => setAutoRefresh(e.target.checked)}
                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                Auto-refresh (5s)
                            </label>
                            <button
                                onClick={() => fetchJobs()}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                                Refresh
                            </button>
                        </div>
                    </div>
                </div>

                {/* Error Message */}
                {error && (
                    <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
                        <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                        <span className="text-red-800">{error}</span>
                    </div>
                )}

                {/* Metrics Cards */}
                {metrics && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4 mb-8">
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                            <div className="text-sm text-gray-600 mb-1">Total Jobs</div>
                            <div className="text-2xl font-bold text-gray-900">{metrics.total_jobs}</div>
                        </div>
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                            <div className="text-sm text-gray-600 mb-1">Pending</div>
                            <div className="text-2xl font-bold text-gray-500">{metrics.pending}</div>
                        </div>
                        <div className="bg-white rounded-lg shadow-sm border border-blue-200 p-4 bg-blue-50">
                            <div className="text-sm text-blue-600 mb-1">Running</div>
                            <div className="text-2xl font-bold text-blue-700">{metrics.running}</div>
                        </div>
                        <div className="bg-white rounded-lg shadow-sm border border-green-200 p-4 bg-green-50">
                            <div className="text-sm text-green-600 mb-1">Success</div>
                            <div className="text-2xl font-bold text-green-700">{metrics.success}</div>
                        </div>
                        <div className="bg-white rounded-lg shadow-sm border border-red-200 p-4 bg-red-50">
                            <div className="text-sm text-red-600 mb-1">Failed</div>
                            <div className="text-2xl font-bold text-red-700">{metrics.failed}</div>
                        </div>
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                            <div className="text-sm text-gray-600 mb-1">Avg Duration</div>
                            <div className="text-2xl font-bold text-gray-900">{formatDuration(metrics.avg_duration)}</div>
                        </div>
                    </div>
                )}

                {/* Filters */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
                    <div className="flex flex-wrap gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Status Filter</label>
                            <select
                                value={filter}
                                onChange={(e) => setFilter(e.target.value)}
                                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            >
                                <option value="all">All Statuses</option>
                                <option value="PENDING">Pending</option>
                                <option value="RUNNING">Running</option>
                                <option value="SUCCESS">Success</option>
                                <option value="FAILED">Failed</option>
                                <option value="RETRY">Retrying</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Job Type Filter</label>
                            <select
                                value={jobTypeFilter}
                                onChange={(e) => setJobTypeFilter(e.target.value)}
                                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            >
                                <option value="all">All Types</option>
                                <option value="GEOMETRY_EXTRACTION">Geometry Extraction</option>
                                <option value="BOM_PARSING">BOM Parsing</option>
                                <option value="VALIDATION">Validation</option>
                                <option value="MASS_PROPERTIES">Mass Properties</option>
                                <option value="INTERFERENCE_CHECK">Interference Check</option>
                                <option value="HASH_CALCULATION">Hash Calculation</option>
                            </select>
                        </div>
                    </div>
                </div>

                {/* Jobs List */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                    {jobs.length === 0 ? (
                        <div className="text-center py-12">
                            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                            </svg>
                            <h3 className="mt-2 text-sm font-medium text-gray-900">No analysis jobs found</h3>
                            <p className="mt-1 text-sm text-gray-500">Jobs will appear here when designs are uploaded and processed.</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Job Type
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Status
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Created
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Duration
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Task ID
                                        </th>
                                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Actions
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {jobs.map((job) => (
                                        <tr key={job.id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="flex items-center gap-3">
                                                    <div className="text-gray-600">
                                                        {getJobTypeIcon(job.job_type)}
                                                    </div>
                                                    <div className="text-sm font-medium text-gray-900">
                                                        {formatJobType(job.job_type)}
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(job.status)}`}>
                                                    {job.status === 'RUNNING' && (
                                                        <svg className="animate-spin -ml-1 mr-2 h-3 w-3" fill="none" viewBox="0 0 24 24">
                                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                        </svg>
                                                    )}
                                                    {job.status}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                                {formatTimestamp(job.created_at)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                                {formatDuration(job.duration)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="text-xs font-mono text-gray-500">
                                                    {job.celery_task_id ? job.celery_task_id.substring(0, 8) + '...' : 'N/A'}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                <button
                                                    onClick={() => router.push(`/designs/${job.design_asset}`)}
                                                    className="text-blue-600 hover:text-blue-900"
                                                >
                                                    View Design
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>

                {/* Failed Jobs Details */}
                {jobs.filter(j => j.status === 'FAILED').length > 0 && (
                    <div className="mt-8 bg-red-50 rounded-lg border border-red-200 p-6">
                        <h2 className="text-lg font-semibold text-red-900 mb-4 flex items-center gap-2">
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                            </svg>
                            Failed Jobs ({jobs.filter(j => j.status === 'FAILED').length})
                        </h2>
                        <div className="space-y-3">
                            {jobs.filter(j => j.status === 'FAILED').slice(0, 5).map((job) => (
                                <div key={job.id} className="bg-white rounded-lg p-4 border border-red-200">
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <div className="font-medium text-gray-900">{formatJobType(job.job_type)}</div>
                                            <div className="text-sm text-gray-600 mt-1">{formatTimestamp(job.created_at)}</div>
                                            {job.error_message && (
                                                <div className="text-sm text-red-700 mt-2 font-mono bg-red-50 p-2 rounded">
                                                    {job.error_message}
                                                </div>
                                            )}
                                        </div>
                                        <button
                                            onClick={() => router.push(`/designs/${job.design_asset}`)}
                                            className="text-sm text-blue-600 hover:text-blue-900"
                                        >
                                            View Design
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
