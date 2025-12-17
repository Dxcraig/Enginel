'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useParams } from 'next/navigation';
import ApiClient from '@/lib/api/client';
import { ReviewSession, Markup } from '@/types';
import Link from 'next/link';

export default function ReviewDetailPage() {
    const { user, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const params = useParams();
    const reviewId = params.id as string;

    const [review, setReview] = useState<ReviewSession | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [newComment, setNewComment] = useState('');
    const [newMarkupTitle, setNewMarkupTitle] = useState('');
    const [submittingComment, setSubmittingComment] = useState(false);
    const [activeTab, setActiveTab] = useState<'comments' | 'reviewers'>('comments');

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (user && reviewId) {
            loadReviewDetail();
        }
    }, [user, reviewId]);

    const loadReviewDetail = async () => {
        try {
            setLoading(true);
            const reviewData = await ApiClient.get<ReviewSession>(`/reviews/${reviewId}/`);
            setReview(reviewData);
            setError('');
        } catch (err: any) {
            console.error('Load review error:', err);
            setError(err.message || 'Failed to load review details');
        } finally {
            setLoading(false);
        }
    };

    const handleAddComment = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newComment.trim() || !newMarkupTitle.trim()) return;

        try {
            setSubmittingComment(true);
            await ApiClient.post('/markups/', {
                review_session: reviewId,
                title: newMarkupTitle,
                comment: newComment,
                anchor_point: { x: 0, y: 0, z: 0 }, // Default position
                camera_state: {
                    position: { x: 0, y: 0, z: 100 },
                    target: { x: 0, y: 0, z: 0 },
                    up: { x: 0, y: 1, z: 0 }
                },
                is_resolved: false
            });
            setNewComment('');
            setNewMarkupTitle('');
            loadReviewDetail();
        } catch (err: any) {
            console.error('Add comment error:', err);
            setError(err.message || 'Failed to add comment');
        } finally {
            setSubmittingComment(false);
        }
    };

    const handleStatusChange = async (newStatus: 'DRAFT' | 'ACTIVE' | 'COMPLETED' | 'CANCELLED') => {
        try {
            await ApiClient.patch(`/reviews/${reviewId}/`, { status: newStatus });
            loadReviewDetail();
        } catch (err: any) {
            console.error('Status change error:', err);
            setError(err.message || 'Failed to update review status');
        }
    };

    const toggleMarkupResolved = async (markupId: string, currentStatus: boolean) => {
        try {
            await ApiClient.patch(`/markups/${markupId}/`, { is_resolved: !currentStatus });
            loadReviewDetail();
        } catch (err: any) {
            console.error('Toggle markup error:', err);
            setError(err.message || 'Failed to update markup');
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

    if (loading) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="flex justify-center items-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            </div>
        );
    }

    if (error && !review) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                    {error}
                </div>
                <Link href="/reviews" className="mt-4 inline-flex items-center text-blue-600 hover:text-blue-700">
                    ← Back to Reviews
                </Link>
            </div>
        );
    }

    if (!review) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="p-4 bg-yellow-50 border border-yellow-200 text-yellow-700 rounded-lg">
                    Review not found
                </div>
                <Link href="/reviews" className="mt-4 inline-flex items-center text-blue-600 hover:text-blue-700">
                    ← Back to Reviews
                </Link>
            </div>
        );
    }

    const markups = review.markups || [];
    const unresolvedCount = markups.filter(m => !m.is_resolved).length;

    return (
        <div className="container mx-auto px-4 py-8">
            {/* Header */}
            <div className="mb-6">
                <Link href="/reviews" className="text-blue-600 hover:text-blue-700 mb-4 inline-flex items-center">
                    <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                    Back to Reviews
                </Link>
                <div className="flex justify-between items-start mt-2">
                    <div className="flex-1">
                        <h1 className="text-3xl font-bold text-gray-900">
                            {review.title || `Review #${review.id}`}
                        </h1>
                        {review.description && (
                            <p className="text-gray-600 mt-2">{review.description}</p>
                        )}
                        <div className="flex items-center space-x-4 mt-4 text-sm text-gray-500">
                            <span>Created by {review.created_by_username || 'Unknown'}</span>
                            <span>•</span>
                            <span>{new Date(review.created_at).toLocaleDateString()}</span>
                        </div>
                    </div>
                    <div className="flex flex-col items-end space-y-2">
                        <span className={`px-3 py-1 text-sm font-semibold rounded-full ${getStatusColor(review.status)}`}>
                            {review.status}
                        </span>
                    </div>
                </div>
            </div>

            {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                    {error}
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Main Content */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Stats Cards */}
                    <div className="grid grid-cols-3 gap-4">
                        <div className="bg-white shadow-md rounded-lg p-4">
                            <div className="text-2xl font-bold text-blue-600">{markups.length}</div>
                            <div className="text-sm text-gray-500">Total Comments</div>
                        </div>
                        <div className="bg-white shadow-md rounded-lg p-4">
                            <div className="text-2xl font-bold text-orange-600">{unresolvedCount}</div>
                            <div className="text-sm text-gray-500">Unresolved</div>
                        </div>
                        <div className="bg-white shadow-md rounded-lg p-4">
                            <div className="text-2xl font-bold text-purple-600">
                                {review.reviewer_usernames?.length || 0}
                            </div>
                            <div className="text-sm text-gray-500">Reviewers</div>
                        </div>
                    </div>

                    {/* Design Asset Link */}
                    {review.design_asset_detail && (
                        <div className="bg-white shadow-md rounded-lg p-6">
                            <h2 className="text-lg font-semibold mb-4">Design Asset</h2>
                            <Link
                                href={`/designs/${review.design_asset}`}
                                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                                <div className="flex items-center space-x-3">
                                    <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    <div>
                                        <div className="font-medium text-blue-600">
                                            {review.design_asset_detail.file_name || review.design_asset_detail.filename}
                                        </div>
                                        <div className="text-sm text-gray-500">
                                            Version {review.design_asset_detail.version_number || '1.0'}
                                        </div>
                                    </div>
                                </div>
                                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                            </Link>
                        </div>
                    )}

                    {/* Tabs */}
                    <div className="bg-white shadow-md rounded-lg">
                        <div className="border-b border-gray-200">
                            <nav className="flex">
                                <button
                                    onClick={() => setActiveTab('comments')}
                                    className={`px-6 py-4 font-medium text-sm border-b-2 transition-colors ${activeTab === 'comments'
                                            ? 'border-blue-500 text-blue-600'
                                            : 'border-transparent text-gray-500 hover:text-gray-700'
                                        }`}
                                >
                                    Comments ({markups.length})
                                </button>
                                <button
                                    onClick={() => setActiveTab('reviewers')}
                                    className={`px-6 py-4 font-medium text-sm border-b-2 transition-colors ${activeTab === 'reviewers'
                                            ? 'border-blue-500 text-blue-600'
                                            : 'border-transparent text-gray-500 hover:text-gray-700'
                                        }`}
                                >
                                    Reviewers ({review.reviewer_usernames?.length || 0})
                                </button>
                            </nav>
                        </div>

                        <div className="p-6">
                            {activeTab === 'comments' ? (
                                <>
                                    {/* Add Comment Form */}
                                    {review.status !== 'COMPLETED' && review.status !== 'CANCELLED' && (
                                        <form onSubmit={handleAddComment} className="mb-6 p-4 bg-gray-50 rounded-lg">
                                            <div className="mb-3">
                                                <input
                                                    type="text"
                                                    value={newMarkupTitle}
                                                    onChange={(e) => setNewMarkupTitle(e.target.value)}
                                                    placeholder="Comment title..."
                                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                />
                                            </div>
                                            <textarea
                                                value={newComment}
                                                onChange={(e) => setNewComment(e.target.value)}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                rows={3}
                                                placeholder="Add your comment or feedback..."
                                            />
                                            <div className="mt-3 flex justify-end">
                                                <button
                                                    type="submit"
                                                    disabled={submittingComment || !newComment.trim() || !newMarkupTitle.trim()}
                                                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                                                >
                                                    {submittingComment ? 'Adding...' : 'Add Comment'}
                                                </button>
                                            </div>
                                        </form>
                                    )}

                                    {/* Comments List */}
                                    <div className="space-y-4">
                                        {markups.length === 0 ? (
                                            <div className="text-center py-12 text-gray-500">
                                                <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                                </svg>
                                                <p className="font-medium">No comments yet</p>
                                                <p className="text-sm mt-1">Be the first to add feedback!</p>
                                            </div>
                                        ) : (
                                            markups.map((markup) => (
                                                <div
                                                    key={markup.id}
                                                    className={`p-4 rounded-lg border-l-4 ${markup.is_resolved
                                                            ? 'bg-green-50 border-green-500'
                                                            : 'bg-white border-blue-500'
                                                        }`}
                                                >
                                                    <div className="flex justify-between items-start mb-2">
                                                        <div className="flex-1">
                                                            <h4 className="font-semibold text-gray-900">{markup.title}</h4>
                                                            <div className="flex items-center space-x-2 mt-1 text-sm text-gray-500">
                                                                <span>{markup.author_username || 'Unknown'}</span>
                                                                <span>•</span>
                                                                <span>{new Date(markup.created_at).toLocaleString()}</span>
                                                            </div>
                                                        </div>
                                                        <button
                                                            onClick={() => toggleMarkupResolved(markup.id, markup.is_resolved)}
                                                            className={`px-3 py-1 text-xs font-semibold rounded-full transition-colors ${markup.is_resolved
                                                                    ? 'bg-green-100 text-green-800 hover:bg-green-200'
                                                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                                                }`}
                                                        >
                                                            {markup.is_resolved ? '✓ Resolved' : 'Mark Resolved'}
                                                        </button>
                                                    </div>
                                                    <p className="text-gray-700 whitespace-pre-wrap">{markup.comment}</p>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </>
                            ) : (
                                <div className="space-y-3">
                                    {review.reviewer_usernames && review.reviewer_usernames.length > 0 ? (
                                        review.reviewer_usernames.map((username, idx) => (
                                            <div key={idx} className="flex items-center p-3 bg-gray-50 rounded-lg">
                                                <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-semibold mr-3">
                                                    {username.charAt(0).toUpperCase()}
                                                </div>
                                                <div>
                                                    <div className="font-medium text-gray-900">{username}</div>
                                                    <div className="text-sm text-gray-500">Reviewer</div>
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-center py-8 text-gray-500">
                                            No reviewers assigned yet
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Sidebar */}
                <div className="space-y-6">
                    {/* Actions Card */}
                    <div className="bg-white shadow-md rounded-lg p-6">
                        <h2 className="text-lg font-semibold mb-4">Actions</h2>
                        <div className="space-y-3">
                            {review.status === 'DRAFT' && (
                                <button
                                    onClick={() => handleStatusChange('ACTIVE')}
                                    className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                                >
                                    Start Review
                                </button>
                            )}
                            {review.status === 'ACTIVE' && (
                                <>
                                    <button
                                        onClick={() => handleStatusChange('COMPLETED')}
                                        className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                                    >
                                        Complete Review
                                    </button>
                                    <button
                                        onClick={() => handleStatusChange('CANCELLED')}
                                        className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                                    >
                                        Cancel Review
                                    </button>
                                </>
                            )}
                            {(review.status === 'COMPLETED' || review.status === 'CANCELLED') && (
                                <button
                                    onClick={() => handleStatusChange('ACTIVE')}
                                    className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                                >
                                    Reopen Review
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Timeline Card */}
                    <div className="bg-white shadow-md rounded-lg p-6">
                        <h2 className="text-lg font-semibold mb-4">Timeline</h2>
                        <div className="space-y-4">
                            <div className="flex items-start">
                                <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 mr-3"></div>
                                <div className="flex-1">
                                    <div className="text-sm font-medium text-gray-900">Created</div>
                                    <div className="text-xs text-gray-500">
                                        {new Date(review.created_at).toLocaleString()}
                                    </div>
                                </div>
                            </div>
                            {review.started_at && (
                                <div className="flex items-start">
                                    <div className="w-2 h-2 bg-green-600 rounded-full mt-2 mr-3"></div>
                                    <div className="flex-1">
                                        <div className="text-sm font-medium text-gray-900">Started</div>
                                        <div className="text-xs text-gray-500">
                                            {new Date(review.started_at).toLocaleString()}
                                        </div>
                                    </div>
                                </div>
                            )}
                            {review.completed_at && (
                                <div className="flex items-start">
                                    <div className="w-2 h-2 bg-purple-600 rounded-full mt-2 mr-3"></div>
                                    <div className="flex-1">
                                        <div className="text-sm font-medium text-gray-900">Completed</div>
                                        <div className="text-xs text-gray-500">
                                            {new Date(review.completed_at).toLocaleString()}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
