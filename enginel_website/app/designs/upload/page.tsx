'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

interface DesignSeries {
    id: string;
    part_number: string;
    name: string;
    description: string;
    version_count: number;
    latest_version_number: number;
}

interface UploadFormData {
    series_id: string;
    new_part_number: string;
    new_series_name: string;
    new_series_description: string;
    classification: string;
    revision: string;
    notes: string;
    file: File | null;
}

const CLASSIFICATION_OPTIONS = [
    { value: 'UNCLASSIFIED', label: 'Unclassified', description: 'Public information' },
    { value: 'CUI', label: 'CUI', description: 'Controlled Unclassified Information' },
    { value: 'EAR99', label: 'EAR99', description: 'Export Administration Regulations' },
    { value: 'ITAR', label: 'ITAR', description: 'International Traffic in Arms Regulations' },
];

const ACCEPTED_FILE_TYPES = [
    '.step', '.stp', '.iges', '.igs', '.stl', '.obj',
    '.prt', '.asm', '.sldprt', '.sldasm', '.catpart', '.catproduct'
];

export default function DesignUploadPage() {
    const router = useRouter();
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [seriesList, setSeriesList] = useState<DesignSeries[]>([]);
    const [loading, setLoading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [dragActive, setDragActive] = useState(false);
    const [isNewSeries, setIsNewSeries] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const [formData, setFormData] = useState<UploadFormData>({
        series_id: '',
        new_part_number: '',
        new_series_name: '',
        new_series_description: '',
        classification: 'UNCLASSIFIED',
        revision: '',
        notes: '',
        file: null,
    });

    useEffect(() => {
        fetchSeries();
    }, []);

    const fetchSeries = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch('http://localhost:8000/api/series/', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (response.ok) {
                const data = await response.json();
                setSeriesList(data.results || data);
            }
        } catch (err) {
            console.error('Error fetching series:', err);
        }
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    };

    const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            handleFileSelect(e.target.files[0]);
        }
    };

    const handleFileSelect = (file: File) => {
        const fileName = file.name.toLowerCase();
        const fileExt = '.' + fileName.split('.').pop();

        if (!ACCEPTED_FILE_TYPES.includes(fileExt)) {
            setError(`Invalid file type. Please upload a CAD file (${ACCEPTED_FILE_TYPES.join(', ')})`);
            return;
        }

        // Check file size (100MB limit)
        const maxSize = 100 * 1024 * 1024; // 100MB
        if (file.size > maxSize) {
            setError('File size exceeds 100MB limit');
            return;
        }

        setFormData(prev => ({ ...prev, file }));
        setError('');
    };

    const validateForm = (): boolean => {
        if (!formData.file) {
            setError('Please select a file to upload');
            return false;
        }

        if (isNewSeries) {
            if (!formData.new_part_number.trim()) {
                setError('Please enter a part number');
                return false;
            }
            if (!formData.new_series_name.trim()) {
                setError('Please enter a series name');
                return false;
            }

            // Validate part number format (alphanumeric with hyphens)
            const partNumberRegex = /^[A-Z0-9\-]+$/;
            if (!partNumberRegex.test(formData.new_part_number)) {
                setError('Part number must contain only uppercase letters, numbers, and hyphens');
                return false;
            }
        } else {
            if (!formData.series_id) {
                setError('Please select a part number or create a new one');
                return false;
            }
        }

        return true;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!validateForm()) {
            return;
        }

        setLoading(true);
        setError('');
        setSuccess('');
        setUploadProgress(0);

        try {
            const token = localStorage.getItem('token');

            // Step 1: Create or select series
            let seriesId = formData.series_id;

            if (isNewSeries) {
                // Create new series
                const seriesResponse = await fetch('http://localhost:8000/api/series/', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        part_number: formData.new_part_number,
                        name: formData.new_series_name,
                        description: formData.new_series_description,
                    }),
                });

                if (!seriesResponse.ok) {
                    const errorData = await seriesResponse.json();
                    throw new Error(errorData.detail || errorData.part_number?.[0] || 'Failed to create series');
                }

                const seriesData = await seriesResponse.json();
                seriesId = seriesData.id;
                setUploadProgress(30);
            } else {
                setUploadProgress(20);
            }

            // Step 2: Upload design asset with file
            const uploadFormData = new FormData();
            uploadFormData.append('series', seriesId);
            uploadFormData.append('file', formData.file!);
            uploadFormData.append('classification', formData.classification);

            if (formData.revision) {
                uploadFormData.append('revision', formData.revision);
            }
            if (formData.notes) {
                uploadFormData.append('notes', formData.notes);
            }

            setUploadProgress(40);

            const uploadResponse = await fetch('http://localhost:8000/api/designs/', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
                body: uploadFormData,
            });

            if (!uploadResponse.ok) {
                const errorData = await uploadResponse.json();
                throw new Error(errorData.detail || 'Upload failed');
            }

            const uploadData = await uploadResponse.json();
            setUploadProgress(100);

            setSuccess('Design uploaded successfully! Processing geometry...');

            // Reset form
            setTimeout(() => {
                router.push(`/designs/${uploadData.id}`);
            }, 2000);

        } catch (err) {
            console.error('Upload error:', err);
            setError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
            setUploadProgress(0);
        } finally {
            setLoading(false);
        }
    };

    const removeFile = () => {
        setFormData(prev => ({ ...prev, file: null }));
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const formatFileSize = (bytes: number): string => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    };

    return (
        <div className="min-h-screen bg-gray-50 py-8 px-4">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center gap-4 mb-4">
                        <Link
                            href="/designs"
                            className="text-gray-600 hover:text-gray-900 transition-colors"
                        >
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                            </svg>
                        </Link>
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900">Upload Design</h1>
                            <p className="text-gray-600 mt-1">Upload a new CAD file to Enginel</p>
                        </div>
                    </div>
                </div>

                {/* Alert Messages */}
                {error && (
                    <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-start gap-3">
                        <svg className="w-5 h-5 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                        <span>{error}</span>
                    </div>
                )}

                {success && (
                    <div className="mb-6 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-start gap-3">
                        <svg className="w-5 h-5 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        <span>{success}</span>
                    </div>
                )}

                {/* Upload Form */}
                <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm border border-gray-200">
                    {/* File Upload Area */}
                    <div className="p-6 border-b border-gray-200">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">Select File</h2>

                        {!formData.file ? (
                            <div
                                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${dragActive
                                        ? 'border-blue-500 bg-blue-50'
                                        : 'border-gray-300 hover:border-gray-400'
                                    }`}
                                onDragEnter={handleDrag}
                                onDragLeave={handleDrag}
                                onDragOver={handleDrag}
                                onDrop={handleDrop}
                            >
                                <svg
                                    className="mx-auto h-12 w-12 text-gray-400"
                                    stroke="currentColor"
                                    fill="none"
                                    viewBox="0 0 48 48"
                                >
                                    <path
                                        d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                                        strokeWidth={2}
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                    />
                                </svg>
                                <div className="mt-4">
                                    <button
                                        type="button"
                                        onClick={() => fileInputRef.current?.click()}
                                        className="text-blue-600 hover:text-blue-700 font-medium"
                                    >
                                        Click to upload
                                    </button>
                                    <span className="text-gray-600"> or drag and drop</span>
                                </div>
                                <p className="text-sm text-gray-500 mt-2">
                                    CAD files: STEP, IGES, STL, OBJ, SolidWorks, CATIA (max 100MB)
                                </p>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    className="hidden"
                                    accept={ACCEPTED_FILE_TYPES.join(',')}
                                    onChange={handleFileInput}
                                />
                            </div>
                        ) : (
                            <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-start gap-3 flex-1">
                                        <div className="p-2 bg-blue-100 rounded">
                                            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                            </svg>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-gray-900 truncate">
                                                {formData.file.name}
                                            </p>
                                            <p className="text-sm text-gray-500">
                                                {formatFileSize(formData.file.size)}
                                            </p>
                                            {uploadProgress > 0 && (
                                                <div className="mt-2">
                                                    <div className="w-full bg-gray-200 rounded-full h-2">
                                                        <div
                                                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                                            style={{ width: `${uploadProgress}%` }}
                                                        />
                                                    </div>
                                                    <p className="text-xs text-gray-500 mt-1">{uploadProgress}%</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={removeFile}
                                        disabled={loading}
                                        className="ml-4 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                                    >
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Part Number Selection */}
                    <div className="p-6 border-b border-gray-200">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">Part Number</h2>

                        <div className="flex gap-4 mb-4">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="radio"
                                    name="seriesOption"
                                    checked={!isNewSeries}
                                    onChange={() => setIsNewSeries(false)}
                                    className="w-4 h-4 text-blue-600"
                                />
                                <span className="text-sm font-medium text-gray-700">Existing Part Number</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="radio"
                                    name="seriesOption"
                                    checked={isNewSeries}
                                    onChange={() => setIsNewSeries(true)}
                                    className="w-4 h-4 text-blue-600"
                                />
                                <span className="text-sm font-medium text-gray-700">New Part Number</span>
                            </label>
                        </div>

                        {!isNewSeries ? (
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Select Part Number
                                </label>
                                <select
                                    value={formData.series_id}
                                    onChange={(e) => setFormData(prev => ({ ...prev, series_id: e.target.value }))}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    required={!isNewSeries}
                                >
                                    <option value="">Select a part number...</option>
                                    {seriesList.map(series => (
                                        <option key={series.id} value={series.id}>
                                            {series.part_number} - {series.name} (v{series.latest_version_number})
                                        </option>
                                    ))}
                                </select>
                                <p className="text-xs text-gray-500 mt-1">
                                    This will create version {seriesList.find(s => s.id === formData.series_id)?.latest_version_number ? (seriesList.find(s => s.id === formData.series_id)!.latest_version_number + 1) : 1}
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Part Number <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.new_part_number}
                                        onChange={(e) => setFormData(prev => ({ ...prev, new_part_number: e.target.value.toUpperCase() }))}
                                        placeholder="PN-2024-001"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        required={isNewSeries}
                                    />
                                    <p className="text-xs text-gray-500 mt-1">Use uppercase letters, numbers, and hyphens</p>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Series Name <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.new_series_name}
                                        onChange={(e) => setFormData(prev => ({ ...prev, new_series_name: e.target.value }))}
                                        placeholder="Mounting Bracket"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        required={isNewSeries}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Description (Optional)
                                    </label>
                                    <textarea
                                        value={formData.new_series_description}
                                        onChange={(e) => setFormData(prev => ({ ...prev, new_series_description: e.target.value }))}
                                        placeholder="Brief description of this part series..."
                                        rows={3}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    />
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Classification & Metadata */}
                    <div className="p-6 border-b border-gray-200">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">Classification & Details</h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Export Classification <span className="text-red-500">*</span>
                                </label>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {CLASSIFICATION_OPTIONS.map(option => (
                                        <label
                                            key={option.value}
                                            className={`relative flex items-start p-4 border-2 rounded-lg cursor-pointer transition-all ${formData.classification === option.value
                                                    ? 'border-blue-500 bg-blue-50'
                                                    : 'border-gray-200 hover:border-gray-300'
                                                }`}
                                        >
                                            <input
                                                type="radio"
                                                name="classification"
                                                value={option.value}
                                                checked={formData.classification === option.value}
                                                onChange={(e) => setFormData(prev => ({ ...prev, classification: e.target.value }))}
                                                className="mt-1 w-4 h-4 text-blue-600"
                                            />
                                            <div className="ml-3">
                                                <div className="text-sm font-semibold text-gray-900">{option.label}</div>
                                                <div className="text-xs text-gray-500 mt-1">{option.description}</div>
                                            </div>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Revision (Optional)
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.revision}
                                        onChange={(e) => setFormData(prev => ({ ...prev, revision: e.target.value }))}
                                        placeholder="A, B, C, or Rev 1, Rev 2..."
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Notes (Optional)
                                </label>
                                <textarea
                                    value={formData.notes}
                                    onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                                    placeholder="Additional notes about this design version..."
                                    rows={4}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Submit Buttons */}
                    <div className="p-6 bg-gray-50 flex items-center justify-between">
                        <Link
                            href="/designs"
                            className="text-gray-600 hover:text-gray-900 font-medium transition-colors"
                        >
                            Cancel
                        </Link>
                        <button
                            type="submit"
                            disabled={loading || !formData.file}
                            className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {loading ? (
                                <span className="flex items-center gap-2">
                                    <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    Uploading...
                                </span>
                            ) : (
                                'Upload Design'
                            )}
                        </button>
                    </div>
                </form>

                {/* Help Section */}
                <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-blue-900 mb-2">Supported File Formats</h3>
                    <div className="text-sm text-blue-800 space-y-1">
                        <p>• <strong>STEP/STP:</strong> Recommended for maximum compatibility</p>
                        <p>• <strong>IGES/IGS:</strong> Legacy CAD interchange format</p>
                        <p>• <strong>STL:</strong> 3D mesh format (no parametric data)</p>
                        <p>• <strong>Native CAD:</strong> SolidWorks (.sldprt, .sldasm), CATIA (.catpart, .catproduct)</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
