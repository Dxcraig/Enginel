'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import ApiClient from '@/lib/api/client';
import { ReviewSession } from '@/types';
import Link from 'next/link';

export default function ReviewsPage() {
    const { user, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const [reviews, setReviews] = useState<ReviewSession[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [filter, setFilter] = useState<'all' | 'DRAFT' | 'ACTIVE' | 'COMPLETED' | 'CANCELLED'>('all');

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (user) {
            loadReviews();
        }
    }, [user, filter]);

    const loadReviews = async () => {
        try {
            setLoading(true);
            const params = filter !== 'all' ? `?status=${filter}` : '';
            const data = await ApiClient.get<{ results: ReviewSession[] }>(`/reviews/${params}`);
            setReviews(data.results || []);
            setError('');
        } catch (err: any) {
            console.error('Load reviews error:', err);
            setError(err.message || err.toString() || 'Failed to load reviews');
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'COMPLETED':
                return 'bg-green-100 text-green-800';
            case 'CANCELLED':
                return 'bg-red-100 text-red-800';
            case 'DRAFT':
                return 'bg-gray-100 text-gray-800';
            case 'ACTIVE':
                return 'bg-blue-100 text-blue-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    if (authLoading || !user) {
        return null;
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-3xl font-bold text-gray-900">Design Reviews</h1>
                <Link
                    href="/reviews/create"
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                >
                    + New Review
                </Link>
            </div>

            {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                    {error}
                </div>
            )}

            {/* Filter Tabs */}
            <div className="mb-6 border-b border-gray-200">
                <nav className="flex space-x-8">
                    {[
                        { value: 'all', label: 'All' },
                        { value: 'DRAFT', label: 'Draft' },
                        { value: 'ACTIVE', label: 'Active' },
                        { value: 'COMPLETED', label: 'Completed' },
                        { value: 'CANCELLED', label: 'Cancelled' }
                    ].map((tab) => (
                        <button
                            key={tab.value}
                            onClick={() => setFilter(tab.value as any)}
                            className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${filter === tab.value
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </nav>
            </div>

            {loading ? (
                <div className="flex justify-center items-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            ) : (
                <div className="grid gap-4">
                    {reviews.length === 0 ? (
                        <div className="bg-white shadow-md rounded-lg p-12 text-center">
                            <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            <h3 className="text-lg font-medium text-gray-900 mb-2">No reviews found</h3>
                            <p className="text-gray-500 mb-4">Create a new review to get started.</p>
                            <Link
                                href="/reviews/create"
                                className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                            >
                                + New Review
                            </Link>
                        </div>
                    ) : (
                        reviews.map((review) => (
                            <Link
                                key={review.id}
                                href={`/reviews/${review.id}`}
                                className="block bg-white shadow-md rounded-lg p-6 hover:shadow-lg transition-shadow"
                            >
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex-1">
                                        <h3 className="text-lg font-semibold text-gray-900">
                                            {review.title || `Review #${review.id}`}
                                        </h3>
                                        {review.description && (
                                            <p className="text-gray-600 mt-1 line-clamp-2">{review.description}</p>
                                        )}
                                    </div>
                                    <span className={`px-3 py-1 text-sm font-semibold rounded-full ml-4 flex-shrink-0 ${getStatusColor(review.status)}`}>
                                        {review.status}
                                    </span>
                                </div>

                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                    <div>
                                        <div className="text-gray-500 mb-1">Created By</div>
                                        <div className="font-medium">{review.created_by_username || 'Unknown'}</div>
                                    </div>
                                    <div>
                                        <div className="text-gray-500 mb-1">Created</div>
                                        <div className="font-medium">{new Date(review.created_at).toLocaleDateString()}</div>
                                    </div>
                                    <div>
                                        <div className="text-gray-500 mb-1">Reviewers</div>
                                        <div className="font-medium">{review.reviewer_usernames?.length || 0}</div>
                                    </div>
                                    <div>
                                        <div className="text-gray-500 mb-1">Comments</div>
                                        <div className="font-medium">{review.markup_count || 0}</div>
                                    </div>
                                </div>

                                {review.started_at && (
                                    <div className="mt-4 pt-4 border-t border-gray-200 flex items-center text-sm text-gray-500">
                                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        Started {new Date(review.started_at).toLocaleDateString()}
                                    </div>
                                )}
                            </Link>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}
