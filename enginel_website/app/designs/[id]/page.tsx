'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useParams } from 'next/navigation';
import ApiClient from '@/lib/api/client';
import { DesignAsset, AssemblyNode, ValidationResult } from '@/types';
import BOMTree from '@/components/BOMTree';
import Link from 'next/link';
import FilePreview from '@/components/FilePreview';

export default function DesignDetailPage() {
    const { user, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const params = useParams();
    const designId = params.id as string;

    const [design, setDesign] = useState<DesignAsset | null>(null);
    const [bomNodes, setBomNodes] = useState<AssemblyNode[]>([]);
    const [validationResults, setValidationResults] = useState<ValidationResult[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState<'preview' | 'details' | 'bom' | 'validation'>('preview');
    const [fileUrl, setFileUrl] = useState<string | undefined>(undefined);

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (user && designId) {
            loadDesignDetail();
        }
    }, [user, designId]);

    const loadDesignDetail = async () => {
        try {
            setLoading(true);
            const [designData, bomData] = await Promise.all([
                ApiClient.get<DesignAsset>(`/designs/${designId}/`),
                ApiClient.get<{ results: AssemblyNode[] }>(`/bom-nodes/?design=${designId}`),
            ]);
            setDesign(designData);
            setBomNodes(bomData.results);

            // Get download URL for preview
            if (designData.s3_key) {
                try {
                    const urlResponse = await ApiClient.get<{ download_url: string }>(
                        `/designs/${designId}/download-url/`
                    );
                    setFileUrl(urlResponse.download_url);
                } catch (urlErr) {
                    console.error('Failed to get download URL:', urlErr);
                }
            }

            // Load validation results
            try {
                const validationData = await ApiClient.get<{ results: ValidationResult[] }>(
                    `/validation/results/?target_model=DesignAsset&target_id=${designId}`
                );
                setValidationResults(validationData.results || []);
            } catch (validationErr) {
                console.error('Failed to load validation results:', validationErr);
            }

            setError('');
        } catch (err: any) {
            setError(err.message || 'Failed to load design details');
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

    if (error || !design) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                    {error || 'Design not found'}
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
                <Link
                    href={`/series/${typeof design.series === 'string' ? design.series : design.series.id}`}
                    className="text-gray-600 hover:text-gray-900 mb-2 inline-block"
                >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                </Link>
                <div className="flex justify-between items-start">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">{design.file_name}</h1>
                        <p className="text-gray-600 mt-1">Version: {design.version_label}</p>
                    </div>
                    <div className="flex space-x-2">
                        <Link
                            href={`/viewer?design=${design.id}`}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                            <span>Full Screen</span>
                        </Link>
                        {design.file_url && (
                            <a
                                href={design.file_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                                <span>Download</span>
                            </a>
                        )}
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-200 mb-6">
                <nav className="flex space-x-8">
                    <button
                        onClick={() => setActiveTab('preview')}
                        className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'preview'
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                    >
                        Preview
                    </button>
                    <button
                        onClick={() => setActiveTab('details')}
                        className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'details'
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                    >
                        Details
                    </button>
                    <button
                        onClick={() => setActiveTab('bom')}
                        className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'bom'
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                    >
                        Bill of Materials
                        {bomNodes.length > 0 && (
                            <span className="ml-2 bg-gray-200 text-gray-700 px-2 py-0.5 rounded-full text-xs">
                                {bomNodes.length}
                            </span>
                        )}
                    </button>
                    <button
                        onClick={() => setActiveTab('validation')}
                        className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'validation'
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                    >
                        Validation Results
                    </button>
                </nav>
            </div>

            {/* Tab Content */}
            {activeTab === 'preview' && (
                <div className="bg-gray-900 rounded-lg overflow-hidden" style={{ height: '600px' }}>
                    <FilePreview
                        fileUrl={fileUrl}
                        fileName={design.file_name}
                        fileType={design.file_type}
                        fileSize={design.file_size}
                    />
                </div>
            )}

            {activeTab === 'details' && (
                <div className="bg-white shadow-md rounded-lg p-6">
                    <h2 className="text-xl font-semibold mb-4">Design Information</h2>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <div className="text-sm text-gray-500 mb-1">File Name</div>
                            <div className="font-medium">{design.file_name}</div>
                        </div>
                        <div>
                            <div className="text-sm text-gray-500 mb-1">File Type</div>
                            <div className="font-medium">{design.file_type}</div>
                        </div>
                        <div>
                            <div className="text-sm text-gray-500 mb-1">File Size</div>
                            <div className="font-medium">{formatFileSize(design.file_size || 0)}</div>
                        </div>
                        <div>
                            <div className="text-sm text-gray-500 mb-1">Processing Status</div>
                            <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${design.processing_status === 'completed' ? 'bg-green-100 text-green-800' :
                                design.processing_status === 'failed' ? 'bg-red-100 text-red-800' :
                                    'bg-yellow-100 text-yellow-800'
                                }`}>
                                {design.processing_status}
                            </span>
                        </div>
                        <div>
                            <div className="text-sm text-gray-500 mb-1">Created At</div>
                            <div className="font-medium">{new Date(design.created_at).toLocaleString()}</div>
                        </div>
                        <div>
                            <div className="text-sm text-gray-500 mb-1">Updated At</div>
                            <div className="font-medium">{new Date(design.updated_at).toLocaleString()}</div>
                        </div>
                    </div>

                    {design.change_description && (
                        <div className="mt-6">
                            <div className="text-sm text-gray-500 mb-2">Change Description</div>
                            <div className="p-4 bg-gray-50 rounded-lg">{design.change_description}</div>
                        </div>
                    )}

                    {design.processing_error && (
                        <div className="mt-6">
                            <div className="text-sm text-red-500 mb-2">Processing Error</div>
                            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                                {design.processing_error}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {activeTab === 'bom' && (
                <div>
                    <div className="mb-4 flex justify-between items-center">
                        <h2 className="text-xl font-semibold">Assembly Structure</h2>
                        <div className="text-sm text-gray-500">
                            Total Components: {bomNodes.length}
                        </div>
                    </div>
                    <BOMTree nodes={bomNodes} />
                </div>
            )}

            {activeTab === 'validation' && (
                <div className="bg-white shadow-md rounded-lg overflow-hidden">
                    <div className="px-6 py-4 bg-gray-50 border-b border-gray-200 flex justify-between items-center">
                        <h2 className="text-xl font-semibold text-gray-900">Validation Results</h2>
                        <div className="text-sm text-gray-500">
                            {validationResults.length} result{validationResults.length !== 1 ? 's' : ''}
                        </div>
                    </div>
                    {validationResults.length === 0 ? (
                        <div className="px-6 py-12 text-center text-gray-500">
                            <svg className="w-12 h-12 text-gray-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <p>No validation results yet</p>
                            <p className="text-sm mt-1">Validation rules will be applied when configured</p>
                        </div>
                    ) : (
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rule</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Field</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Message</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validated</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {validationResults.map((result) => (
                                    <tr key={result.id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs font-semibold rounded-full ${result.status === 'PASSED' ? 'bg-green-100 text-green-800' :
                                                    result.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                                                        result.status === 'SKIPPED' ? 'bg-gray-100 text-gray-800' :
                                                            'bg-orange-100 text-orange-800'
                                                }`}>
                                                {result.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="text-sm text-gray-900">
                                                {typeof result.rule === 'string' ? result.rule : result.rule.name}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-gray-500">
                                            {result.target_field || '-'}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="text-sm text-gray-700">{result.error_message || '-'}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {new Date(result.validated_at).toLocaleDateString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}
        </div>
    );
}
