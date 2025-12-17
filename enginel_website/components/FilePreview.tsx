'use client';

import { useState } from 'react';
import ModelViewer from './ModelViewer';

interface FilePreviewProps {
    fileUrl?: string;
    fileName?: string;
    fileType?: string;
    fileSize?: number;
    mimeType?: string;
}

// Supported file types
const SUPPORTED_3D_FORMATS = ['step', 'stp', 'stl', 'obj', 'gltf', 'glb', 'iges', 'igs'];
const SUPPORTED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp'];
const SUPPORTED_DOCUMENT_FORMATS = ['pdf', 'txt', 'md', 'json', 'xml'];

function getFileExtension(fileName: string): string {
    return fileName.split('.').pop()?.toLowerCase() || '';
}

function getPreviewType(fileName: string, mimeType?: string): 'model' | 'image' | 'document' | 'unsupported' {
    const ext = getFileExtension(fileName);

    if (SUPPORTED_3D_FORMATS.includes(ext)) {
        return 'model';
    }
    if (SUPPORTED_IMAGE_FORMATS.includes(ext)) {
        return 'image';
    }
    if (SUPPORTED_DOCUMENT_FORMATS.includes(ext)) {
        return 'document';
    }

    // Check by MIME type if extension didn't match
    if (mimeType) {
        if (mimeType.startsWith('image/')) return 'image';
        if (mimeType === 'application/pdf') return 'document';
        if (mimeType.startsWith('text/')) return 'document';
    }

    return 'unsupported';
}

function ImagePreview({ fileUrl, fileName }: { fileUrl: string; fileName: string }) {
    const [imageError, setImageError] = useState(false);
    const [imageLoading, setImageLoading] = useState(true);

    if (imageError) {
        return (
            <div className="flex items-center justify-center h-full bg-gray-100">
                <div className="text-center">
                    <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p className="text-gray-600">Failed to load image</p>
                </div>
            </div>
        );
    }

    return (
        <div className="relative w-full h-full bg-gray-900 flex items-center justify-center overflow-hidden">
            {imageLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                </div>
            )}
            <img
                src={fileUrl}
                alt={fileName}
                className="max-w-full max-h-full object-contain"
                onLoad={() => setImageLoading(false)}
                onError={() => {
                    setImageLoading(false);
                    setImageError(true);
                }}
            />
        </div>
    );
}

function DocumentPreview({ fileUrl, fileName }: { fileUrl: string; fileName: string }) {
    const ext = getFileExtension(fileName);

    if (ext === 'pdf') {
        return (
            <div className="w-full h-full">
                <iframe
                    src={fileUrl}
                    className="w-full h-full border-0"
                    title={fileName}
                />
            </div>
        );
    }

    // For text files, show in a text area (would need to fetch content)
    return (
        <div className="flex items-center justify-center h-full bg-gray-100">
            <div className="text-center">
                <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-gray-600 mb-4">Document preview not available</p>
                <a
                    href={fileUrl}
                    download={fileName}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-block"
                >
                    Download File
                </a>
            </div>
        </div>
    );
}

function UnsupportedPreview({ fileName, fileUrl }: { fileName: string; fileUrl?: string }) {
    return (
        <div className="flex items-center justify-center h-full bg-gray-100">
            <div className="text-center max-w-md px-4">
                <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Preview not available</h3>
                <p className="text-gray-600 mb-4">
                    Preview is not supported for this file type.
                </p>
                {fileUrl && (
                    <a
                        href={fileUrl}
                        download={fileName}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-block"
                    >
                        Download File
                    </a>
                )}
            </div>
        </div>
    );
}

export default function FilePreview({ fileUrl, fileName, fileType, fileSize, mimeType }: FilePreviewProps) {
    if (!fileName) {
        return <UnsupportedPreview fileName="Unknown" fileUrl={fileUrl} />;
    }

    const previewType = getPreviewType(fileName, mimeType);

    switch (previewType) {
        case 'model':
            return (
                <ModelViewer
                    modelUrl={fileUrl}
                    fileType={fileType || getFileExtension(fileName)}
                    fileName={fileName}
                />
            );

        case 'image':
            if (!fileUrl) {
                return <UnsupportedPreview fileName={fileName} fileUrl={fileUrl} />;
            }
            return <ImagePreview fileUrl={fileUrl} fileName={fileName} />;

        case 'document':
            if (!fileUrl) {
                return <UnsupportedPreview fileName={fileName} fileUrl={fileUrl} />;
            }
            return <DocumentPreview fileUrl={fileUrl} fileName={fileName} />;

        case 'unsupported':
        default:
            return <UnsupportedPreview fileName={fileName} fileUrl={fileUrl} />;
    }
}

export { getFileExtension, getPreviewType, SUPPORTED_3D_FORMATS, SUPPORTED_IMAGE_FORMATS, SUPPORTED_DOCUMENT_FORMATS };
