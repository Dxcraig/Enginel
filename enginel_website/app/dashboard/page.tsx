'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import ApiClient from '@/lib/api/client';
import { DesignSeries, DesignAsset, ReviewSession } from '@/types';

interface DashboardStats {
    totalDesigns: number;
    totalSeries: number;
    activeReviews: number;
    completedReviews: number;
    recentUploads: number;
}

interface RecentActivity {
    id: string;
    type: 'design' | 'series' | 'review' | 'upload';
    title: string;
    description: string;
    timestamp: string;
    link?: string;
}

export default function DashboardPage() {
    const { user, isAuthenticated, isLoading } = useAuth();
    const router = useRouter();
    const [stats, setStats] = useState<DashboardStats>({
        totalDesigns: 0,
        totalSeries: 0,
        activeReviews: 0,
        completedReviews: 0,
        recentUploads: 0,
    });
    const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
    const [recentDesigns, setRecentDesigns] = useState<DesignAsset[]>([]);
    const [loadingData, setLoadingData] = useState(true);

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/login');
        }
    }, [isAuthenticated, isLoading, router]);

    useEffect(() => {
        if (user) {
            loadDashboardData();
        }
    }, [user]);

    const loadDashboardData = async () => {
        try {
            setLoadingData(true);

            // Check if user is authenticated
            const token = localStorage.getItem('enginel_auth_token');
            if (!token) {
                console.error('No authentication token found');
                router.push('/login');
                return;
            }

            console.log('Fetching dashboard data...');

            // Fetch all data in parallel with individual error handling
            const [seriesData, designsData, reviewsData] = await Promise.all([
                ApiClient.get<{ results: DesignSeries[] }>('/series/').catch(err => {
                    console.error('Failed to fetch series:', {
                        message: err?.message,
                        status: err?.status,
                        url: err?.url,
                        details: err?.details
                    });
                    return { results: [] };
                }),
                ApiClient.get<{ results: DesignAsset[] }>('/designs/').catch(err => {
                    console.error('Failed to fetch designs:', {
                        message: err?.message,
                        status: err?.status,
                        url: err?.url,
                        details: err?.details
                    });
                    return { results: [] };
                }),
                ApiClient.get<{ results: ReviewSession[] }>('/reviews/').catch(err => {
                    console.error('Failed to fetch reviews:', {
                        message: err?.message,
                        status: err?.status,
                        url: err?.url,
                        details: err?.details
                    });
                    return { results: [] };
                }),
            ]);

            console.log('Dashboard data loaded:', {
                series: seriesData.results.length,
                designs: designsData.results.length,
                reviews: reviewsData.results.length
            });

            // Calculate stats
            const now = new Date();
            const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

            const recentUploadsCount = designsData.results.filter(
                (d) => new Date(d.created_at) > sevenDaysAgo
            ).length;

            const activeReviewsCount = reviewsData.results.filter(
                (r) => r.status === 'ACTIVE' || r.status === 'DRAFT'
            ).length;

            const completedReviewsCount = reviewsData.results.filter(
                (r) => r.status === 'COMPLETED'
            ).length;

            setStats({
                totalDesigns: designsData.results.length,
                totalSeries: seriesData.results.length,
                activeReviews: activeReviewsCount,
                completedReviews: completedReviewsCount,
                recentUploads: recentUploadsCount,
            });

            // Get recent designs (last 5)
            const sortedDesigns = [...designsData.results]
                .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                .slice(0, 5);
            setRecentDesigns(sortedDesigns);

            // Build activity feed
            const activities: RecentActivity[] = [];

            // Recent designs
            sortedDesigns.slice(0, 3).forEach((design) => {
                activities.push({
                    id: design.id,
                    type: 'design',
                    title: 'New Design Upload',
                    description: `${design.filename || design.file_name || 'Design file'} uploaded`,
                    timestamp: design.created_at,
                    link: `/designs/${design.id}`,
                });
            });

            // Recent reviews
            reviewsData.results.slice(0, 3).forEach((review) => {
                activities.push({
                    id: review.id,
                    type: 'review',
                    title: review.title || 'Design Review',
                    description: `Status: ${review.status}`,
                    timestamp: review.created_at,
                    link: `/reviews/${review.id}`,
                });
            });

            // Sort by timestamp
            activities.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
            setRecentActivity(activities.slice(0, 10));

        } catch (err: any) {
            console.error('Failed to load dashboard data:', {
                error: err,
                message: err?.message || 'Unknown error',
                status: err?.status,
                details: err?.details
            });
        } finally {
            setLoadingData(false);
        }
    };

    const getActivityIcon = (type: string) => {
        switch (type) {
            case 'design':
                return (
                    <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                );
            case 'review':
                return (
                    <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                );
            default:
                return (
                    <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                );
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return null;
    }

    return (
        <div className="container mx-auto px-4 py-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
                <p className="text-gray-600 mt-2">
                    Welcome back, {user?.first_name || user?.username}!
                </p>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <Link
                    href="/series"
                    className="flex items-center p-4 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg transition-colors group"
                >
                    <div className="flex-shrink-0 w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center group-hover:bg-blue-700 transition-colors">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                    </div>
                    <div className="ml-4">
                        <h3 className="font-semibold text-gray-900">New Part Number</h3>
                        <p className="text-sm text-gray-600">Create design series</p>
                    </div>
                </Link>

                <Link
                    href="/series"
                    className="flex items-center p-4 bg-green-50 hover:bg-green-100 border border-green-200 rounded-lg transition-colors group"
                >
                    <div className="flex-shrink-0 w-12 h-12 bg-green-600 rounded-lg flex items-center justify-center group-hover:bg-green-700 transition-colors">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                    </div>
                    <div className="ml-4">
                        <h3 className="font-semibold text-gray-900">Upload Design</h3>
                        <p className="text-sm text-gray-600">Add new version</p>
                    </div>
                </Link>

                <Link
                    href="/reviews/create"
                    className="flex items-center p-4 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-lg transition-colors group"
                >
                    <div className="flex-shrink-0 w-12 h-12 bg-purple-600 rounded-lg flex items-center justify-center group-hover:bg-purple-700 transition-colors">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                        </svg>
                    </div>
                    <div className="ml-4">
                        <h3 className="font-semibold text-gray-900">Start Review</h3>
                        <p className="text-sm text-gray-600">Create review session</p>
                    </div>
                </Link>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
                <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-gray-600 text-sm font-medium">Total Designs</h3>
                            <p className="text-3xl font-bold text-gray-900 mt-2">
                                {loadingData ? '-' : stats.totalDesigns}
                            </p>
                        </div>
                        <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                    </div>
                    <p className="text-gray-500 text-sm mt-2">All design assets</p>
                </div>

                <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-gray-600 text-sm font-medium">Part Numbers</h3>
                            <p className="text-3xl font-bold text-gray-900 mt-2">
                                {loadingData ? '-' : stats.totalSeries}
                            </p>
                        </div>
                        <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                            <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                            </svg>
                        </div>
                    </div>
                    <p className="text-gray-500 text-sm mt-2">Active series</p>
                </div>

                <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-gray-600 text-sm font-medium">Active Reviews</h3>
                            <p className="text-3xl font-bold text-gray-900 mt-2">
                                {loadingData ? '-' : stats.activeReviews}
                            </p>
                        </div>
                        <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                            <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                    </div>
                    <p className="text-gray-500 text-sm mt-2">Pending completion</p>
                </div>

                <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-gray-600 text-sm font-medium">Completed</h3>
                            <p className="text-3xl font-bold text-gray-900 mt-2">
                                {loadingData ? '-' : stats.completedReviews}
                            </p>
                        </div>
                        <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                            <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                    </div>
                    <p className="text-gray-500 text-sm mt-2">Reviews done</p>
                </div>

                <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-gray-600 text-sm font-medium">Recent Uploads</h3>
                            <p className="text-3xl font-bold text-gray-900 mt-2">
                                {loadingData ? '-' : stats.recentUploads}
                            </p>
                        </div>
                        <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                            <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                        </div>
                    </div>
                    <p className="text-gray-500 text-sm mt-2">Last 7 days</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Recent Activity */}
                <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Activity</h2>
                    {loadingData ? (
                        <div className="flex justify-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        </div>
                    ) : recentActivity.length === 0 ? (
                        <p className="text-gray-500 py-8 text-center">No recent activity to display.</p>
                    ) : (
                        <div className="space-y-4">
                            {recentActivity.map((activity) => (
                                <Link
                                    key={activity.id}
                                    href={activity.link || '#'}
                                    className="flex items-start p-3 hover:bg-gray-50 rounded-lg transition-colors"
                                >
                                    <div className="flex-shrink-0 w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                                        {getActivityIcon(activity.type)}
                                    </div>
                                    <div className="ml-3 flex-1 min-w-0">
                                        <p className="text-sm font-medium text-gray-900 truncate">{activity.title}</p>
                                        <p className="text-sm text-gray-600 truncate">{activity.description}</p>
                                        <p className="text-xs text-gray-500 mt-1">
                                            {new Date(activity.timestamp).toLocaleString()}
                                        </p>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    )}
                </div>

                {/* Recent Designs */}
                <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-xl font-bold text-gray-900">Recent Designs</h2>
                        <Link href="/series" className="text-blue-600 hover:text-blue-700 transition-colors">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                            </svg>
                        </Link>
                    </div>
                    {loadingData ? (
                        <div className="flex justify-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        </div>
                    ) : recentDesigns.length === 0 ? (
                        <p className="text-gray-500 py-8 text-center">No designs uploaded yet.</p>
                    ) : (
                        <div className="space-y-3">
                            {recentDesigns.map((design) => (
                                <Link
                                    key={design.id}
                                    href={`/designs/${design.id}`}
                                    className="block p-3 hover:bg-gray-50 rounded-lg transition-colors border border-gray-100"
                                >
                                    <div className="flex items-center justify-between">
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-gray-900 truncate">
                                                {design.file_name || design.id}
                                            </p>
                                            <p className="text-xs text-gray-600 mt-1">
                                                Version {design.version_label || design.version_number}
                                            </p>
                                        </div>
                                        <span className={`ml-3 px-2 py-1 text-xs font-medium rounded-full ${design.status === 'READY' ? 'bg-green-100 text-green-800' :
                                            design.status === 'PROCESSING' ? 'bg-blue-100 text-blue-800' :
                                                'bg-gray-100 text-gray-800'
                                            }`}>
                                            {design.status}
                                        </span>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

