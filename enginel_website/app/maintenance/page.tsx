'use client';

import { useState, useEffect } from 'react';

export default function MaintenancePage() {
    const [countdown, setCountdown] = useState<string>('');

    // Example: Set maintenance end time (2 hours from now)
    useEffect(() => {
        const maintenanceEnd = new Date();
        maintenanceEnd.setHours(maintenanceEnd.getHours() + 2);

        const updateCountdown = () => {
            const now = new Date();
            const diff = maintenanceEnd.getTime() - now.getTime();

            if (diff > 0) {
                const hours = Math.floor(diff / (1000 * 60 * 60));
                const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((diff % (1000 * 60)) / 1000);

                setCountdown(`${hours}h ${minutes}m ${seconds}s`);
            } else {
                setCountdown('Soon');
            }
        };

        updateCountdown();
        const interval = setInterval(updateCountdown, 1000);

        return () => clearInterval(interval);
    }, []);

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex items-center justify-center px-4">
            <div className="max-w-3xl w-full text-center">
                {/* Maintenance Icon */}
                <div className="mb-8 relative">
                    <svg
                        className="w-40 h-40 mx-auto text-indigo-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={1.5}
                            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                        />
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={1.5}
                            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                        />
                    </svg>
                    {/* Animated dots */}
                    <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-4">
                        <div className="flex space-x-2">
                            <div className="w-3 h-3 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                            <div className="w-3 h-3 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                            <div className="w-3 h-3 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                    </div>
                </div>

                {/* Status Badge */}
                <div className="inline-flex items-center space-x-2 px-4 py-2 bg-yellow-100 border border-yellow-300 rounded-full mb-6">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
                    <span className="text-sm font-semibold text-yellow-800">Scheduled Maintenance</span>
                </div>

                {/* Title */}
                <h1 className="text-5xl font-bold text-gray-900 mb-4">
                    We'll Be Right Back
                </h1>

                {/* Description */}
                <p className="text-xl text-gray-600 mb-8">
                    Enginel is currently undergoing scheduled maintenance to improve your experience.
                    We appreciate your patience!
                </p>

                {/* Countdown Timer */}
                {countdown && (
                    <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
                        <p className="text-sm text-gray-500 uppercase tracking-wider mb-2">
                            Estimated Time Remaining
                        </p>
                        <div className="text-5xl font-bold text-indigo-600 mb-4">
                            {countdown}
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                            <div className="bg-indigo-600 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                        </div>
                    </div>
                )}

                {/* What We're Doing */}
                <div className="bg-white rounded-lg shadow-lg p-8 mb-8 text-left">
                    <h3 className="text-2xl font-bold text-gray-900 mb-4 text-center">What We're Doing</h3>
                    <ul className="space-y-4">
                        <li className="flex items-start space-x-3">
                            <svg className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <div>
                                <p className="font-semibold text-gray-900">System Upgrades</p>
                                <p className="text-gray-600 text-sm">Installing the latest features and improvements</p>
                            </div>
                        </li>
                        <li className="flex items-start space-x-3">
                            <svg className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <div>
                                <p className="font-semibold text-gray-900">Performance Optimization</p>
                                <p className="text-gray-600 text-sm">Enhancing speed and reliability</p>
                            </div>
                        </li>
                        <li className="flex items-start space-x-3">
                            <svg className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <div>
                                <p className="font-semibold text-gray-900">Security Updates</p>
                                <p className="text-gray-600 text-sm">Implementing the latest security patches</p>
                            </div>
                        </li>
                        <li className="flex items-start space-x-3">
                            <svg className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <div>
                                <p className="font-semibold text-gray-900">Database Optimization</p>
                                <p className="text-gray-600 text-sm">Improving data processing and storage</p>
                            </div>
                        </li>
                    </ul>
                </div>

                {/* Contact Information */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                    <div className="flex items-start space-x-3">
                        <svg className="w-6 h-6 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <div className="text-left">
                            <p className="font-semibold text-blue-900 mb-1">Need Immediate Assistance?</p>
                            <p className="text-blue-700 text-sm mb-2">
                                For urgent matters, please contact our support team:
                            </p>
                            <a
                                href="mailto:support@enginel.com"
                                className="inline-flex items-center space-x-2 text-blue-600 hover:text-blue-700 font-medium"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                </svg>
                                <span>support@enginel.com</span>
                            </a>
                        </div>
                    </div>
                </div>

                {/* Refresh Button */}
                <button
                    onClick={() => window.location.reload()}
                    className="mt-8 px-8 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center justify-center space-x-2 mx-auto"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span>Check If We're Back</span>
                </button>
            </div>
        </div>
    );
}
