'use client';

import { useState, useEffect } from 'react';
import ApiClient from '@/lib/api/client';
import type { AuditLogEntry } from '@/types';
import Link from 'next/link';

export default function AuditLogsPage() {
    const [logs, setLogs] = useState<AuditLogEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [totalCount, setTotalCount] = useState(0);

    // Filters
    const [actionFilter, setActionFilter] = useState<string>('');
    const [resourceFilter, setResourceFilter] = useState<string>('');
    const [usernameFilter, setUsernameFilter] = useState<string>('');
    const [dateRange, setDateRange] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState('');

    // Pagination
    const [currentPage, setCurrentPage] = useState(1);
    const pageSize = 50;

    useEffect(() => {
        fetchLogs();
    }, [currentPage, actionFilter, resourceFilter, usernameFilter, dateRange, searchQuery]);

    const fetchLogs = async () => {
        try {
            setLoading(true);

            const params = new URLSearchParams({
                page: currentPage.toString(),
                page_size: pageSize.toString(),
            });

            if (actionFilter) params.append('action', actionFilter);
            if (resourceFilter) params.append('resource_type', resourceFilter);
            if (usernameFilter) params.append('actor_username', usernameFilter);
            if (searchQuery) params.append('search', searchQuery);

            // Date range filters
            if (dateRange === 'last_hour') params.append('last_hour', 'true');
            else if (dateRange === 'last_day') params.append('last_day', 'true');
            else if (dateRange === 'last_week') params.append('last_week', 'true');

            const response = await ApiClient.get<{ results: AuditLogEntry[]; count: number }>(`/audit-logs/?${params.toString()}`);
            setLogs(response.results);
            setTotalCount(response.count);
        } catch (error) {
            console.error('Failed to fetch audit logs:', error);
        } finally {
            setLoading(false);
        }
    };

    const exportLogs = async (format: 'csv' | 'json') => {
        try {
            const params = new URLSearchParams({
                page_size: '10000', // Export all
            });

            if (actionFilter) params.append('action', actionFilter);
            if (resourceFilter) params.append('resource_type', resourceFilter);
            if (usernameFilter) params.append('actor_username', usernameFilter);
            if (searchQuery) params.append('search', searchQuery);

            if (dateRange === 'last_hour') params.append('last_hour', 'true');
            else if (dateRange === 'last_day') params.append('last_day', 'true');
            else if (dateRange === 'last_week') params.append('last_week', 'true');

            const response = await ApiClient.get<{ results: AuditLogEntry[] }>(`/audit-logs/?${params.toString()}`);
            const data = response.results;

            if (format === 'csv') {
                const csv = convertToCSV(data);
                downloadFile(csv, 'audit-logs.csv', 'text/csv');
            } else {
                const json = JSON.stringify(data, null, 2);
                downloadFile(json, 'audit-logs.json', 'application/json');
            }
        } catch (error) {
            console.error('Failed to export logs:', error);
        }
    };

    const convertToCSV = (data: AuditLogEntry[]): string => {
        const headers = ['Timestamp', 'User', 'Action', 'Resource Type', 'Resource ID', 'IP Address'];
        const rows = data.map(log => [
            new Date(log.timestamp).toISOString(),
            log.actor_username,
            log.action_display,
            log.resource_type,
            log.resource_id,
            log.ip_address || 'N/A',
        ]);

        return [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(',')),
        ].join('\n');
    };

    const downloadFile = (content: string, filename: string, mimeType: string) => {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    const resetFilters = () => {
        setActionFilter('');
        setResourceFilter('');
        setUsernameFilter('');
        setDateRange('all');
        setSearchQuery('');
        setCurrentPage(1);
    };

    const getActionIcon = (action: string) => {
        switch (action) {
            case 'CREATE':
                return (
                    <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                );
            case 'UPDATE':
                return (
                    <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                );
            case 'DELETE':
                return (
                    <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                );
            case 'READ':
                return (
                    <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                );
            case 'DOWNLOAD':
                return (
                    <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                );
            case 'UPLOAD':
                return (
                    <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                );
            default:
                return (
                    <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                );
        }
    };

    const getActionBadge = (action: string) => {
        const colors = {
            CREATE: 'bg-green-100 text-green-800',
            UPDATE: 'bg-blue-100 text-blue-800',
            DELETE: 'bg-red-100 text-red-800',
            READ: 'bg-gray-100 text-gray-800',
            DOWNLOAD: 'bg-purple-100 text-purple-800',
            UPLOAD: 'bg-orange-100 text-orange-800',
        };
        return colors[action as keyof typeof colors] || 'bg-gray-100 text-gray-800';
    };

    const formatTimestamp = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;

        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const totalPages = Math.ceil(totalCount / pageSize);

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Header */}
            <div className="mb-8">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Audit Logs</h1>
                        <p className="mt-2 text-gray-600">Complete system activity trail for compliance</p>
                    </div>
                    <div className="flex space-x-2">
                        <button
                            onClick={() => exportLogs('csv')}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center space-x-2"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            <span>CSV</span>
                        </button>
                        <button
                            onClick={() => exportLogs('json')}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            <span>JSON</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                    {/* Search */}
                    <div className="lg:col-span-2">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search username, action, resource..."
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                    </div>

                    {/* Action Filter */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Action</label>
                        <select
                            value={actionFilter}
                            onChange={(e) => setActionFilter(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                            <option value="">All Actions</option>
                            <option value="CREATE">Create</option>
                            <option value="UPDATE">Update</option>
                            <option value="DELETE">Delete</option>
                            <option value="READ">Read</option>
                            <option value="DOWNLOAD">Download</option>
                            <option value="UPLOAD">Upload</option>
                        </select>
                    </div>

                    {/* Resource Type Filter */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Resource</label>
                        <select
                            value={resourceFilter}
                            onChange={(e) => setResourceFilter(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                            <option value="">All Resources</option>
                            <option value="DesignAsset">Design Asset</option>
                            <option value="DesignSeries">Design Series</option>
                            <option value="ReviewSession">Review Session</option>
                            <option value="AssemblyNode">Assembly Node</option>
                            <option value="ValidationRule">Validation Rule</option>
                            <option value="User">User</option>
                        </select>
                    </div>

                    {/* Date Range */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Time Range</label>
                        <select
                            value={dateRange}
                            onChange={(e) => setDateRange(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                            <option value="all">All Time</option>
                            <option value="last_hour">Last Hour</option>
                            <option value="last_day">Last 24 Hours</option>
                            <option value="last_week">Last 7 Days</option>
                        </select>
                    </div>
                </div>

                {/* Active Filters + Reset */}
                {(actionFilter || resourceFilter || usernameFilter || dateRange !== 'all' || searchQuery) && (
                    <div className="mt-4 flex items-center justify-between border-t border-gray-200 pt-4">
                        <div className="flex flex-wrap gap-2">
                            {actionFilter && (
                                <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
                                    Action: {actionFilter}
                                </span>
                            )}
                            {resourceFilter && (
                                <span className="px-3 py-1 bg-green-100 text-green-800 text-sm rounded-full">
                                    Resource: {resourceFilter}
                                </span>
                            )}
                            {dateRange !== 'all' && (
                                <span className="px-3 py-1 bg-purple-100 text-purple-800 text-sm rounded-full">
                                    {dateRange === 'last_hour' ? 'Last Hour' : dateRange === 'last_day' ? 'Last 24 Hours' : 'Last 7 Days'}
                                </span>
                            )}
                            {searchQuery && (
                                <span className="px-3 py-1 bg-orange-100 text-orange-800 text-sm rounded-full">
                                    Search: "{searchQuery}"
                                </span>
                            )}
                        </div>
                        <button
                            onClick={resetFilters}
                            className="text-sm text-gray-600 hover:text-gray-900 font-medium"
                        >
                            Clear All Filters
                        </button>
                    </div>
                )}
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-white rounded-lg shadow p-4">
                    <div className="text-sm text-gray-600 mb-1">Total Events</div>
                    <div className="text-2xl font-bold text-gray-900">{totalCount.toLocaleString()}</div>
                </div>
                <div className="bg-green-50 rounded-lg shadow p-4">
                    <div className="text-sm text-green-700 mb-1">Creates</div>
                    <div className="text-2xl font-bold text-green-900">
                        {logs.filter(l => l.action === 'CREATE').length}
                    </div>
                </div>
                <div className="bg-blue-50 rounded-lg shadow p-4">
                    <div className="text-sm text-blue-700 mb-1">Updates</div>
                    <div className="text-2xl font-bold text-blue-900">
                        {logs.filter(l => l.action === 'UPDATE').length}
                    </div>
                </div>
                <div className="bg-red-50 rounded-lg shadow p-4">
                    <div className="text-sm text-red-700 mb-1">Deletes</div>
                    <div className="text-2xl font-bold text-red-900">
                        {logs.filter(l => l.action === 'DELETE').length}
                    </div>
                </div>
            </div>

            {/* Timeline */}
            {loading ? (
                <div className="flex justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            ) : logs.length === 0 ? (
                <div className="bg-white rounded-lg shadow p-12 text-center">
                    <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No audit logs found</h3>
                    <p className="text-gray-600">Try adjusting your filters</p>
                </div>
            ) : (
                <div className="bg-white rounded-lg shadow">
                    <div className="divide-y divide-gray-200">
                        {logs.map((log, index) => (
                            <div key={log.id} className="p-4 hover:bg-gray-50 transition-colors">
                                <div className="flex items-start space-x-4">
                                    {/* Icon */}
                                    <div className="flex-shrink-0 mt-1">
                                        {getActionIcon(log.action)}
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center space-x-2 mb-1">
                                            <span className={`px-2.5 py-0.5 text-xs font-medium rounded-full ${getActionBadge(log.action)}`}>
                                                {log.action_display}
                                            </span>
                                            <span className="text-sm font-medium text-gray-900">
                                                {log.actor_username}
                                            </span>
                                            <span className="text-sm text-gray-500">•</span>
                                            <span className="text-sm text-gray-500">
                                                {formatTimestamp(log.timestamp)}
                                            </span>
                                        </div>

                                        <p className="text-sm text-gray-700">
                                            {log.action_display} <span className="font-medium">{log.resource_type}</span>
                                            {log.resource_id && (
                                                <span className="text-gray-500"> (ID: {log.resource_id.slice(0, 8)}...)</span>
                                            )}
                                        </p>

                                        {/* Additional Info */}
                                        <div className="flex flex-wrap gap-4 mt-2 text-xs text-gray-500">
                                            {log.ip_address && (
                                                <span className="flex items-center">
                                                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                                                    </svg>
                                                    {log.ip_address}
                                                </span>
                                            )}
                                            <span>Actor ID: {log.actor_id}</span>
                                            {log.changes && Object.keys(log.changes).length > 0 && (
                                                <button
                                                    className="text-blue-600 hover:text-blue-800 font-medium"
                                                    onClick={() => {
                                                        alert(JSON.stringify(log.changes, null, 2));
                                                    }}
                                                >
                                                    View Changes
                                                </button>
                                            )}
                                        </div>
                                    </div>

                                    {/* Timestamp (detailed) */}
                                    <div className="flex-shrink-0 text-right">
                                        <div className="text-xs text-gray-500">
                                            {new Date(log.timestamp).toLocaleTimeString('en-US', {
                                                hour: '2-digit',
                                                minute: '2-digit',
                                            })}
                                        </div>
                                        <div className="text-xs text-gray-400">
                                            {new Date(log.timestamp).toLocaleDateString('en-US', {
                                                month: 'short',
                                                day: 'numeric',
                                            })}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="mt-6 flex items-center justify-between">
                    <div className="text-sm text-gray-600">
                        Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalCount)} of {totalCount} logs
                    </div>
                    <div className="flex space-x-2">
                        <button
                            onClick={() => setCurrentPage(currentPage - 1)}
                            disabled={currentPage === 1}
                            className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Previous
                        </button>
                        <div className="flex space-x-1">
                            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                let pageNum;
                                if (totalPages <= 5) {
                                    pageNum = i + 1;
                                } else if (currentPage <= 3) {
                                    pageNum = i + 1;
                                } else if (currentPage >= totalPages - 2) {
                                    pageNum = totalPages - 4 + i;
                                } else {
                                    pageNum = currentPage - 2 + i;
                                }

                                return (
                                    <button
                                        key={pageNum}
                                        onClick={() => setCurrentPage(pageNum)}
                                        className={`px-3 py-2 rounded-lg text-sm font-medium ${currentPage === pageNum
                                                ? 'bg-blue-600 text-white'
                                                : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                                            }`}
                                    >
                                        {pageNum}
                                    </button>
                                );
                            })}
                        </div>
                        <button
                            onClick={() => setCurrentPage(currentPage + 1)}
                            disabled={currentPage === totalPages}
                            className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Next
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
