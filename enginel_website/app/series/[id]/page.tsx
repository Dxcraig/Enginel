'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useParams } from 'next/navigation';
import ApiClient from '@/lib/api/client';
import { DesignSeries, DesignAsset } from '@/types';
import Link from 'next/link';

export default function SeriesDetailPage() {
    const { user, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const params = useParams();
    const seriesId = params.id as string;

    const [series, setSeries] = useState<DesignSeries | null>(null);
    const [assets, setAssets] = useState<DesignAsset[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (user && seriesId) {
            loadSeriesDetail();
        }
    }, [user, seriesId]);

    const loadSeriesDetail = async () => {
        try {
            setLoading(true);
            const [seriesData, assetsData] = await Promise.all([
                ApiClient.get<DesignSeries>(`/series/${seriesId}/`),
                ApiClient.get<{ results: DesignAsset[] }>(`/designs/?series=${seriesId}`),
            ]);
            setSeries(seriesData);
            setAssets(assetsData.results);
            setError('');
        } catch (err: any) {
            setError(err.message || 'Failed to load series details');
        } finally {
            setLoading(false);
        }
    };

    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
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

    if (error || !series) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                    {error || 'Series not found'}
                </div>
                <Link href="/series" className="mt-4 inline-block text-gray-600 hover:text-gray-900">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                </Link>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8">
            {/* Header */}
            <div className="mb-6">
                <Link href="/series" className="text-gray-600 hover:text-gray-900 mb-2 inline-block">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                </Link>
                <div className="flex justify-between items-start">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">{series.part_number}</h1>
                        <p className="text-gray-600 mt-2">{series.description}</p>
                    </div>
                    <Link
                        href={`/series/${seriesId}/upload`}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
                    >
                        + Upload Version
                    </Link>
                </div>
            </div>

            {/* Metadata Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-white p-4 rounded-lg shadow">
                    <div className="text-sm text-gray-500 mb-1">Classification</div>
                    <div className={`font-semibold ${series.classification_level === 'Top Secret' ? 'text-red-600' :
                        series.classification_level === 'Secret' ? 'text-orange-600' :
                            series.classification_level === 'Confidential' ? 'text-yellow-600' :
                                'text-green-600'
                        }`}>
                        {series.classification_level}
                    </div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                    <div className="text-sm text-gray-500 mb-1">Status</div>
                    <div className="font-semibold text-gray-900">{series.lifecycle_state}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                    <div className="text-sm text-gray-500 mb-1">Current Version</div>
                    <div className="font-semibold text-gray-900">{series.current_version || 'N/A'}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                    <div className="text-sm text-gray-500 mb-1">Total Versions</div>
                    <div className="font-semibold text-gray-900">{assets.length}</div>
                </div>
            </div>

            {/* Version History */}
            <div className="bg-white shadow-md rounded-lg overflow-hidden">
                <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
                    <h2 className="text-xl font-semibold text-gray-900">Version History</h2>
                </div>
                {assets.length === 0 ? (
                    <div className="px-6 py-12 text-center text-gray-500">
                        No versions uploaded yet. Click "Upload Version" to add your first design file.
                    </div>
                ) : (
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Version
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    File Name
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Type
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Size
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Uploaded
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Status
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Actions
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {assets.map((asset) => (
                                <tr key={asset.id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                                        {asset.version_label}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="text-sm text-gray-900">{asset.file_name}</div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {asset.file_type}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {formatFileSize(asset.file_size || 0)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {new Date(asset.created_at).toLocaleDateString()}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${asset.processing_status === 'completed' ? 'bg-green-100 text-green-800' :
                                            asset.processing_status === 'failed' ? 'bg-red-100 text-red-800' :
                                                'bg-yellow-100 text-yellow-800'
                                            }`}>
                                            {asset.processing_status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                        <Link
                                            href={`/viewer?design=${asset.id}`}
                                            className="text-purple-600 hover:text-purple-900 mr-3"
                                            title="Preview file"
                                        >
                                            Preview
                                        </Link>
                                        <Link
                                            href={`/designs/${asset.id}`}
                                            className="text-blue-600 hover:text-blue-900 mr-3"
                                        >
                                            View
                                        </Link>
                                        {asset.file_url && (
                                            <a
                                                href={asset.file_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-green-600 hover:text-green-900"
                                            >
                                                Download
                                            </a>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
