'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

interface DesignAsset {
    id: string;
    series: string;
    part_number: string;
    version_number: number;
    filename: string;
    status: string;
    classification: string;
    file_size_bytes: number;
    file_hash_sha256: string;
    uploaded_by: string;
    uploaded_by_username: string;
    created_at: string;
    updated_at: string;
}

interface Series {
    id: string;
    part_number: string;
    name: string;
    version_count: number;
    latest_version_number: number;
    created_by_username: string;
    created_at: string;
}

export default function DesignsPage() {
    const router = useRouter();
    const [designs, setDesigns] = useState<DesignAsset[]>([]);
    const [series, setSeries] = useState<Series[]>([]);
    const [loading, setLoading] = useState(true);
    const [view, setView] = useState<'designs' | 'series'>('designs');
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [classificationFilter, setClassificationFilter] = useState('all');

    useEffect(() => {
        if (view === 'designs') {
            fetchDesigns();
        } else {
            fetchSeries();
        }
    }, [view, statusFilter, classificationFilter]);

    const fetchDesigns = async () => {
        try {
            setLoading(true);
            const token = localStorage.getItem('token');
            let url = '/api/designs/';
            const params = new URLSearchParams();

            if (statusFilter !== 'all') {
                params.append('status', statusFilter);
            }
            if (classificationFilter !== 'all') {
                params.append('classification', classificationFilter);
            }
            if (params.toString()) {
                url += '?' + params.toString();
            }

            const response = await fetch(url, {
                headers: {
                    'Authorization': `Token ${token}`,
                },
            });

            if (response.ok) {
                const data = await response.json();
                setDesigns(data.results || data);
            }
        } catch (error) {
            console.error('Failed to fetch designs:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchSeries = async () => {
        try {
            setLoading(true);
            const token = localStorage.getItem('token');
            const response = await fetch('/api/series/', {
                headers: {
                    'Authorization': `Token ${token}`,
                },
            });

            if (response.ok) {
                const data = await response.json();
                setSeries(data.results || data);
            }
        } catch (error) {
            console.error('Failed to fetch series:', error);
        } finally {
            setLoading(false);
        }
    };

    const filteredDesigns = designs.filter(design => {
        if (!searchQuery) return true;
        const query = searchQuery.toLowerCase();
        return (
            design.filename.toLowerCase().includes(query) ||
            design.part_number.toLowerCase().includes(query) ||
            design.uploaded_by_username.toLowerCase().includes(query)
        );
    });

    const filteredSeries = series.filter(s => {
        if (!searchQuery) return true;
        const query = searchQuery.toLowerCase();
        return (
            s.part_number.toLowerCase().includes(query) ||
            s.name.toLowerCase().includes(query) ||
            s.created_by_username.toLowerCase().includes(query)
        );
    });

    const getStatusBadge = (status: string) => {
        const badges = {
            UPLOADED: 'bg-blue-100 text-blue-800 border-blue-200',
            PROCESSING: 'bg-yellow-100 text-yellow-800 border-yellow-200',
            PROCESSED: 'bg-green-100 text-green-800 border-green-200',
            FAILED: 'bg-red-100 text-red-800 border-red-200',
            APPROVED: 'bg-green-100 text-green-800 border-green-200',
            REJECTED: 'bg-red-100 text-red-800 border-red-200',
        };
        return badges[status as keyof typeof badges] || 'bg-gray-100 text-gray-800 border-gray-200';
    };

    const getClassificationBadge = (classification: string) => {
        const badges = {
            UNCLASSIFIED: 'bg-gray-100 text-gray-800',
            CUI: 'bg-blue-100 text-blue-800',
            CONFIDENTIAL: 'bg-purple-100 text-purple-800',
            SECRET: 'bg-orange-100 text-orange-800',
            TOP_SECRET: 'bg-red-100 text-red-800',
            ITAR: 'bg-red-200 text-red-900 font-bold',
        };
        return badges[classification as keyof typeof badges] || 'bg-gray-100 text-gray-800';
    };

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="container mx-auto px-4 py-8 max-w-7xl">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Design Assets</h1>
                        <p className="text-gray-600 mt-2">
                            Manage engineering design files, CAD models, and technical drawings
                        </p>
                    </div>
                    <button
                        onClick={() => router.push('/designs/upload')}
                        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2 shadow-sm"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        <span>Upload Design</span>
                    </button>
                </div>

                {/* View Toggle & Search */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
                    <div className="flex items-center justify-between flex-wrap gap-4">
                        {/* View Toggle */}
                        <div className="flex items-center space-x-2">
                            <button
                                onClick={() => setView('designs')}
                                className={`px-4 py-2 rounded-lg font-medium transition-colors ${view === 'designs'
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                    }`}
                            >
                                All Designs
                            </button>
                            <button
                                onClick={() => setView('series')}
                                className={`px-4 py-2 rounded-lg font-medium transition-colors ${view === 'series'
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                    }`}
                            >
                                Part Numbers
                            </button>
                        </div>

                        {/* Search */}
                        <div className="flex-1 max-w-md">
                            <div className="relative">
                                <input
                                    type="text"
                                    placeholder={view === 'designs' ? "Search designs..." : "Search part numbers..."}
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                                <svg
                                    className="absolute left-3 top-2.5 w-5 h-5 text-gray-400"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                            </div>
                        </div>

                        {/* Filters (Only for designs view) */}
                        {view === 'designs' && (
                            <div className="flex items-center space-x-2">
                                <select
                                    value={statusFilter}
                                    onChange={(e) => setStatusFilter(e.target.value)}
                                    className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="all">All Status</option>
                                    <option value="UPLOADED">Uploaded</option>
                                    <option value="PROCESSING">Processing</option>
                                    <option value="PROCESSED">Processed</option>
                                    <option value="APPROVED">Approved</option>
                                    <option value="REJECTED">Rejected</option>
                                    <option value="FAILED">Failed</option>
                                </select>

                                <select
                                    value={classificationFilter}
                                    onChange={(e) => setClassificationFilter(e.target.value)}
                                    className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="all">All Classifications</option>
                                    <option value="UNCLASSIFIED">Unclassified</option>
                                    <option value="CUI">CUI</option>
                                    <option value="CONFIDENTIAL">Confidential</option>
                                    <option value="SECRET">Secret</option>
                                    <option value="TOP_SECRET">Top Secret</option>
                                    <option value="ITAR">ITAR</option>
                                </select>
                            </div>
                        )}
                    </div>
                </div>

                {/* Content */}
                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
                    </div>
                ) : view === 'designs' ? (
                    /* Designs List View */
                    filteredDesigns.length === 0 ? (
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
                            <svg className="w-20 h-20 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            <h3 className="text-lg font-semibold text-gray-900 mb-2">No designs found</h3>
                            <p className="text-gray-500 mb-4">
                                {searchQuery ? 'Try adjusting your search or filters' : 'Upload your first design to get started'}
                            </p>
                            {!searchQuery && (
                                <button
                                    onClick={() => router.push('/designs/upload')}
                                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                                >
                                    Upload Design
                                </button>
                            )}
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 gap-4">
                            {filteredDesigns.map((design) => (
                                <Link
                                    key={design.id}
                                    href={`/designs/${design.id}`}
                                    className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-all hover:border-blue-300"
                                >
                                    <div className="flex items-start justify-between">
                                        <div className="flex items-start space-x-4 flex-1">
                                            {/* File Icon */}
                                            <div className="flex-shrink-0">
                                                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                                                    <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                    </svg>
                                                </div>
                                            </div>

                                            {/* Design Info */}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center space-x-3 mb-2">
                                                    <h3 className="text-lg font-semibold text-gray-900 truncate">
                                                        {design.filename}
                                                    </h3>
                                                    <span className={`px-3 py-1 text-xs font-medium rounded-full border ${getStatusBadge(design.status)}`}>
                                                        {design.status}
                                                    </span>
                                                    <span className={`px-3 py-1 text-xs font-medium rounded-full ${getClassificationBadge(design.classification)}`}>
                                                        {design.classification}
                                                    </span>
                                                </div>

                                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                                    <div>
                                                        <span className="text-gray-500">Part Number:</span>
                                                        <p className="font-medium text-gray-900">{design.part_number}</p>
                                                    </div>
                                                    <div>
                                                        <span className="text-gray-500">Version:</span>
                                                        <p className="font-medium text-gray-900">v{design.version_number}</p>
                                                    </div>
                                                    <div>
                                                        <span className="text-gray-500">File Size:</span>
                                                        <p className="font-medium text-gray-900">{formatFileSize(design.file_size_bytes)}</p>
                                                    </div>
                                                    <div>
                                                        <span className="text-gray-500">Uploaded By:</span>
                                                        <p className="font-medium text-gray-900">{design.uploaded_by_username}</p>
                                                    </div>
                                                </div>

                                                <div className="flex items-center space-x-4 mt-3 text-xs text-gray-500">
                                                    <span>Uploaded: {formatDate(design.created_at)}</span>
                                                    {design.updated_at !== design.created_at && (
                                                        <>
                                                            <span>•</span>
                                                            <span>Updated: {formatDate(design.updated_at)}</span>
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Arrow Icon */}
                                        <div className="flex-shrink-0 ml-4">
                                            <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                            </svg>
                                        </div>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    )
                ) : (
                    /* Series/Part Numbers List View */
                    filteredSeries.length === 0 ? (
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
                            <svg className="w-20 h-20 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                            </svg>
                            <h3 className="text-lg font-semibold text-gray-900 mb-2">No part numbers found</h3>
                            <p className="text-gray-500">
                                {searchQuery ? 'Try adjusting your search' : 'Part numbers will appear here once designs are uploaded'}
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {filteredSeries.map((s) => (
                                <Link
                                    key={s.id}
                                    href={`/series/${s.id}`}
                                    className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-all hover:border-blue-300"
                                >
                                    <div className="flex items-start justify-between mb-4">
                                        <div className="flex items-center space-x-3">
                                            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                                                <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                                </svg>
                                            </div>
                                            <div>
                                                <h3 className="font-semibold text-gray-900">{s.part_number}</h3>
                                                <p className="text-sm text-gray-600">{s.name}</p>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="space-y-2 text-sm">
                                        <div className="flex items-center justify-between">
                                            <span className="text-gray-500">Versions:</span>
                                            <span className="font-medium text-gray-900">{s.version_count}</span>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <span className="text-gray-500">Latest Version:</span>
                                            <span className="font-medium text-gray-900">v{s.latest_version_number}</span>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <span className="text-gray-500">Created By:</span>
                                            <span className="font-medium text-gray-900">{s.created_by_username}</span>
                                        </div>
                                    </div>

                                    <div className="mt-4 pt-4 border-t border-gray-200">
                                        <p className="text-xs text-gray-500">
                                            Created {formatDate(s.created_at)}
                                        </p>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    )
                )}
            </div>
        </div>
    );
}
