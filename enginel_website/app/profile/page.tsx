'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import ApiClient from '@/lib/api/client';

export default function ProfilePage() {
    const { user, isLoading: authLoading } = useAuth();
    const router = useRouter();

    const [editing, setEditing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        email: '',
        phone_number: '',
        department: '',
        job_title: '',
    });

    const [passwordData, setPasswordData] = useState({
        current_password: '',
        new_password: '',
        confirm_password: '',
    });
    const [changingPassword, setChangingPassword] = useState(false);
    const [showPasswordSection, setShowPasswordSection] = useState(false);

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (user) {
            setFormData({
                first_name: user.first_name || '',
                last_name: user.last_name || '',
                email: user.email || '',
                phone_number: user.phone_number || '',
                department: user.department || '',
                job_title: user.job_title || '',
            });
        }
    }, [user]);

    const handleSaveProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            setSaving(true);
            setError('');
            setSuccess('');

            await ApiClient.patch('/users/me/', formData);

            setSuccess('Profile updated successfully!');
            setEditing(false);

            // Reload user data
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } catch (err: any) {
            setError(err.message || 'Failed to update profile');
        } finally {
            setSaving(false);
        }
    };

    const handleChangePassword = async (e: React.FormEvent) => {
        e.preventDefault();

        if (passwordData.new_password !== passwordData.confirm_password) {
            setError('New passwords do not match');
            return;
        }

        if (passwordData.new_password.length < 8) {
            setError('Password must be at least 8 characters long');
            return;
        }

        try {
            setChangingPassword(true);
            setError('');
            setSuccess('');

            await ApiClient.post('/auth/change-password/', {
                current_password: passwordData.current_password,
                new_password: passwordData.new_password,
            });

            setSuccess('Password changed successfully!');
            setPasswordData({
                current_password: '',
                new_password: '',
                confirm_password: '',
            });
            setShowPasswordSection(false);
        } catch (err: any) {
            setError(err.message || 'Failed to change password');
        } finally {
            setChangingPassword(false);
        }
    };

    if (authLoading || !user) {
        return null;
    }

    const getInitials = (firstName?: string, lastName?: string) => {
        const first = firstName?.charAt(0) || '';
        const last = lastName?.charAt(0) || '';
        return (first + last).toUpperCase() || user?.username?.charAt(0).toUpperCase() || 'U';
    };

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Profile Header Banner */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-12 mb-8">
                <div className="container mx-auto">
                    <div className="flex items-center gap-6">
                        {/* Avatar */}
                        <div className="flex-shrink-0">
                            <div className="w-24 h-24 rounded-full bg-white flex items-center justify-center text-3xl font-bold text-blue-600 shadow-lg">
                                {getInitials(user.first_name, user.last_name)}
                            </div>
                        </div>

                        {/* User Info */}
                        <div className="flex-grow text-white">
                            <h1 className="text-3xl font-bold mb-1">
                                {user.first_name && user.last_name
                                    ? `${user.first_name} ${user.last_name}`
                                    : user.username}
                            </h1>
                            <p className="text-blue-100 mb-2">@{user.username}</p>
                            {(user.job_title || user.department) && (
                                <p className="text-blue-100 text-sm">
                                    {user.job_title}{user.job_title && user.department ? ' • ' : ''}{user.department}
                                </p>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            <div className="container mx-auto px-4 pb-8">
                {/* Messages */}
                {error && (
                    <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                        {error}
                    </div>
                )}
                {success && (
                    <div className="mb-6 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg">
                        {success}
                    </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Main Content */}
                    <div className="lg:col-span-2 space-y-6">
                        {/* Profile Information */}
                        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
                            <div className="flex justify-between items-center mb-6">
                                <div className="flex items-center gap-2">
                                    <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                    </svg>
                                    <h2 className="text-xl font-semibold text-gray-900">Profile Information</h2>
                                </div>
                                {!editing && (
                                    <button
                                        onClick={() => setEditing(true)}
                                        className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                    >
                                        Edit Profile
                                    </button>
                                )}
                            </div>

                            <form onSubmit={handleSaveProfile}>
                                <div className="space-y-4">
                                    {/* Username (Read-only) */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Username
                                        </label>
                                        <input
                                            type="text"
                                            value={user.username}
                                            disabled
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-600 cursor-not-allowed"
                                        />
                                        <p className="text-xs text-gray-500 mt-1">Username cannot be changed</p>
                                    </div>

                                    {/* First Name */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            First Name
                                        </label>
                                        <input
                                            type="text"
                                            value={formData.first_name}
                                            onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                                            disabled={!editing}
                                            className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${!editing ? 'bg-gray-50' : ''
                                                }`}
                                        />
                                    </div>

                                    {/* Last Name */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Last Name
                                        </label>
                                        <input
                                            type="text"
                                            value={formData.last_name}
                                            onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                                            disabled={!editing}
                                            className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${!editing ? 'bg-gray-50' : ''
                                                }`}
                                        />
                                    </div>

                                    {/* Email */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Email Address
                                        </label>
                                        <input
                                            type="email"
                                            value={formData.email}
                                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                            disabled={!editing}
                                            className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${!editing ? 'bg-gray-50' : ''
                                                }`}
                                        />
                                    </div>

                                    {/* Phone Number */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Phone Number
                                        </label>
                                        <input
                                            type="tel"
                                            value={formData.phone_number}
                                            onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                                            disabled={!editing}
                                            placeholder="Optional"
                                            className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${!editing ? 'bg-gray-50' : ''
                                                }`}
                                        />
                                    </div>

                                    {/* Department */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Department
                                        </label>
                                        <input
                                            type="text"
                                            value={formData.department}
                                            onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                                            disabled={!editing}
                                            placeholder="e.g., Engineering, Design"
                                            className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${!editing ? 'bg-gray-50' : ''
                                                }`}
                                        />
                                    </div>

                                    {/* Job Title */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Job Title
                                        </label>
                                        <input
                                            type="text"
                                            value={formData.job_title}
                                            onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                                            disabled={!editing}
                                            placeholder="e.g., Senior Engineer, Designer"
                                            className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${!editing ? 'bg-gray-50' : ''
                                                }`}
                                        />
                                    </div>
                                </div>

                                {/* Action Buttons */}
                                {editing && (
                                    <div className="flex space-x-3 mt-6">
                                        <button
                                            type="submit"
                                            disabled={saving}
                                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                                        >
                                            {saving ? 'Saving...' : 'Save Changes'}
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setEditing(false);
                                                setFormData({
                                                    first_name: user.first_name || '',
                                                    last_name: user.last_name || '',
                                                    email: user.email || '',
                                                    phone_number: user.phone_number || '',
                                                    department: user.department || '',
                                                    job_title: user.job_title || '',
                                                });
                                            }}
                                            className="px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg font-medium transition-colors"
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                )}
                            </form>
                        </div>

                        {/* Password Change */}
                        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
                            <div className="flex justify-between items-center mb-4">
                                <div>
                                    <h2 className="text-xl font-semibold text-gray-900">Password</h2>
                                    <p className="text-sm text-gray-600 mt-1">Change your account password</p>
                                </div>
                                {!showPasswordSection && (
                                    <button
                                        onClick={() => setShowPasswordSection(true)}
                                        className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                    >
                                        Change Password
                                    </button>
                                )}
                            </div>

                            {showPasswordSection && (
                                <form onSubmit={handleChangePassword} className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Current Password
                                        </label>
                                        <input
                                            type="password"
                                            value={passwordData.current_password}
                                            onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
                                            required
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            New Password
                                        </label>
                                        <input
                                            type="password"
                                            value={passwordData.new_password}
                                            onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                                            required
                                            minLength={8}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        />
                                        <p className="text-xs text-gray-500 mt-1">Minimum 8 characters</p>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Confirm New Password
                                        </label>
                                        <input
                                            type="password"
                                            value={passwordData.confirm_password}
                                            onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                                            required
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        />
                                    </div>

                                    <div className="flex space-x-3 pt-2">
                                        <button
                                            type="submit"
                                            disabled={changingPassword}
                                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                                        >
                                            {changingPassword ? 'Changing...' : 'Change Password'}
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setShowPasswordSection(false);
                                                setPasswordData({
                                                    current_password: '',
                                                    new_password: '',
                                                    confirm_password: '',
                                                });
                                                setError('');
                                            }}
                                            className="px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg font-medium transition-colors"
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </form>
                            )}
                        </div>
                    </div>

                    {/* Sidebar */}
                    <div className="space-y-6">
                        {/* Security Clearance */}
                        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
                            <h2 className="text-xl font-semibold text-gray-900 mb-4">Security Clearance</h2>
                            <div className="space-y-4">
                                <div>
                                    <div className="text-sm text-gray-600 mb-2">Clearance Level</div>
                                    <span className={`inline-flex items-center px-3 py-2 rounded-lg text-sm font-semibold ${user.security_clearance_level === 'UNCLASSIFIED'
                                            ? 'bg-gray-100 text-gray-800'
                                            : user.security_clearance_level === 'CONFIDENTIAL'
                                                ? 'bg-blue-100 text-blue-800'
                                                : user.security_clearance_level === 'SECRET'
                                                    ? 'bg-yellow-100 text-yellow-800'
                                                    : user.security_clearance_level === 'TOP_SECRET'
                                                        ? 'bg-red-100 text-red-800'
                                                        : 'bg-gray-100 text-gray-800'
                                        }`}>
                                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                        </svg>
                                        {user.security_clearance_level}
                                    </span>
                                </div>

                                <div className="pt-4 border-t border-gray-200">
                                    <p className="text-xs text-gray-500">
                                        Security clearance level is managed by your system administrator and cannot be changed here.
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Account Information */}
                        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
                            <h2 className="text-xl font-semibold text-gray-900 mb-4">Account Information</h2>
                            <div className="space-y-3 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-gray-600">Member Since</span>
                                    <span className="font-medium text-gray-900">
                                        {new Date(user.date_joined).toLocaleDateString()}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-600">User ID</span>
                                    <span className="font-mono text-xs text-gray-900">{user.id}</span>
                                </div>
                                {user.organization && (
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Organization</span>
                                        <span className="font-medium text-gray-900">{user.organization}</span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Preferences (Placeholder for future) */}
                        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
                            <h2 className="text-xl font-semibold text-gray-900 mb-4">Preferences</h2>
                            <div className="space-y-3">
                                <label className="flex items-center">
                                    <input
                                        type="checkbox"
                                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                                        defaultChecked
                                    />
                                    <span className="ml-3 text-sm text-gray-700">Email notifications</span>
                                </label>
                                <label className="flex items-center">
                                    <input
                                        type="checkbox"
                                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                                        defaultChecked
                                    />
                                    <span className="ml-3 text-sm text-gray-700">Review assignments</span>
                                </label>
                                <label className="flex items-center">
                                    <input
                                        type="checkbox"
                                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                                    />
                                    <span className="ml-3 text-sm text-gray-700">Weekly digest</span>
                                </label>
                            </div>
                            <p className="text-xs text-gray-500 mt-4">
                                Notification preferences will be saved automatically in a future update.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
