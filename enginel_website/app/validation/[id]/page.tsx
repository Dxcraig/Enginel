'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useParams } from 'next/navigation';
import ApiClient from '@/lib/api/client';
import { ValidationRule, ValidationResult } from '@/types';
import Link from 'next/link';

export default function ValidationRuleDetailPage() {
    const { user, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const params = useParams();
    const ruleId = params.id as string;

    const [rule, setRule] = useState<ValidationRule | null>(null);
    const [results, setResults] = useState<ValidationResult[]>([]);
    const [statistics, setStatistics] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (user && ruleId) {
            loadRuleDetail();
        }
    }, [user, ruleId]);

    const loadRuleDetail = async () => {
        try {
            setLoading(true);
            const [ruleData, statsData, resultsData] = await Promise.all([
                ApiClient.get<ValidationRule>(`/validation/rules/${ruleId}/`),
                ApiClient.get<any>(`/validation/rules/${ruleId}/statistics/`),
                ApiClient.get<{ results: ValidationResult[] }>(`/validation/results/?rule=${ruleId}&ordering=-validated_at`),
            ]);

            setRule(ruleData);
            setStatistics(statsData.statistics);
            setResults(resultsData.results || []);
            setError('');
        } catch (err: any) {
            setError(err.message || 'Failed to load rule details');
        } finally {
            setLoading(false);
        }
    };

    const handleToggleActive = async () => {
        if (!rule) return;

        try {
            const action = rule.is_active ? 'deactivate' : 'activate';
            await ApiClient.post(`/validation/rules/${ruleId}/${action}/`, {});
            loadRuleDetail();
        } catch (err: any) {
            setError(err.message || 'Failed to update rule');
        }
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'CRITICAL': return 'bg-red-100 text-red-800';
            case 'ERROR': return 'bg-orange-100 text-orange-800';
            case 'WARNING': return 'bg-yellow-100 text-yellow-800';
            case 'INFO': return 'bg-blue-100 text-blue-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'PASSED': return 'bg-green-100 text-green-800';
            case 'FAILED': return 'bg-red-100 text-red-800';
            case 'SKIPPED': return 'bg-gray-100 text-gray-800';
            case 'ERROR': return 'bg-orange-100 text-orange-800';
            default: return 'bg-gray-100 text-gray-800';
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

    if (error || !rule) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                    {error || 'Rule not found'}
                </div>
                <Link href="/validation" className="mt-4 inline-block text-gray-600 hover:text-gray-900">
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
                <Link href="/validation" className="text-gray-600 hover:text-gray-900 mb-2 inline-block">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                </Link>
                <div className="flex justify-between items-start">
                    <div>
                        <div className="flex items-center space-x-3 mb-2">
                            <h1 className="text-3xl font-bold text-gray-900">{rule.name}</h1>
                            <span className={`px-3 py-1 text-sm font-semibold rounded-full ${getSeverityColor(rule.severity)}`}>
                                {rule.severity}
                            </span>
                            {rule.is_active ? (
                                <span className="px-3 py-1 text-sm font-semibold rounded-full bg-green-100 text-green-800">
                                    Active
                                </span>
                            ) : (
                                <span className="px-3 py-1 text-sm font-semibold rounded-full bg-gray-100 text-gray-800">
                                    Inactive
                                </span>
                            )}
                        </div>
                        <p className="text-gray-600">{rule.description}</p>
                    </div>
                    <div className="flex space-x-2">
                        <button
                            onClick={handleToggleActive}
                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${rule.is_active
                                    ? 'bg-orange-100 text-orange-700 hover:bg-orange-200'
                                    : 'bg-green-100 text-green-700 hover:bg-green-200'
                                }`}
                        >
                            {rule.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                        <Link
                            href={`/validation/${ruleId}/edit`}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                        >
                            Edit Rule
                        </Link>
                    </div>
                </div>
            </div>

            {/* Statistics Cards */}
            {statistics && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-white p-4 rounded-lg shadow">
                        <div className="text-sm text-gray-500 mb-1">Total Checks</div>
                        <div className="text-2xl font-bold text-gray-900">{statistics.total_checks || 0}</div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                        <div className="text-sm text-gray-500 mb-1">Total Failures</div>
                        <div className="text-2xl font-bold text-red-600">{statistics.total_failures || 0}</div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                        <div className="text-sm text-gray-500 mb-1">Failure Rate</div>
                        <div className="text-2xl font-bold text-orange-600">
                            {statistics.failure_rate ? `${(statistics.failure_rate * 100).toFixed(1)}%` : '0%'}
                        </div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                        <div className="text-sm text-gray-500 mb-1">Recent Pass Rate</div>
                        <div className="text-2xl font-bold text-green-600">
                            {statistics.recent_100?.pass_rate || 0}%
                        </div>
                        <div className="text-xs text-gray-500 mt-1">Last 100 checks</div>
                    </div>
                </div>
            )}

            {/* Rule Details */}
            <div className="bg-white shadow-md rounded-lg p-6 mb-6">
                <h2 className="text-xl font-semibold mb-4">Rule Details</h2>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <div className="text-sm text-gray-500 mb-1">Rule Type</div>
                        <div className="font-medium">{rule.rule_type}</div>
                    </div>
                    <div>
                        <div className="text-sm text-gray-500 mb-1">Target Model</div>
                        <div className="font-medium">{rule.target_model}</div>
                    </div>
                    <div>
                        <div className="text-sm text-gray-500 mb-1">Target Field</div>
                        <div className="font-medium">{rule.target_field || 'Model-level'}</div>
                    </div>
                    <div>
                        <div className="text-sm text-gray-500 mb-1">Created</div>
                        <div className="font-medium">{new Date(rule.created_at).toLocaleDateString()}</div>
                    </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="text-sm text-gray-500 mb-2">Error Message</div>
                    <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded italic">
                        "{rule.error_message}"
                    </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="text-sm text-gray-500 mb-2">Configuration</div>
                    <pre className="p-3 bg-gray-50 border border-gray-200 rounded text-sm overflow-x-auto">
                        {JSON.stringify(rule.rule_config, null, 2)}
                    </pre>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="text-sm text-gray-500 mb-2">Application Settings</div>
                    <div className="flex space-x-4 text-sm">
                        <div>
                            <span className={`px-2 py-1 rounded ${rule.apply_on_create ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                                {rule.apply_on_create ? '✓' : '✗'} Apply on Create
                            </span>
                        </div>
                        <div>
                            <span className={`px-2 py-1 rounded ${rule.apply_on_update ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                                {rule.apply_on_update ? '✓' : '✗'} Apply on Update
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Recent Results */}
            <div className="bg-white shadow-md rounded-lg overflow-hidden">
                <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
                    <h2 className="text-xl font-semibold text-gray-900">Recent Validation Results</h2>
                </div>
                {results.length === 0 ? (
                    <div className="px-6 py-12 text-center text-gray-500">
                        No validation results yet. This rule has not been applied.
                    </div>
                ) : (
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Error Message</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validated</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {results.map((result) => (
                                <tr key={result.id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(result.status)}`}>
                                            {result.status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="text-sm text-gray-900">{result.target_model}</div>
                                        {result.target_field && (
                                            <div className="text-xs text-gray-500">{result.target_field}</div>
                                        )}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="text-sm text-gray-700">{result.error_message || '-'}</div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {new Date(result.validated_at).toLocaleString()}
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
