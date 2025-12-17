'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import FilePreview from '@/components/FilePreview';
import ApiClient from '@/lib/api/client';
import { DesignAsset } from '@/types';

export default function ViewerPage() {
    const { user, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();

    const designId = searchParams.get('design');
    const [design, setDesign] = useState<DesignAsset | null>(null);
    const [fileUrl, setFileUrl] = useState<string | undefined>(undefined);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [downloading, setDownloading] = useState(false);

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (user && designId) {
            loadDesign();
        }
    }, [user, designId]);

    const loadDesign = async () => {
        if (!designId) {
            setError('No design ID provided');
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            const designData = await ApiClient.get<DesignAsset>(`/designs/${designId}/`);
            setDesign(designData);

            // Get download URL
            if (designData.s3_key) {
                const urlResponse = await ApiClient.get<{ download_url: string }>(
                    `/designs/${designId}/download-url/`
                );
                setFileUrl(urlResponse.download_url);
            }

            setError('');
        } catch (err: any) {
            setError(err.message || 'Failed to load design');
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = async () => {
        if (!design || !fileUrl) return;

        try {
            setDownloading(true);
            const response = await fetch(fileUrl);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = design.file_name || design.filename || 'download';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (err) {
            console.error('Download failed:', err);
        } finally {
            setDownloading(false);
        }
    };

    const handleClose = () => {
        if (design) {
            const seriesId = typeof design.series === 'string' ? design.series : design.series.id;
            router.push(`/designs/${design.id}`);
        } else {
            router.back();
        }
    };

    if (authLoading || !user) {
        return null;
    }

    if (loading) {
        return (
            <div className="fixed inset-0 bg-gray-900 flex items-center justify-center z-50">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
                    <p className="text-white text-lg">Loading viewer...</p>
                </div>
            </div>
        );
    }

    if (error || !design) {
        return (
            <div className="fixed inset-0 bg-gray-900 flex items-center justify-center z-50">
                <div className="text-center max-w-md px-4">
                    <svg className="w-16 h-16 text-red-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h2 className="text-xl font-semibold text-white mb-2">Error</h2>
                    <p className="text-gray-400 mb-6">{error || 'Design not found'}</p>
                    <button
                        onClick={() => router.back()}
                        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        Go Back
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 bg-gray-900 z-50">
            {/* Header */}
            <div className="absolute top-0 left-0 right-0 bg-gradient-to-b from-black/50 to-transparent z-10 p-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <button
                            onClick={handleClose}
                            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                            title="Close viewer"
                        >
                            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                        <div className="text-white">
                            <h1 className="text-lg font-semibold">{design.file_name}</h1>
                            <p className="text-sm text-gray-300">
                                Version {design.version_label}
                                {typeof design.series !== 'string' && ` • ${design.series.part_number}`}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center space-x-2">
                        <button
                            onClick={handleDownload}
                            disabled={downloading || !fileUrl}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg transition-colors flex items-center space-x-2"
                        >
                            {downloading ? (
                                <>
                                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    <span>Downloading...</span>
                                </>
                            ) : (
                                <>
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                    </svg>
                                    <span>Download</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>

            {/* File Preview */}
            <div className="w-full h-full">
                <FilePreview
                    fileUrl={fileUrl}
                    fileName={design.file_name}
                    fileType={design.file_type}
                    fileSize={design.file_size}
                />
            </div>

            {/* Info Panel (Optional) */}
            <div className="absolute top-20 right-4 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-4 max-w-xs z-10">
                <h3 className="font-semibold text-gray-900 mb-3">File Information</h3>
                <div className="space-y-2 text-sm">
                    <div>
                        <span className="text-gray-500">Type:</span>
                        <span className="ml-2 text-gray-900">{design.file_type}</span>
                    </div>
                    <div>
                        <span className="text-gray-500">Size:</span>
                        <span className="ml-2 text-gray-900">
                            {design.file_size ? `${(design.file_size / 1024 / 1024).toFixed(2)} MB` : 'N/A'}
                        </span>
                    </div>
                    <div>
                        <span className="text-gray-500">Uploaded:</span>
                        <span className="ml-2 text-gray-900">
                            {new Date(design.created_at).toLocaleDateString()}
                        </span>
                    </div>
                    <div>
                        <span className="text-gray-500">Status:</span>
                        <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${design.processing_status === 'completed' ? 'bg-green-100 text-green-800' :
                                design.processing_status === 'failed' ? 'bg-red-100 text-red-800' :
                                    'bg-yellow-100 text-yellow-800'
                            }`}>
                            {design.processing_status}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
