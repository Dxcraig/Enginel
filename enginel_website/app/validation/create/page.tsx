'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import ApiClient from '@/lib/api/client';
import { ValidationRule } from '@/types';
import Link from 'next/link';

const RULE_TYPES = [
    { value: 'REGEX', label: 'Regular Expression' },
    { value: 'RANGE', label: 'Numeric Range' },
    { value: 'LENGTH', label: 'String Length' },
    { value: 'FORMAT', label: 'Format Validation' },
    { value: 'CUSTOM', label: 'Custom Expression' },
    { value: 'FILE_TYPE', label: 'File Type' },
    { value: 'FILE_SIZE', label: 'File Size' },
    { value: 'UNIQUENESS', label: 'Uniqueness Check' },
    { value: 'RELATIONSHIP', label: 'Relationship' },
    { value: 'BUSINESS_RULE', label: 'Business Rule' },
];

const TARGET_MODELS = [
    { value: 'DesignAsset', label: 'Design Asset' },
    { value: 'DesignSeries', label: 'Design Series' },
    { value: 'CustomUser', label: 'User' },
    { value: 'ReviewSession', label: 'Review Session' },
    { value: 'Markup', label: 'Markup' },
    { value: 'AssemblyNode', label: 'Assembly Node' },
    { value: '*', label: 'All Models' },
];

const SEVERITIES = [
    { value: 'INFO', label: 'Informational', description: 'For informational purposes only' },
    { value: 'WARNING', label: 'Warning', description: 'Important but non-blocking' },
    { value: 'ERROR', label: 'Error', description: 'Must be resolved' },
    { value: 'CRITICAL', label: 'Critical', description: 'Blocks all operations' },
];

export default function CreateValidationRulePage() {
    const { user, isLoading: authLoading } = useAuth();
    const router = useRouter();

    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        rule_type: 'REGEX',
        target_model: 'DesignAsset',
        target_field: '',
        error_message: '',
        severity: 'ERROR',
        is_active: true,
        apply_on_create: true,
        apply_on_update: true,
        rule_config: '{}',
    });

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        try {
            setSaving(true);
            setError('');

            // Parse rule_config
            let parsedConfig;
            try {
                parsedConfig = JSON.parse(formData.rule_config);
            } catch (err) {
                setError('Invalid JSON in Rule Configuration');
                setSaving(false);
                return;
            }

            const payload = {
                ...formData,
                rule_config: parsedConfig,
            };

            await ApiClient.post('/validation/rules/', payload);
            router.push('/validation');
        } catch (err: any) {
            setError(err.message || 'Failed to create validation rule');
        } finally {
            setSaving(false);
        }
    };

    const updateFormData = (field: string, value: any) => {
        setFormData({ ...formData, [field]: value });
    };

    const getConfigExample = () => {
        switch (formData.rule_type) {
            case 'REGEX':
                return '{"pattern": "^[A-Z]{2}-\\\\d{4}$"}';
            case 'RANGE':
                return '{"min": 0, "max": 100}';
            case 'LENGTH':
                return '{"min_length": 5, "max_length": 255}';
            case 'FILE_SIZE':
                return '{"max_size_mb": 100}';
            case 'FILE_TYPE':
                return '{"allowed_types": ["STEP", "STL", "IGES"]}';
            case 'CUSTOM':
                return '{"expression": "value > 0 and value < 100"}';
            default:
                return '{}';
        }
    };

    if (authLoading || !user) {
        return null;
    }

    return (
        <div className="container mx-auto px-4 py-8 max-w-4xl">
            {/* Header */}
            <div className="mb-8">
                <Link href="/validation" className="text-gray-600 hover:text-gray-900 mb-2 inline-block">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                </Link>
                <h1 className="text-3xl font-bold text-gray-900">Create Validation Rule</h1>
                <p className="text-gray-600 mt-2">Define a new validation rule for data quality enforcement</p>
            </div>

            {/* Error Message */}
            {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                    {error}
                </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
                <div className="space-y-6">
                    {/* Basic Information */}
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">Basic Information</h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Rule Name <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => updateFormData('name', e.target.value)}
                                    required
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="e.g., Part Number Format Check"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Description <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    value={formData.description}
                                    onChange={(e) => updateFormData('description', e.target.value)}
                                    required
                                    rows={3}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="Describe what this rule validates..."
                                />
                            </div>
                        </div>
                    </div>

                    {/* Rule Configuration */}
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">Rule Configuration</h2>

                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Rule Type <span className="text-red-500">*</span>
                                    </label>
                                    <select
                                        value={formData.rule_type}
                                        onChange={(e) => updateFormData('rule_type', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    >
                                        {RULE_TYPES.map((type) => (
                                            <option key={type.value} value={type.value}>{type.label}</option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Target Model <span className="text-red-500">*</span>
                                    </label>
                                    <select
                                        value={formData.target_model}
                                        onChange={(e) => updateFormData('target_model', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    >
                                        {TARGET_MODELS.map((model) => (
                                            <option key={model.value} value={model.value}>{model.label}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Target Field
                                </label>
                                <input
                                    type="text"
                                    value={formData.target_field}
                                    onChange={(e) => updateFormData('target_field', e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="e.g., part_number, file_size (leave blank for model-level validation)"
                                />
                                <p className="text-xs text-gray-500 mt-1">Leave blank for model-level validation</p>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Rule Configuration (JSON) <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    value={formData.rule_config}
                                    onChange={(e) => updateFormData('rule_config', e.target.value)}
                                    rows={4}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                                    placeholder={getConfigExample()}
                                />
                                <p className="text-xs text-gray-500 mt-1">Example for {formData.rule_type}: {getConfigExample()}</p>
                            </div>
                        </div>
                    </div>

                    {/* Error Handling */}
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">Error Handling</h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Error Message <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    value={formData.error_message}
                                    onChange={(e) => updateFormData('error_message', e.target.value)}
                                    required
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="Message to display when validation fails"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Severity <span className="text-red-500">*</span>
                                </label>
                                <div className="grid grid-cols-2 gap-3">
                                    {SEVERITIES.map((sev) => (
                                        <label
                                            key={sev.value}
                                            className={`relative flex items-start p-3 border-2 rounded-lg cursor-pointer transition-colors ${formData.severity === sev.value
                                                    ? 'border-blue-500 bg-blue-50'
                                                    : 'border-gray-200 hover:border-gray-300'
                                                }`}
                                        >
                                            <input
                                                type="radio"
                                                name="severity"
                                                value={sev.value}
                                                checked={formData.severity === sev.value}
                                                onChange={(e) => updateFormData('severity', e.target.value)}
                                                className="mt-1"
                                            />
                                            <div className="ml-3">
                                                <div className="text-sm font-medium text-gray-900">{sev.label}</div>
                                                <div className="text-xs text-gray-500">{sev.description}</div>
                                            </div>
                                        </label>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Activation Settings */}
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">Activation Settings</h2>

                        <div className="space-y-3">
                            <label className="flex items-center space-x-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={formData.is_active}
                                    onChange={(e) => updateFormData('is_active', e.target.checked)}
                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <div>
                                    <div className="text-sm font-medium text-gray-900">Active</div>
                                    <div className="text-xs text-gray-500">Rule is enabled and will be applied</div>
                                </div>
                            </label>

                            <label className="flex items-center space-x-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={formData.apply_on_create}
                                    onChange={(e) => updateFormData('apply_on_create', e.target.checked)}
                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <div>
                                    <div className="text-sm font-medium text-gray-900">Apply on Create</div>
                                    <div className="text-xs text-gray-500">Validate when creating new records</div>
                                </div>
                            </label>

                            <label className="flex items-center space-x-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={formData.apply_on_update}
                                    onChange={(e) => updateFormData('apply_on_update', e.target.checked)}
                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <div>
                                    <div className="text-sm font-medium text-gray-900">Apply on Update</div>
                                    <div className="text-xs text-gray-500">Validate when updating existing records</div>
                                </div>
                            </label>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200">
                        <Link
                            href="/validation"
                            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                        >
                            Cancel
                        </Link>
                        <button
                            type="submit"
                            disabled={saving}
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg transition-colors"
                        >
                            {saving ? 'Creating...' : 'Create Rule'}
                        </button>
                    </div>
                </div>
            </form>
        </div>
    );
}
