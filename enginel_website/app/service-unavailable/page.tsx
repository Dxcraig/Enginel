'use client';

import { useRouter } from 'next/navigation';

export default function ServiceUnavailablePage() {
    const router = useRouter();

    const handleRetry = () => {
        window.location.reload();
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-red-50 flex items-center justify-center px-4">
            <div className="max-w-2xl w-full text-center">
                {/* Service Icon */}
                <div className="mb-8">
                    <svg
                        className="w-32 h-32 mx-auto text-purple-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={1.5}
                            d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"
                        />
                    </svg>
                </div>

                {/* Error Code */}
                <h1 className="text-9xl font-bold text-purple-600 mb-4">503</h1>

                {/* Title */}
                <h2 className="text-4xl font-bold text-gray-900 mb-4">
                    Service Unavailable
                </h2>

                {/* Description */}
                <p className="text-xl text-gray-600 mb-8">
                    Our servers are experiencing high traffic or temporary issues.
                    We're working to restore service as quickly as possible.
                </p>

                {/* Status Information */}
                <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
                    <div className="flex items-center justify-center space-x-3 mb-6">
                        <div className="flex space-x-1">
                            <div className="w-3 h-3 bg-purple-500 rounded-full animate-pulse" style={{ animationDelay: '0ms' }}></div>
                            <div className="w-3 h-3 bg-purple-500 rounded-full animate-pulse" style={{ animationDelay: '150ms' }}></div>
                            <div className="w-3 h-3 bg-purple-500 rounded-full animate-pulse" style={{ animationDelay: '300ms' }}></div>
                        </div>
                        <span className="text-gray-700 font-medium">Processing your request...</span>
                    </div>

                    <div className="space-y-4 text-left">
                        <div className="flex items-start space-x-3">
                            <svg className="w-6 h-6 text-purple-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <div>
                                <p className="font-semibold text-gray-900">Why is this happening?</p>
                                <p className="text-gray-600 text-sm">
                                    The service might be temporarily overloaded, undergoing maintenance, or experiencing technical difficulties.
                                </p>
                            </div>
                        </div>

                        <div className="flex items-start space-x-3">
                            <svg className="w-6 h-6 text-purple-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <div>
                                <p className="font-semibold text-gray-900">What should I do?</p>
                                <p className="text-gray-600 text-sm">
                                    Please wait a few moments and try refreshing the page. The issue is usually temporary.
                                </p>
                            </div>
                        </div>

                        <div className="flex items-start space-x-3">
                            <svg className="w-6 h-6 text-purple-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                            <div>
                                <p className="font-semibold text-gray-900">Your data is safe</p>
                                <p className="text-gray-600 text-sm">
                                    All your work has been saved. Nothing will be lost during this temporary service interruption.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Common Causes */}
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-6 mb-8 text-left">
                    <h3 className="font-semibold text-purple-900 mb-3 text-center">Common Causes</h3>
                    <ul className="space-y-2 text-sm text-purple-800">
                        <li className="flex items-center space-x-2">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clipRule="evenodd" />
                            </svg>
                            <span>Scheduled or emergency server maintenance</span>
                        </li>
                        <li className="flex items-center space-x-2">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clipRule="evenodd" />
                            </svg>
                            <span>High traffic volume during peak hours</span>
                        </li>
                        <li className="flex items-center space-x-2">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clipRule="evenodd" />
                            </svg>
                            <span>Temporary database or cache issues</span>
                        </li>
                        <li className="flex items-center space-x-2">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clipRule="evenodd" />
                            </svg>
                            <span>Infrastructure upgrades or deployments</span>
                        </li>
                    </ul>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
                    <button
                        onClick={handleRetry}
                        className="w-full sm:w-auto px-8 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center justify-center space-x-2"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        <span>Refresh Page</span>
                    </button>
                    <button
                        onClick={() => router.push('/dashboard')}
                        className="w-full sm:w-auto px-8 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center justify-center space-x-2"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                        </svg>
                        <span>Go to Dashboard</span>
                    </button>
                </div>

                {/* Support Information */}
                <div className="mt-8 text-sm text-gray-500">
                    <p>
                        If the problem persists, please{' '}
                        <a href="mailto:support@enginel.com" className="text-purple-600 hover:underline">
                            contact support
                        </a>
                        {' '}with error code: 503
                    </p>
                </div>
            </div>
        </div>
    );
}
