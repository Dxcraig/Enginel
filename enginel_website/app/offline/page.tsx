'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function OfflinePage() {
    const router = useRouter();
    const [isOnline, setIsOnline] = useState(false);
    const [retryCount, setRetryCount] = useState(0);

    useEffect(() => {
        // Check if we're actually online
        setIsOnline(navigator.onLine);

        const handleOnline = () => {
            setIsOnline(true);
            setTimeout(() => {
                router.push('/dashboard');
            }, 1000);
        };

        const handleOffline = () => {
            setIsOnline(false);
        };

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, [router]);

    const handleRetry = async () => {
        setRetryCount(prev => prev + 1);

        try {
            const response = await fetch('/api/health', {
                method: 'HEAD',
                cache: 'no-cache'
            });

            if (response.ok) {
                setIsOnline(true);
                router.push('/dashboard');
            }
        } catch (error) {
            console.error('Still offline:', error);
            setIsOnline(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-100 to-gray-200 flex items-center justify-center px-4">
            <div className="max-w-2xl w-full text-center">
                {/* Connection Icon */}
                <div className="mb-8 relative">
                    {isOnline ? (
                        <svg
                            className="w-32 h-32 mx-auto text-green-500"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={1.5}
                                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                            />
                        </svg>
                    ) : (
                        <svg
                            className="w-32 h-32 mx-auto text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={1.5}
                                d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"
                            />
                        </svg>
                    )}
                </div>

                {/* Status Badge */}
                <div className={`inline-flex items-center space-x-2 px-4 py-2 rounded-full mb-6 ${isOnline
                        ? 'bg-green-100 border border-green-300'
                        : 'bg-red-100 border border-red-300'
                    }`}>
                    <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                        }`}></div>
                    <span className={`text-sm font-semibold ${isOnline ? 'text-green-800' : 'text-red-800'
                        }`}>
                        {isOnline ? 'Back Online' : 'No Connection'}
                    </span>
                </div>

                {/* Title */}
                <h1 className="text-5xl font-bold text-gray-900 mb-4">
                    {isOnline ? 'Connection Restored!' : "You're Offline"}
                </h1>

                {/* Description */}
                <p className="text-xl text-gray-600 mb-8">
                    {isOnline
                        ? 'Great! Your connection has been restored. Redirecting you to the dashboard...'
                        : "It looks like you've lost your internet connection. Please check your network and try again."
                    }
                </p>

                {!isOnline && (
                    <>
                        {/* Troubleshooting Steps */}
                        <div className="bg-white rounded-lg shadow-lg p-8 mb-8 text-left">
                            <h3 className="text-2xl font-bold text-gray-900 mb-4 text-center">
                                Troubleshooting Steps
                            </h3>
                            <ul className="space-y-4">
                                <li className="flex items-start space-x-3">
                                    <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                                        <span className="text-blue-600 font-bold">1</span>
                                    </div>
                                    <div>
                                        <p className="font-semibold text-gray-900">Check Your WiFi or Ethernet</p>
                                        <p className="text-gray-600 text-sm">Make sure you're connected to your network</p>
                                    </div>
                                </li>
                                <li className="flex items-start space-x-3">
                                    <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                                        <span className="text-blue-600 font-bold">2</span>
                                    </div>
                                    <div>
                                        <p className="font-semibold text-gray-900">Restart Your Router</p>
                                        <p className="text-gray-600 text-sm">Unplug for 30 seconds, then plug back in</p>
                                    </div>
                                </li>
                                <li className="flex items-start space-x-3">
                                    <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                                        <span className="text-blue-600 font-bold">3</span>
                                    </div>
                                    <div>
                                        <p className="font-semibold text-gray-900">Check Firewall Settings</p>
                                        <p className="text-gray-600 text-sm">Ensure Enginel isn't blocked by your firewall</p>
                                    </div>
                                </li>
                                <li className="flex items-start space-x-3">
                                    <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                                        <span className="text-blue-600 font-bold">4</span>
                                    </div>
                                    <div>
                                        <p className="font-semibold text-gray-900">Contact IT Support</p>
                                        <p className="text-gray-600 text-sm">If the problem persists, reach out to your IT team</p>
                                    </div>
                                </li>
                            </ul>
                        </div>

                        {/* Retry Information */}
                        {retryCount > 0 && (
                            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                                <p className="text-yellow-800 text-sm">
                                    Retry attempts: {retryCount}
                                </p>
                            </div>
                        )}

                        {/* Action Buttons */}
                        <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
                            <button
                                onClick={handleRetry}
                                className="w-full sm:w-auto px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center space-x-2"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                                <span>Try Again</span>
                            </button>
                            <button
                                onClick={() => router.back()}
                                className="w-full sm:w-auto px-8 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center justify-center space-x-2"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                                </svg>
                                <span>Go Back</span>
                            </button>
                        </div>

                        {/* Offline Tips */}
                        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
                            <div className="flex items-start space-x-3">
                                <svg className="w-6 h-6 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <div className="text-left">
                                    <p className="font-semibold text-blue-900 mb-1">Did You Know?</p>
                                    <p className="text-blue-700 text-sm">
                                        Some features may be available offline in future updates. We're working on improving your offline experience!
                                    </p>
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
