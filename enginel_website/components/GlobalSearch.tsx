'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import ApiClient from '@/lib/api/client';

interface SearchResult {
    id: string;
    type: 'series' | 'design' | 'review' | 'user';
    title: string;
    subtitle?: string;
    description?: string;
    url: string;
}

interface GlobalSearchProps {
    onClose?: () => void;
}

export default function GlobalSearch({ onClose }: GlobalSearchProps) {
    const router = useRouter();
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [showResults, setShowResults] = useState(false);
    const searchRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
                setShowResults(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    useEffect(() => {
        const searchTimeout = setTimeout(() => {
            if (query.trim().length >= 2) {
                performSearch(query.trim());
            } else {
                setResults([]);
                setShowResults(false);
            }
        }, 300);

        return () => clearTimeout(searchTimeout);
    }, [query]);

    const performSearch = async (searchQuery: string) => {
        try {
            setLoading(true);
            setShowResults(true);

            const [seriesRes, designsRes, reviewsRes, usersRes] = await Promise.all([
                ApiClient.get<{ results: any[] }>(`/series/?search=${encodeURIComponent(searchQuery)}`).catch(() => ({ results: [] })),
                ApiClient.get<{ results: any[] }>(`/designs/?search=${encodeURIComponent(searchQuery)}`).catch(() => ({ results: [] })),
                ApiClient.get<{ results: any[] }>(`/reviews/?search=${encodeURIComponent(searchQuery)}`).catch(() => ({ results: [] })),
                ApiClient.get<{ results: any[] }>(`/users/?search=${encodeURIComponent(searchQuery)}`).catch(() => ({ results: [] })),
            ]);

            const searchResults: SearchResult[] = [
                ...(seriesRes.results || []).slice(0, 3).map((item: any) => ({
                    id: item.id,
                    type: 'series' as const,
                    title: item.part_number,
                    subtitle: item.name,
                    description: item.description,
                    url: `/series/${item.id}`,
                })),
                ...(designsRes.results || []).slice(0, 3).map((item: any) => ({
                    id: item.id,
                    type: 'design' as const,
                    title: item.file_name || item.filename,
                    subtitle: typeof item.series === 'string' ? item.series : item.series?.part_number,
                    description: `Version ${item.version_label || item.version_number}`,
                    url: `/designs/${item.id}`,
                })),
                ...(reviewsRes.results || []).slice(0, 3).map((item: any) => ({
                    id: item.id,
                    type: 'review' as const,
                    title: item.title || `Review #${item.id}`,
                    subtitle: item.review_type,
                    description: item.description,
                    url: `/reviews/${item.id}`,
                })),
                ...(usersRes.results || []).slice(0, 3).map((item: any) => ({
                    id: item.id,
                    type: 'user' as const,
                    title: `${item.first_name} ${item.last_name}`.trim() || item.username,
                    subtitle: item.email,
                    description: item.security_clearance_level,
                    url: `/profile`, // Could be user detail page if you create one
                })),
            ];

            setResults(searchResults);
        } catch (error) {
            console.error('Search error:', error);
            setResults([]);
        } finally {
            setLoading(false);
        }
    };

    const handleResultClick = (result: SearchResult) => {
        router.push(result.url);
        setQuery('');
        setResults([]);
        setShowResults(false);
        if (onClose) onClose();
    };

    const handleViewAll = () => {
        router.push(`/search?q=${encodeURIComponent(query)}`);
        setShowResults(false);
        if (onClose) onClose();
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
        };
        return colors[type as keyof typeof colors] || 'bg-gray-100 text-gray-800';
    };

    return (
        <div ref={searchRef} className="relative w-full max-w-xl">
            <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
                <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => query.trim().length >= 2 && setShowResults(true)}
                    placeholder="Search designs, series, reviews..."
                    className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                />
                {loading && (
                    <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    </div>
                )}
            </div>

            {/* Search Results Dropdown */}
            {showResults && (query.trim().length >= 2) && (
                <div className="absolute z-50 mt-2 w-full bg-white rounded-lg shadow-xl border border-gray-200 max-h-96 overflow-y-auto">
                    {results.length === 0 && !loading ? (
                        <div className="px-4 py-8 text-center text-gray-500">
                            <svg className="w-12 h-12 text-gray-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <p className="font-medium">No results found</p>
                            <p className="text-sm mt-1">Try different keywords</p>
                        </div>
                    ) : (
                        <>
                            {results.map((result) => (
                                <button
                                    key={`${result.type}-${result.id}`}
                                    onClick={() => handleResultClick(result)}
                                    className="w-full px-4 py-3 hover:bg-gray-50 transition-colors flex items-start space-x-3 border-b border-gray-100 last:border-0"
                                >
                                    <div className={`flex-shrink-0 mt-0.5 ${result.type === 'series' ? 'text-blue-600' : result.type === 'design' ? 'text-green-600' : result.type === 'review' ? 'text-purple-600' : 'text-orange-600'}`}>
                                        {getTypeIcon(result.type)}
                                    </div>
                                    <div className="flex-1 min-w-0 text-left">
                                        <div className="flex items-center space-x-2 mb-1">
                                            <p className="text-sm font-medium text-gray-900 truncate">{result.title}</p>
                                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${getTypeBadge(result.type)}`}>
                                                {result.type}
                                            </span>
                                        </div>
                                        {result.subtitle && (
                                            <p className="text-xs text-gray-600 truncate">{result.subtitle}</p>
                                        )}
                                        {result.description && (
                                            <p className="text-xs text-gray-500 truncate mt-0.5">{result.description}</p>
                                        )}
                                    </div>
                                </button>
                            ))}

                            {results.length > 0 && (
                                <button
                                    onClick={handleViewAll}
                                    className="w-full px-4 py-3 text-center text-sm font-medium text-blue-600 hover:bg-blue-50 transition-colors"
                                >
                                    View all results for "{query}"
                                </button>
                            )}
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
