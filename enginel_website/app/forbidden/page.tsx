'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function ForbiddenPage() {
    const router = useRouter();

    return (
        <div className="min-h-screen bg-gradient-to-br from-red-50 via-orange-50 to-yellow-50 flex items-center justify-center px-4">
            <div className="max-w-2xl w-full text-center">
                {/* Lock Icon */}
                <div className="mb-8">
                    <svg
                        className="w-32 h-32 mx-auto text-red-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={1.5}
                            d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                        />
                    </svg>
                </div>

                {/* Error Code */}
                <h1 className="text-9xl font-bold text-red-600 mb-4">403</h1>

                {/* Title */}
                <h2 className="text-4xl font-bold text-gray-900 mb-4">
                    Access Forbidden
                </h2>

                {/* Description */}
                <p className="text-xl text-gray-600 mb-8">
                    You don't have permission to access this resource. This might be because:
                </p>

                {/* Reasons List */}
                <div className="bg-white rounded-lg shadow-lg p-6 mb-8 text-left">
                    <ul className="space-y-3 text-gray-700">
                        <li className="flex items-start space-x-3">
                            <svg className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                            <span>You don't have the required security clearance level</span>
                        </li>
                        <li className="flex items-start space-x-3">
                            <svg className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                            <span>You're not assigned to this project or design series</span>
                        </li>
                        <li className="flex items-start space-x-3">
                            <svg className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                            <span>This resource has been restricted by an administrator</span>
                        </li>
                        <li className="flex items-start space-x-3">
                            <svg className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                            <span>Your account doesn't have the necessary role or permissions</span>
                        </li>
                    </ul>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
                    <button
                        onClick={() => router.back()}
                        className="w-full sm:w-auto px-8 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center justify-center space-x-2"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                        </svg>
                        <span>Go Back</span>
                    </button>
                    <Link
                        href="/dashboard"
                        className="w-full sm:w-auto px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center space-x-2"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                        </svg>
                        <span>Go to Dashboard</span>
                    </Link>
                </div>

                {/* Contact Support */}
                <div className="mt-8 text-sm text-gray-500">
                    <p>
                        If you believe this is an error, please{' '}
                        <a href="mailto:support@enginel.com" className="text-blue-600 hover:underline">
                            contact your administrator
                        </a>
                        {' '}for assistance.
                    </p>
                </div>
            </div>
        </div>
    );
}
