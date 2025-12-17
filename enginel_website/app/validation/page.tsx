'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import ApiClient from '@/lib/api/client';
import { ValidationRule } from '@/types';
import Link from 'next/link';

export default function ValidationRulesPage() {
    const { user, isLoading: authLoading } = useAuth();
    const router = useRouter();

    const [rules, setRules] = useState<ValidationRule[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [filterActive, setFilterActive] = useState<'all' | 'active' | 'inactive'>('all');
    const [filterSeverity, setFilterSeverity] = useState<string>('all');
    const [filterModel, setFilterModel] = useState<string>('all');

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (user) {
            loadRules();
        }
    }, [user, filterActive, filterSeverity, filterModel]);

    const loadRules = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();

            if (filterActive === 'active') params.append('is_active', 'true');
            if (filterActive === 'inactive') params.append('is_active', 'false');
            if (filterSeverity !== 'all') params.append('severity', filterSeverity);
            if (filterModel !== 'all') params.append('target_model', filterModel);

            const data = await ApiClient.get<{ results: ValidationRule[] }>(
                `/validation/rules/?${params.toString()}`
            );
            setRules(data.results || []);
            setError('');
        } catch (err: any) {
            setError(err.message || 'Failed to load validation rules');
        } finally {
            setLoading(false);
        }
    };

    const handleToggleActive = async (ruleId: string, currentStatus: boolean) => {
        try {
            const action = currentStatus ? 'deactivate' : 'activate';
            await ApiClient.post(`/validation/rules/${ruleId}/${action}/`, {});
            loadRules();
        } catch (err: any) {
            setError(err.message || `Failed to ${currentStatus ? 'deactivate' : 'activate'} rule`);
        }
    };

    const handleDeleteRule = async (ruleId: string, ruleName: string) => {
        if (!confirm(`Are you sure you want to delete the rule "${ruleName}"?`)) {
            return;
        }

        try {
            await ApiClient.delete(`/validation/rules/${ruleId}/`);
            loadRules();
        } catch (err: any) {
            setError(err.message || 'Failed to delete rule');
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

    const getRuleTypeLabel = (type: string) => {
        const labels: Record<string, string> = {
            'REGEX': 'Regular Expression',
            'RANGE': 'Numeric Range',
            'LENGTH': 'String Length',
            'FORMAT': 'Format Validation',
            'CUSTOM': 'Custom Expression',
            'FILE_TYPE': 'File Type',
            'FILE_SIZE': 'File Size',
            'UNIQUENESS': 'Uniqueness Check',
            'RELATIONSHIP': 'Relationship',
            'BUSINESS_RULE': 'Business Rule',
        };
        return labels[type] || type;
    };

    if (authLoading || !user) {
        return null;
    }

    return (
        <div className="container mx-auto px-4 py-8">
            {/* Header */}
            <div className="mb-8">
                <div className="flex justify-between items-start">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Validation Rules</h1>
                        <p className="text-gray-600 mt-2">Manage data validation rules for your designs</p>
                    </div>
                    <Link
                        href="/validation/create"
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                    >
                        + Create Rule
                    </Link>
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                    {error}
                </div>
            )}

            {/* Filters */}
            <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4 mb-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
                        <select
                            value={filterActive}
                            onChange={(e) => setFilterActive(e.target.value as any)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                            <option value="all">All Rules</option>
                            <option value="active">Active Only</option>
                            <option value="inactive">Inactive Only</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Severity</label>
                        <select
                            value={filterSeverity}
                            onChange={(e) => setFilterSeverity(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                            <option value="all">All Severities</option>
                            <option value="CRITICAL">Critical</option>
                            <option value="ERROR">Error</option>
                            <option value="WARNING">Warning</option>
                            <option value="INFO">Info</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Target Model</label>
                        <select
                            value={filterModel}
                            onChange={(e) => setFilterModel(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                            <option value="all">All Models</option>
                            <option value="DesignAsset">Design Asset</option>
                            <option value="DesignSeries">Design Series</option>
                            <option value="ReviewSession">Review Session</option>
                            <option value="AssemblyNode">Assembly Node</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Rules List */}
            {loading ? (
                <div className="flex justify-center items-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            ) : rules.length === 0 ? (
                <div className="bg-white rounded-lg shadow-md border border-gray-200 p-12 text-center">
                    <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">No validation rules found</h3>
                    <p className="text-gray-600 mb-4">Create your first validation rule to start enforcing data quality</p>
                    <Link
                        href="/validation/create"
                        className="inline-block px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                    >
                        Create Rule
                    </Link>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-4">
                    {rules.map((rule) => (
                        <div
                            key={rule.id}
                            className="bg-white rounded-lg shadow-md border border-gray-200 p-6 hover:shadow-lg transition-shadow"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className="flex-1">
                                    <div className="flex items-center space-x-3 mb-2">
                                        <h3 className="text-lg font-semibold text-gray-900">{rule.name}</h3>
                                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getSeverityColor(rule.severity)}`}>
                                            {rule.severity}
                                        </span>
                                        {rule.is_active ? (
                                            <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                                                Active
                                            </span>
                                        ) : (
                                            <span className="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
                                                Inactive
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-gray-600 text-sm mb-3">{rule.description}</p>
                                    <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                                        <div>
                                            <span className="font-medium">Type:</span> {getRuleTypeLabel(rule.rule_type)}
                                        </div>
                                        <div>
                                            <span className="font-medium">Target:</span> {rule.target_model}
                                            {rule.target_field && ` → ${rule.target_field}`}
                                        </div>
                                        {rule.total_checks !== undefined && (
                                            <div>
                                                <span className="font-medium">Checks:</span> {rule.total_checks}
                                                {rule.total_failures !== undefined && ` (${rule.total_failures} failures)`}
                                            </div>
                                        )}
                                    </div>
                                </div>
                                <div className="flex space-x-2 ml-4">
                                    <Link
                                        href={`/validation/${rule.id}`}
                                        className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                    >
                                        View
                                    </Link>
                                    <Link
                                        href={`/validation/${rule.id}/edit`}
                                        className="px-3 py-1 text-sm text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
                                    >
                                        Edit
                                    </Link>
                                    <button
                                        onClick={() => handleToggleActive(rule.id, rule.is_active)}
                                        className={`px-3 py-1 text-sm rounded-lg transition-colors ${rule.is_active
                                                ? 'text-orange-600 hover:bg-orange-50'
                                                : 'text-green-600 hover:bg-green-50'
                                            }`}
                                    >
                                        {rule.is_active ? 'Deactivate' : 'Activate'}
                                    </button>
                                    <button
                                        onClick={() => handleDeleteRule(rule.id, rule.name)}
                                        className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                    >
                                        Delete
                                    </button>
                                </div>
                            </div>

                            {/* Error Message Preview */}
                            <div className="mt-4 pt-4 border-t border-gray-200">
                                <div className="text-xs text-gray-500 mb-1">Error Message:</div>
                                <div className="text-sm text-gray-700 italic">"{rule.error_message}"</div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
