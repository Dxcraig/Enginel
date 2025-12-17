'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import ApiClient from '@/lib/api/client';
import { DesignAsset, User } from '@/types';
import Link from 'next/link';

export default function CreateReviewPage() {
    const { user, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const [designs, setDesigns] = useState<DesignAsset[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        design_asset: '',
        status: 'DRAFT' as 'DRAFT' | 'ACTIVE',
        reviewers: [] as string[]
    });

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (user) {
            loadDesigns();
            loadUsers();
        }
    }, [user]);

    const loadDesigns = async () => {
        try {
            const data = await ApiClient.get<{ results: DesignAsset[] }>('/designs/');
            setDesigns(data.results || []);
        } catch (err: any) {
            console.error('Failed to load designs:', err);
        }
    };

    const loadUsers = async () => {
        try {
            const data = await ApiClient.get<{ results: User[] }>('/users/');
            setUsers(data.results || []);
        } catch (err: any) {
            console.error('Failed to load users:', err);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.design_asset) {
            setError('Please select a design asset');
            return;
        }

        try {
            setLoading(true);
            setError('');
            const response = await ApiClient.post<{ id: string }>('/reviews/', formData);
            router.push(`/reviews/${response.id}`);
        } catch (err: any) {
            console.error('Create review error:', err);
            setError(err.message || 'Failed to create review');
            setLoading(false);
        }
    };

    const toggleReviewer = (userId: string) => {
        setFormData(prev => ({
            ...prev,
            reviewers: prev.reviewers.includes(userId)
                ? prev.reviewers.filter(id => id !== userId)
                : [...prev.reviewers, userId]
        }));
    };

    if (authLoading || !user) {
        return null;
    }

    return (
        <div className="container mx-auto px-4 py-8 max-w-3xl">
            <Link href="/reviews" className="text-blue-600 hover:text-blue-700 mb-4 inline-flex items-center">
                <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to Reviews
            </Link>

            <div className="bg-white shadow-md rounded-lg p-6">
                <div className="mb-6">
                    <h1 className="text-3xl font-bold text-gray-900">Create Design Review</h1>
                    <p className="text-gray-600 mt-2">
                        Start a new review session for a design asset
                    </p>
                </div>

                {error && (
                    <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Design Asset */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Design Asset *
                        </label>
                        <select
                            required
                            value={formData.design_asset}
                            onChange={(e) => setFormData({ ...formData, design_asset: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                            <option value="">Select a design...</option>
                            {designs.map((design) => (
                                <option key={design.id} value={design.id}>
                                    {design.file_name || design.filename} {design.version_number && `(v${design.version_number})`}
                                </option>
                            ))}
                        </select>
                        <p className="mt-1 text-sm text-gray-500">
                            Select the design file to review
                        </p>
                    </div>

                    {/* Title */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Review Title *
                        </label>
                        <input
                            type="text"
                            required
                            value={formData.title}
                            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="e.g., PCB Layout Review - Rev A"
                        />
                    </div>

                    {/* Description */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Description
                        </label>
                        <textarea
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            rows={4}
                            placeholder="Describe the purpose and scope of this review..."
                        />
                    </div>

                    {/* Status */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Initial Status *
                        </label>
                        <div className="flex space-x-4">
                            <label className="flex items-center">
                                <input
                                    type="radio"
                                    value="DRAFT"
                                    checked={formData.status === 'DRAFT'}
                                    onChange={(e) => setFormData({ ...formData, status: 'DRAFT' })}
                                    className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-gray-700">Draft</span>
                            </label>
                            <label className="flex items-center">
                                <input
                                    type="radio"
                                    value="ACTIVE"
                                    checked={formData.status === 'ACTIVE'}
                                    onChange={(e) => setFormData({ ...formData, status: 'ACTIVE' })}
                                    className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-gray-700">Active</span>
                            </label>
                        </div>
                        <p className="mt-1 text-sm text-gray-500">
                            Start as Draft to prepare, or Active to begin immediately
                        </p>
                    </div>

                    {/* Reviewers */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Select Reviewers
                        </label>
                        <div className="border border-gray-300 rounded-lg p-4 max-h-80 overflow-y-auto">
                            {users.length === 0 ? (
                                <div className="text-center py-8">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                                    <p className="text-gray-500 text-sm">Loading users...</p>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {users
                                        .filter(u => u.id !== user?.id)
                                        .map((u) => (
                                            <label
                                                key={u.id}
                                                className="flex items-center p-3 hover:bg-gray-50 rounded cursor-pointer transition-colors"
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={formData.reviewers.includes(u.id)}
                                                    onChange={() => toggleReviewer(u.id)}
                                                    className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                                />
                                                <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-semibold mr-3 flex-shrink-0">
                                                    {u.username.charAt(0).toUpperCase()}
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="font-medium text-gray-900 truncate">{u.username}</div>
                                                    {u.email && (
                                                        <div className="text-sm text-gray-500 truncate">{u.email}</div>
                                                    )}
                                                </div>
                                                {u.security_clearance_level && (
                                                    <span className="ml-2 px-2 py-1 text-xs font-semibold bg-blue-100 text-blue-800 rounded flex-shrink-0">
                                                        {u.security_clearance_level}
                                                    </span>
                                                )}
                                            </label>
                                        ))}
                                </div>
                            )}
                        </div>
                        <p className="mt-2 text-sm text-gray-500">
                            {formData.reviewers.length} reviewer{formData.reviewers.length !== 1 ? 's' : ''} selected
                        </p>
                    </div>

                    {/* Actions */}
                    <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                        <Link
                            href="/reviews"
                            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors"
                        >
                            Cancel
                        </Link>
                        <button
                            type="submit"
                            disabled={loading}
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                        >
                            {loading ? 'Creating...' : 'Create Review'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
