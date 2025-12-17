'use client';

import { useEffect } from 'react';

export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        // Log the error to an error reporting service
        console.error('Global application error:', error);
    }, [error]);

    return (
        <html>
            <body>
                <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
                    <div className="max-w-lg w-full text-center">
                        {/* Critical Error Illustration */}
                        <div className="mb-8">
                            <svg
                                className="mx-auto h-48 w-48 text-red-500"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                aria-hidden="true"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={1.5}
                                    d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                                />
                            </svg>
                        </div>

                        {/* Error Message */}
                        <h1 className="text-4xl font-bold text-gray-900 mb-4">Critical Error</h1>
                        <p className="text-gray-600 mb-6">
                            A critical error has occurred and the application needs to restart.
                        </p>

                        {/* Error Details */}
                        <div className="mb-8 p-4 bg-red-50 border border-red-200 rounded-lg">
                            <p className="text-sm font-semibold text-red-800 mb-2">Error Information:</p>
                            <p className="text-sm text-red-700 break-words">
                                {error.message || 'An unexpected error occurred'}
                            </p>
                            {error.digest && (
                                <p className="text-xs text-red-600 mt-2">
                                    Error ID: {error.digest}
                                </p>
                            )}
                        </div>

                        {/* Action Buttons */}
                        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
                            <button
                                onClick={reset}
                                className="inline-flex items-center justify-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                                Restart Application
                            </button>
                            <button
                                onClick={() => window.location.href = '/'}
                                className="inline-flex items-center justify-center px-6 py-3 bg-white text-gray-700 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
                            >
                                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                                </svg>
                                Go to Home
                            </button>
                        </div>

                        {/* Recovery Options */}
                        <div className="pt-8 border-t border-gray-200">
                            <p className="text-sm text-gray-600 mb-4">Recovery Options:</p>
                            <div className="flex flex-col gap-2 text-sm">
                                <button
                                    onClick={() => window.location.reload()}
                                    className="text-blue-600 hover:text-blue-800"
                                >
                                    Force Reload Page
                                </button>
                                <button
                                    onClick={() => {
                                        localStorage.clear();
                                        sessionStorage.clear();
                                        window.location.href = '/';
                                    }}
                                    className="text-blue-600 hover:text-blue-800"
                                >
                                    Clear All Data & Restart
                                </button>
                            </div>
                        </div>

                        {/* Additional Help */}
                        <div className="mt-8 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                            <p className="text-sm text-yellow-800">
                                <strong>Note:</strong> If this error continues to occur, please contact your
                                system administrator with the error ID shown above.
                            </p>
                        </div>
                    </div>
                </div>
            </body>
        </html>
    );
}
