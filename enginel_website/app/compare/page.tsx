'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useSearchParams } from 'next/navigation';
import ApiClient from '@/lib/api/client';
import { DesignAsset, DesignSeries } from '@/types';
import Link from 'next/link';

interface ComparisonData {
    left: DesignAsset | null;
    right: DesignAsset | null;
}

export default function ComparePage() {
    const { user, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();

    const [comparison, setComparison] = useState<ComparisonData>({ left: null, right: null });
    const [seriesList, setSeriesList] = useState<DesignSeries[]>([]);
    const [designsList, setDesignsList] = useState<DesignAsset[]>([]);
    const [selectedSeries, setSelectedSeries] = useState<string>('');
    const [selectedLeft, setSelectedLeft] = useState<string>('');
    const [selectedRight, setSelectedRight] = useState<string>('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (user) {
            loadSeries();

            // Check URL params for pre-selected designs
            const leftId = searchParams.get('left');
            const rightId = searchParams.get('right');

            if (leftId && rightId) {
                loadComparison(leftId, rightId);
            }
        }
    }, [user]);

    useEffect(() => {
        if (selectedSeries) {
            loadDesignsForSeries(selectedSeries);
        }
    }, [selectedSeries]);

    const loadSeries = async () => {
        try {
            const data = await ApiClient.get<{ results: DesignSeries[] }>('/series/');
            setSeriesList(data.results);
        } catch (err: any) {
            console.error('Failed to load series:', err);
        }
    };

    const loadDesignsForSeries = async (seriesId: string) => {
        try {
            setLoading(true);
            const data = await ApiClient.get<{ results: DesignAsset[] }>(`/designs/?series=${seriesId}`);
            setDesignsList(data.results.sort((a, b) => b.version_number - a.version_number));
            setError('');
        } catch (err: any) {
            setError(err.message || 'Failed to load designs');
        } finally {
            setLoading(false);
        }
    };

    const loadComparison = async (leftId: string, rightId: string) => {
        try {
            setLoading(true);
            const [leftData, rightData] = await Promise.all([
                ApiClient.get<DesignAsset>(`/designs/${leftId}/`),
                ApiClient.get<DesignAsset>(`/designs/${rightId}/`),
            ]);
            setComparison({ left: leftData, right: rightData });
            setError('');
        } catch (err: any) {
            setError(err.message || 'Failed to load designs for comparison');
        } finally {
            setLoading(false);
        }
    };

    const handleCompare = () => {
        if (selectedLeft && selectedRight) {
            loadComparison(selectedLeft, selectedRight);
            // Update URL
            router.push(`/compare?left=${selectedLeft}&right=${selectedRight}`);
        }
    };

    const getDifference = (leftVal: any, rightVal: any): 'same' | 'different' => {
        return JSON.stringify(leftVal) === JSON.stringify(rightVal) ? 'same' : 'different';
    };

    const ComparisonRow = ({
        label,
        leftValue,
        rightValue
    }: {
        label: string;
        leftValue: any;
        rightValue: any;
    }) => {
        const isDifferent = getDifference(leftValue, rightValue) === 'different';

        return (
            <div className={`grid grid-cols-3 gap-4 py-3 border-b border-gray-200 ${isDifferent ? 'bg-yellow-50' : ''}`}>
                <div className="font-medium text-gray-700">{label}</div>
                <div className={`text-gray-900 ${isDifferent ? 'font-semibold' : ''}`}>
                    {leftValue !== null && leftValue !== undefined ? String(leftValue) : '-'}
                </div>
                <div className={`text-gray-900 ${isDifferent ? 'font-semibold' : ''}`}>
                    {rightValue !== null && rightValue !== undefined ? String(rightValue) : '-'}
                </div>
            </div>
        );
    };

    if (authLoading || !user) {
        return null;
    }

    return (
        <div className="container mx-auto px-4 py-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Design Comparison</h1>
                <p className="text-gray-600 mt-2">Compare two design versions side-by-side</p>
            </div>

            {/* Selection Controls */}
            <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Select Designs to Compare</h2>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {/* Series Selection */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Part Number Series
                        </label>
                        <select
                            value={selectedSeries}
                            onChange={(e) => {
                                setSelectedSeries(e.target.value);
                                setSelectedLeft('');
                                setSelectedRight('');
                                setComparison({ left: null, right: null });
                            }}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">Select series...</option>
                            {seriesList.map((series) => (
                                <option key={series.id} value={series.id}>
                                    {series.part_number}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Left Design */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            First Design (Left)
                        </label>
                        <select
                            value={selectedLeft}
                            onChange={(e) => setSelectedLeft(e.target.value)}
                            disabled={!selectedSeries}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                        >
                            <option value="">Select design...</option>
                            {designsList.map((design) => (
                                <option key={design.id} value={design.id}>
                                    v{design.version_number} - {design.version_label || design.file_name}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Right Design */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Second Design (Right)
                        </label>
                        <select
                            value={selectedRight}
                            onChange={(e) => setSelectedRight(e.target.value)}
                            disabled={!selectedSeries}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                        >
                            <option value="">Select design...</option>
                            {designsList.map((design) => (
                                <option key={design.id} value={design.id}>
                                    v{design.version_number} - {design.version_label || design.file_name}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Compare Button */}
                    <div className="flex items-end">
                        <button
                            onClick={handleCompare}
                            disabled={!selectedLeft || !selectedRight || selectedLeft === selectedRight}
                            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
                        >
                            Compare
                        </button>
                    </div>
                </div>

                {error && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
                        {error}
                    </div>
                )}
            </div>

            {/* Comparison Results */}
            {loading ? (
                <div className="flex justify-center items-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            ) : comparison.left && comparison.right ? (
                <div className="space-y-6">
                    {/* Headers */}
                    <div className="grid grid-cols-3 gap-4 bg-gray-50 p-4 rounded-lg border border-gray-200">
                        <div className="font-semibold text-gray-700">Property</div>
                        <div className="font-semibold text-gray-900">
                            <div className="flex items-center justify-between">
                                <span>Version {comparison.left.version_number}</span>
                                <Link
                                    href={`/designs/${comparison.left.id}`}
                                    className="text-sm text-blue-600 hover:text-blue-700"
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                    </svg>
                                </Link>
                            </div>
                        </div>
                        <div className="font-semibold text-gray-900">
                            <div className="flex items-center justify-between">
                                <span>Version {comparison.right.version_number}</span>
                                <Link
                                    href={`/designs/${comparison.right.id}`}
                                    className="text-sm text-blue-600 hover:text-blue-700"
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                    </svg>
                                </Link>
                            </div>
                        </div>
                    </div>

                    {/* Basic Information */}
                    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h3>
                        <div>
                            <ComparisonRow
                                label="File Name"
                                leftValue={comparison.left.file_name}
                                rightValue={comparison.right.file_name}
                            />
                            <ComparisonRow
                                label="Version Label"
                                leftValue={comparison.left.version_label}
                                rightValue={comparison.right.version_label}
                            />
                            <ComparisonRow
                                label="Version Number"
                                leftValue={comparison.left.version_number}
                                rightValue={comparison.right.version_number}
                            />
                            <ComparisonRow
                                label="Classification"
                                leftValue={comparison.left.classification}
                                rightValue={comparison.right.classification}
                            />
                            <ComparisonRow
                                label="Processing Status"
                                leftValue={comparison.left.processing_status}
                                rightValue={comparison.right.processing_status}
                            />
                            <ComparisonRow
                                label="File Size"
                                leftValue={comparison.left.file_size ? `${(comparison.left.file_size / 1024).toFixed(2)} KB` : null}
                                rightValue={comparison.right.file_size ? `${(comparison.right.file_size / 1024).toFixed(2)} KB` : null}
                            />
                            <ComparisonRow
                                label="Created At"
                                leftValue={new Date(comparison.left.created_at).toLocaleString()}
                                rightValue={new Date(comparison.right.created_at).toLocaleString()}
                            />
                            <ComparisonRow
                                label="Updated At"
                                leftValue={new Date(comparison.left.updated_at).toLocaleString()}
                                rightValue={new Date(comparison.right.updated_at).toLocaleString()}
                            />
                        </div>
                    </div>

                    {/* Summary */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                        <h3 className="text-lg font-semibold text-blue-900 mb-2">Comparison Summary</h3>
                        <p className="text-blue-800">
                            Comparing <strong>Version {comparison.left.version_number}</strong> with{' '}
                            <strong>Version {comparison.right.version_number}</strong>
                        </p>
                        <p className="text-sm text-blue-700 mt-2">
                            💡 Highlighted rows indicate differences between the two versions
                        </p>
                    </div>
                </div>
            ) : (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-12 text-center">
                    <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No Comparison Yet</h3>
                    <p className="text-gray-600">
                        Select a part number series and two designs above to compare them
                    </p>
                </div>
            )}
        </div>
    );
}
