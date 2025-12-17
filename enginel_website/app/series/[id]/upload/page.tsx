'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useParams } from 'next/navigation';
import ApiClient from '@/lib/api/client';
import { DesignSeries } from '@/types';
import Link from 'next/link';

export default function UploadPage() {
    const { user, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const params = useParams();
    const seriesId = params.id as string;

    const [series, setSeries] = useState<DesignSeries | null>(null);
    const [file, setFile] = useState<File | null>(null);
    const [formData, setFormData] = useState({
        version_label: '',
        change_description: '',
        is_major_version: false,
    });
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (user && seriesId) {
            loadSeries();
        }
    }, [user, seriesId]);

    const loadSeries = async () => {
        try {
            const data = await ApiClient.get<DesignSeries>(`/series/${seriesId}/`);
            setSeries(data);
            // Auto-generate next version
            const nextVersion = data.current_version
                ? `v${parseInt(data.current_version.substring(1)) + 1}`
                : 'v1';
            setFormData(prev => ({ ...prev, version_label: nextVersion }));
        } catch (err: any) {
            setError(err.message || 'Failed to load series');
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setError('');
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!file) {
            setError('Please select a file to upload');
            return;
        }

        try {
            setUploading(true);
            setError('');
            setUploadProgress(0);

            // Upload file using multipart form data
            const uploadData = new FormData();
            uploadData.append('file', file);
            uploadData.append('series', seriesId);
            uploadData.append('version_label', formData.version_label);
            uploadData.append('change_description', formData.change_description);
            uploadData.append('is_major_version', String(formData.is_major_version));

            await ApiClient.upload('/designs/', uploadData, (progress) => {
                setUploadProgress(progress);
            });

            setSuccess(true);
            setTimeout(() => {
                router.push(`/series/${seriesId}`);
            }, 2000);
        } catch (err: any) {
            setError(err.message || 'Upload failed');
            setUploading(false);
        }
    };

    if (authLoading || !user) {
        return null;
    }

    if (!series) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="flex justify-center items-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8 max-w-2xl">
            <Link
                href={`/series/${seriesId}`}
                className="text-gray-600 hover:text-gray-900 mb-4 inline-block"
            >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
            </Link>

            <div className="bg-white shadow-md rounded-lg p-6">
                <h1 className="text-2xl font-bold mb-2">Upload New Version</h1>
                <p className="text-gray-600 mb-6">
                    Upload a new design file for {series.part_number}
                </p>

                {error && (
                    <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                        {error}
                    </div>
                )}

                {success && (
                    <div className="mb-4 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg">
                        Upload successful! Redirecting...
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    {/* File Upload */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Design File *
                        </label>
                        <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-lg hover:border-blue-400 transition-colors">
                            <div className="space-y-1 text-center">
                                <svg
                                    className="mx-auto h-12 w-12 text-gray-400"
                                    stroke="currentColor"
                                    fill="none"
                                    viewBox="0 0 48 48"
                                    aria-hidden="true"
                                >
                                    <path
                                        d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                                        strokeWidth={2}
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                    />
                                </svg>
                                <div className="flex text-sm text-gray-600">
                                    <label
                                        htmlFor="file-upload"
                                        className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none"
                                    >
                                        <span>Upload a file</span>
                                        <input
                                            id="file-upload"
                                            name="file-upload"
                                            type="file"
                                            className="sr-only"
                                            onChange={handleFileChange}
                                            accept=".step,.stp,.iges,.igs,.stl,.obj,.fbx,.dxf,.dwg"
                                        />
                                    </label>
                                    <p className="pl-1">or drag and drop</p>
                                </div>
                                <p className="text-xs text-gray-500">
                                    STEP, IGES, STL, OBJ, FBX, DXF, DWG up to 500MB
                                </p>
                            </div>
                        </div>
                        {file && (
                            <div className="mt-2 text-sm text-gray-600">
                                Selected: <span className="font-medium">{file.name}</span> ({(file.size / 1024 / 1024).toFixed(2)} MB)
                            </div>
                        )}
                    </div>

                    {/* Version Label */}
                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Version Label *
                        </label>
                        <input
                            type="text"
                            required
                            value={formData.version_label}
                            onChange={(e) => setFormData({ ...formData, version_label: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="e.g., v1, v2.1, Rev A"
                        />
                    </div>

                    {/* Change Description */}
                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Change Description *
                        </label>
                        <textarea
                            required
                            value={formData.change_description}
                            onChange={(e) => setFormData({ ...formData, change_description: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            rows={4}
                            placeholder="Describe what changed in this version..."
                        />
                    </div>

                    {/* Major Version Checkbox */}
                    <div className="mb-6">
                        <label className="flex items-center">
                            <input
                                type="checkbox"
                                checked={formData.is_major_version}
                                onChange={(e) => setFormData({ ...formData, is_major_version: e.target.checked })}
                                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            />
                            <span className="ml-2 text-sm text-gray-700">
                                This is a major version (significant changes)
                            </span>
                        </label>
                    </div>

                    {/* Upload Progress */}
                    {uploading && (
                        <div className="mb-4">
                            <div className="flex justify-between text-sm text-gray-600 mb-1">
                                <span>Uploading...</span>
                                <span>{uploadProgress}%</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                                <div
                                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                    style={{ width: `${uploadProgress}%` }}
                                />
                            </div>
                        </div>
                    )}

                    {/* Submit Buttons */}
                    <div className="flex justify-end space-x-3">
                        <Link
                            href={`/series/${seriesId}`}
                            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                        >
                            Cancel
                        </Link>
                        <button
                            type="submit"
                            disabled={uploading || !file}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {uploading ? 'Uploading...' : 'Upload'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
