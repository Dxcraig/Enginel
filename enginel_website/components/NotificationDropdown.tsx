'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ApiClient from '@/lib/api/client';
import { Notification } from '@/types';

interface NotificationDropdownProps {
    onClose: () => void;
    onUnreadCountChange: (count: number) => void;
}

export default function NotificationDropdown({ onClose, onUnreadCountChange }: NotificationDropdownProps) {
    const router = useRouter();
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<'all' | 'unread'>('all');

    useEffect(() => {
        fetchNotifications();
    }, [filter]);

    const fetchNotifications = async () => {
        try {
            setLoading(true);
            const params = filter === 'unread' ? '?is_read=false' : '';
            const data = await ApiClient.get<{ results: Notification[] }>(`/notifications/${params}`);
            setNotifications(data.results || []);
        } catch (error) {
            console.error('Failed to fetch notifications:', error);
        } finally {
            setLoading(false);
        }
    };

    const markAsRead = async (notificationId: string) => {
        try {
            await ApiClient.post(`/notifications/${notificationId}/mark_as_read/`, {});

            // Update local state
            setNotifications(prev =>
                prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
            );

            // Update unread count
            const unreadCount = notifications.filter(n => !n.is_read && n.id !== notificationId).length;
            onUnreadCountChange(Math.max(0, unreadCount));
        } catch (error) {
            console.error('Failed to mark notification as read:', error);
        }
    };

    const markAllAsRead = async () => {
        try {
            await ApiClient.post('/notifications/mark_all_as_read/', {});

            // Update local state
            setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
            onUnreadCountChange(0);
        } catch (error) {
            console.error('Failed to mark all as read:', error);
        }
    };

    const handleNotificationClick = (notification: Notification) => {
        if (!notification.is_read) {
            markAsRead(notification.id);
        }

        if (notification.action_url) {
            onClose();
            router.push(notification.action_url);
        }
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'URGENT': return 'text-red-600 bg-red-50 border-l-4 border-red-500';
            case 'HIGH': return 'text-orange-600 bg-orange-50 border-l-4 border-orange-500';
            case 'NORMAL': return 'text-blue-600 bg-blue-50';
            default: return 'text-gray-600 bg-gray-50';
        }
    };

    const getTypeIcon = (type: string) => {
        switch (type) {
            case 'REVIEW_ASSIGNED':
            case 'REVIEW_STARTED':
            case 'REVIEW_COMPLETED':
                return (
                    <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                );
            case 'DESIGN_UPLOADED':
            case 'DESIGN_APPROVED':
            case 'DESIGN_UPDATED':
                return (
                    <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                );
            case 'DESIGN_REJECTED':
            case 'VALIDATION_FAILED':
            case 'JOB_FAILED':
                return (
                    <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                );
            case 'MENTION':
            case 'REVIEW_COMMENT':
                return (
                    <svg className="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                    </svg>
                );
            case 'VALIDATION_PASSED':
            case 'JOB_COMPLETED':
                return (
                    <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                );
            default:
                return (
                    <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                );
        }
    };

    const groupByDate = (notifications: Notification[]) => {
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        const groups: { [key: string]: Notification[] } = {
            'Today': [],
            'Yesterday': [],
            'Earlier': [],
        };

        notifications.forEach(notification => {
            const notifDate = new Date(notification.created_at);
            const isToday = notifDate.toDateString() === today.toDateString();
            const isYesterday = notifDate.toDateString() === yesterday.toDateString();

            if (isToday) {
                groups['Today'].push(notification);
            } else if (isYesterday) {
                groups['Yesterday'].push(notification);
            } else {
                groups['Earlier'].push(notification);
            }
        });

        return groups;
    };

    const groupedNotifications = groupByDate(notifications);

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 z-30"
                onClick={onClose}
            />

            {/* Dropdown Panel */}
            <div className="absolute right-0 mt-2 w-96 bg-white rounded-lg shadow-2xl border border-gray-200 z-40 max-h-[600px] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="px-4 py-3 border-b border-gray-200 bg-slate-50">
                    <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold text-gray-900">Notifications</h3>
                        <div className="flex items-center space-x-2">
                            {/* Filter buttons */}
                            <button
                                onClick={() => setFilter('all')}
                                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${filter === 'all'
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                            >
                                All
                            </button>
                            <button
                                onClick={() => setFilter('unread')}
                                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${filter === 'unread'
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                            >
                                Unread
                            </button>
                        </div>
                    </div>

                    {/* Mark all as read */}
                    {notifications.some(n => !n.is_read) && (
                        <button
                            onClick={markAllAsRead}
                            className="mt-2 text-xs text-blue-600 hover:text-blue-700 font-medium"
                        >
                            Mark all as read
                        </button>
                    )}
                </div>

                {/* Notification List */}
                <div className="overflow-y-auto flex-1">
                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
                        </div>
                    ) : notifications.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 px-4">
                            <svg className="w-16 h-16 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                            </svg>
                            <p className="text-gray-500 text-sm font-medium">No notifications</p>
                            <p className="text-gray-400 text-xs mt-1">You're all caught up!</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-100">
                            {Object.entries(groupedNotifications).map(([date, dateNotifications]) => (
                                dateNotifications.length > 0 && (
                                    <div key={date}>
                                        <div className="px-4 py-2 bg-gray-50">
                                            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{date}</h4>
                                        </div>
                                        {dateNotifications.map((notification) => (
                                            <button
                                                key={notification.id}
                                                onClick={() => handleNotificationClick(notification)}
                                                className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors ${!notification.is_read ? 'bg-blue-50/50' : ''
                                                    } ${getPriorityColor(notification.priority)}`}
                                            >
                                                <div className="flex items-start space-x-3">
                                                    <div className="flex-shrink-0 mt-1">
                                                        {getTypeIcon(notification.notification_type)}
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-start justify-between">
                                                            <p className={`text-sm font-medium text-gray-900 ${!notification.is_read ? 'font-semibold' : ''}`}>
                                                                {notification.title}
                                                            </p>
                                                            {!notification.is_read && (
                                                                <span className="ml-2 w-2 h-2 bg-blue-600 rounded-full flex-shrink-0 mt-1.5" />
                                                            )}
                                                        </div>
                                                        <p className="text-xs text-gray-600 mt-1 line-clamp-2">{notification.message}</p>
                                                        <div className="flex items-center justify-between mt-2">
                                                            {notification.actor_username && (
                                                                <p className="text-xs text-gray-500">by {notification.actor_username}</p>
                                                            )}
                                                            <p className="text-xs text-gray-400">{notification.time_ago}</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                )
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-4 py-3 border-t border-gray-200 bg-slate-50">
                    <button
                        onClick={() => {
                            onClose();
                            router.push('/notifications');
                        }}
                        className="w-full text-center text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
                    >
                        View all notifications
                    </button>
                </div>
            </div>
        </>
    );
}
