'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import ApiClient from '@/lib/api/client';
import Link from 'next/link';

interface SearchResult {
    id: string;
    type: 'series' | 'design' | 'review' | 'user' | 'validation';
    title: string;
    subtitle?: string;
    description?: string;
    url: string;
    metadata?: Record<string, any>;
}

interface SearchStats {
    series: number;
    designs: number;
    reviews: number;
    users: number;
    validation: number;
    total: number;
}

function SearchContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const query = searchParams.get('q') || '';
    const typeFilter = searchParams.get('type') || 'all';

    const [results, setResults] = useState<SearchResult[]>([]);
    const [stats, setStats] = useState<SearchStats>({
        series: 0,
        designs: 0,
        reviews: 0,
        users: 0,
        validation: 0,
        total: 0,
    });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (query.trim().length >= 2) {
            performSearch(query.trim());
        }
    }, [query, typeFilter]);

    const performSearch = async (searchQuery: string) => {
        try {
            setLoading(true);

            const [seriesRes, designsRes, reviewsRes, usersRes, validationRes] = await Promise.all([
                ApiClient.get<{ results: any[]; count?: number }>(`/series/?search=${encodeURIComponent(searchQuery)}`).catch(() => ({ results: [], count: 0 })),
                ApiClient.get<{ results: any[]; count?: number }>(`/designs/?search=${encodeURIComponent(searchQuery)}`).catch(() => ({ results: [], count: 0 })),
                ApiClient.get<{ results: any[]; count?: number }>(`/reviews/?search=${encodeURIComponent(searchQuery)}`).catch(() => ({ results: [], count: 0 })),
                ApiClient.get<{ results: any[]; count?: number }>(`/users/?search=${encodeURIComponent(searchQuery)}`).catch(() => ({ results: [], count: 0 })),
                ApiClient.get<{ results: any[]; count?: number }>(`/validation/rules/?search=${encodeURIComponent(searchQuery)}`).catch(() => ({ results: [], count: 0 })),
            ]);

            const newStats = {
                series: seriesRes.count || seriesRes.results.length,
                designs: designsRes.count || designsRes.results.length,
                reviews: reviewsRes.count || reviewsRes.results.length,
                users: usersRes.count || usersRes.results.length,
                validation: validationRes.count || validationRes.results.length,
                total: 0,
            };
            newStats.total = newStats.series + newStats.designs + newStats.reviews + newStats.users + newStats.validation;
            setStats(newStats);

            let allResults: SearchResult[] = [];

            if (typeFilter === 'all' || typeFilter === 'series') {
                allResults.push(
                    ...(seriesRes.results || []).map((item: any) => ({
                        id: item.id,
                        type: 'series' as const,
                        title: item.part_number,
                        subtitle: item.name,
                        description: item.description,
                        url: `/series/${item.id}`,
                        metadata: {
                            created: item.created_at,
                            updated: item.updated_at,
                            status: item.lifecycle_stage,
                        },
                    }))
                );
            }

            if (typeFilter === 'all' || typeFilter === 'design') {
                allResults.push(
                    ...(designsRes.results || []).map((item: any) => ({
                        id: item.id,
                        type: 'design' as const,
                        title: item.file_name || item.filename,
                        subtitle: typeof item.series === 'string' ? item.series : item.series?.part_number,
                        description: `Version ${item.version_label || item.version_number} • ${item.revision || 'A'}`,
                        url: `/designs/${item.id}`,
                        metadata: {
                            uploaded: item.created_at,
                            fileSize: item.file_size,
                            fileType: item.file_type,
                        },
                    }))
                );
            }

            if (typeFilter === 'all' || typeFilter === 'review') {
                allResults.push(
                    ...(reviewsRes.results || []).map((item: any) => ({
                        id: item.id,
                        type: 'review' as const,
                        title: item.title || `Review #${item.id}`,
                        subtitle: `${item.review_type} • ${item.status}`,
                        description: item.description,
                        url: `/reviews/${item.id}`,
                        metadata: {
                            created: item.created_at,
                            updated: item.updated_at,
                            status: item.status,
                        },
                    }))
                );
            }

            if (typeFilter === 'all' || typeFilter === 'user') {
                allResults.push(
                    ...(usersRes.results || []).map((item: any) => ({
                        id: item.id,
                        type: 'user' as const,
                        title: `${item.first_name} ${item.last_name}`.trim() || item.username,
                        subtitle: item.email,
                        description: `@${item.username} • ${item.security_clearance_level || 'No clearance'}`,
                        url: `/profile`,
                        metadata: {
                            username: item.username,
                            clearance: item.security_clearance_level,
                        },
                    }))
                );
            }

            if (typeFilter === 'all' || typeFilter === 'validation') {
                allResults.push(
                    ...(validationRes.results || []).map((item: any) => ({
                        id: item.id,
                        type: 'validation' as const,
                        title: item.name,
                        subtitle: `${item.rule_type} • ${item.target_model}`,
                        description: item.description,
                        url: `/validation/${item.id}`,
                        metadata: {
                            severity: item.severity,
                            isActive: item.is_active,
                        },
                    }))
                );
            }

            setResults(allResults);
        } catch (error) {
            console.error('Search error:', error);
            setResults([]);
        } finally {
            setLoading(false);
        }
    };

    const setFilter = (type: string) => {
        const params = new URLSearchParams(searchParams.toString());
        if (type === 'all') {
            params.delete('type');
        } else {
            params.set('type', type);
        }
        router.push(`/search?${params.toString()}`);
    };

    const getTypeIcon = (type: string) => {
        switch (type) {
            case 'series':
                return (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                );
            case 'design':
                return (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                );
            case 'review':
                return (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                );
            case 'user':
                return (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                );
            case 'validation':
                return (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                );
            default:
                return null;
        }
    };

    const getTypeBadge = (type: string) => {
        const colors = {
            series: 'bg-blue-100 text-blue-800',
            design: 'bg-green-100 text-green-800',
            review: 'bg-purple-100 text-purple-800',
            user: 'bg-orange-100 text-orange-800',
            validation: 'bg-indigo-100 text-indigo-800',
        };
        return colors[type as keyof typeof colors] || 'bg-gray-100 text-gray-800';
    };

    if (query.trim().length < 2) {
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <div className="text-center">
                    <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    <h1 className="text-2xl font-bold text-gray-900 mb-2">Search Enginel</h1>
                    <p className="text-gray-600">Enter at least 2 characters to search</p>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Search Header */}
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900 mb-2">
                    Search results for "<span className="text-blue-600">{query}</span>"
                </h1>
                <p className="text-gray-600">
                    {loading ? 'Searching...' : `Found ${stats.total} result${stats.total !== 1 ? 's' : ''}`}
                </p>
            </div>

            {/* Type Filters */}
            <div className="flex flex-wrap gap-2 mb-6">
                <button
                    onClick={() => setFilter('all')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${typeFilter === 'all'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    All ({stats.total})
                </button>
                <button
                    onClick={() => setFilter('series')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${typeFilter === 'series'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    Series ({stats.series})
                </button>
                <button
                    onClick={() => setFilter('design')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${typeFilter === 'design'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    Designs ({stats.designs})
                </button>
                <button
                    onClick={() => setFilter('review')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${typeFilter === 'review'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    Reviews ({stats.reviews})
                </button>
                <button
                    onClick={() => setFilter('user')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${typeFilter === 'user'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    Users ({stats.users})
                </button>
                <button
                    onClick={() => setFilter('validation')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${typeFilter === 'validation'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    Validation ({stats.validation})
                </button>
            </div>

            {/* Results */}
            {loading ? (
                <div className="flex justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            ) : results.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-lg shadow">
                    <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No results found</h3>
                    <p className="text-gray-600">Try different keywords or filters</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {results.map((result) => (
                        <Link
                            key={`${result.type}-${result.id}`}
                            href={result.url}
                            className="block bg-white rounded-lg shadow hover:shadow-lg transition-all p-5 border border-gray-200 hover:border-blue-300"
                        >
                            <div className="flex items-start space-x-4">
                                <div className={`flex-shrink-0 mt-1 ${result.type === 'series' ? 'text-blue-600' :
                                        result.type === 'design' ? 'text-green-600' :
                                            result.type === 'review' ? 'text-purple-600' :
                                                result.type === 'user' ? 'text-orange-600' :
                                                    'text-indigo-600'
                                    }`}>
                                    {getTypeIcon(result.type)}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center space-x-2 mb-1">
                                        <h3 className="text-lg font-semibold text-gray-900 truncate">{result.title}</h3>
                                        <span className={`px-2.5 py-0.5 text-xs font-medium rounded-full ${getTypeBadge(result.type)}`}>
                                            {result.type}
                                        </span>
                                    </div>
                                    {result.subtitle && (
                                        <p className="text-sm text-gray-700 mb-1">{result.subtitle}</p>
                                    )}
                                    {result.description && (
                                        <p className="text-sm text-gray-600 line-clamp-2">{result.description}</p>
                                    )}
                                    {result.metadata && (
                                        <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-500">
                                            {result.metadata.created && (
                                                <span>Created {new Date(result.metadata.created).toLocaleDateString()}</span>
                                            )}
                                            {result.metadata.status && (
                                                <span>• {result.metadata.status}</span>
                                            )}
                                            {result.metadata.severity && (
                                                <span className={`font-medium ${result.metadata.severity === 'ERROR' ? 'text-red-600' :
                                                        result.metadata.severity === 'WARNING' ? 'text-yellow-600' :
                                                            'text-blue-600'
                                                    }`}>
                                                    • {result.metadata.severity}
                                                </span>
                                            )}
                                        </div>
                                    )}
                                </div>
                                <div className="flex-shrink-0">
                                    <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                    </svg>
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}

export default function SearchPage() {
    return (
        <Suspense fallback={
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <div className="flex justify-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            </div>
        }>
            <SearchContent />
        </Suspense>
    );
}
