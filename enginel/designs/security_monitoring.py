"""
Security monitoring and alerting for Enginel.

Provides:
- Real-time security event monitoring
- Threat detection and alerting
- Security metrics collection
- Incident response automation
"""

import logging
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from collections import defaultdict

logger = logging.getLogger(__name__)


class SecurityMonitor:
    """
    Real-time security monitoring and threat detection.
    """
    
    # Threat severity levels
    SEVERITY_LOW = 'LOW'
    SEVERITY_MEDIUM = 'MEDIUM'
    SEVERITY_HIGH = 'HIGH'
    SEVERITY_CRITICAL = 'CRITICAL'
    
    @classmethod
    def get_security_events(cls, severity=None, limit=100):
        """
        Get recent security events from cache.
        
        Args:
            severity: Filter by severity level
            limit: Maximum events to return
        
        Returns:
            List of security events
        """
        events = cache.get('security_events', [])
        
        if severity:
            events = [e for e in events if e.get('severity') == severity]
        
        return events[-limit:]
    
    @classmethod
    def get_threat_summary(cls):
        """
        Get summary of recent threats.
        
        Returns:
            Dictionary with threat statistics
        """
        events = cls.get_security_events()
        
        # Count by event type
        event_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        ip_counts = defaultdict(int)
        
        for event in events:
            event_counts[event.get('event_type', 'unknown')] += 1
            severity_counts[event.get('severity', 'UNKNOWN')] += 1
            ip = event.get('ip_address')
            if ip:
                ip_counts[ip] += 1
        
        # Find top offenders
        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_events': len(events),
            'event_counts': dict(event_counts),
            'severity_counts': dict(severity_counts),
            'top_ips': [{'ip': ip, 'count': count} for ip, count in top_ips],
            'recent_critical': len([e for e in events if e.get('severity') == cls.SEVERITY_CRITICAL]),
            'recent_high': len([e for e in events if e.get('severity') == cls.SEVERITY_HIGH]),
        }
    
    @classmethod
    def check_anomalies(cls, user_id=None, ip_address=None):
        """
        Check for anomalous behavior patterns.
        
        Args:
            user_id: User ID to check
            ip_address: IP address to check
        
        Returns:
            Dictionary with anomaly details
        """
        anomalies = []
        
        events = cls.get_security_events()
        
        if user_id:
            user_events = [e for e in events if e.get('user_id') == user_id]
            
            # Check for rapid authentication failures
            failed_logins = [e for e in user_events if e.get('event_type') == 'login_failed']
            if len(failed_logins) >= 3:
                anomalies.append({
                    'type': 'rapid_login_failures',
                    'severity': cls.SEVERITY_HIGH,
                    'count': len(failed_logins),
                    'user_id': user_id
                })
            
            # Check for unusual access patterns
            access_events = [e for e in user_events if e.get('event_type') == 'data_access']
            if len(access_events) > 100:  # More than 100 accesses
                anomalies.append({
                    'type': 'excessive_data_access',
                    'severity': cls.SEVERITY_MEDIUM,
                    'count': len(access_events),
                    'user_id': user_id
                })
        
        if ip_address:
            ip_events = [e for e in events if e.get('ip_address') == ip_address]
            
            # Check for distributed attack patterns
            if len(ip_events) > 50:
                anomalies.append({
                    'type': 'high_request_volume',
                    'severity': cls.SEVERITY_HIGH,
                    'count': len(ip_events),
                    'ip_address': ip_address
                })
            
            # Check for attack attempts
            attack_events = [e for e in ip_events if 'attack' in e.get('event_type', '')]
            if len(attack_events) > 0:
                anomalies.append({
                    'type': 'attack_detected',
                    'severity': cls.SEVERITY_CRITICAL,
                    'count': len(attack_events),
                    'ip_address': ip_address
                })
        
        return {
            'has_anomalies': len(anomalies) > 0,
            'anomalies': anomalies
        }
    
    @classmethod
    def get_blocked_ips(cls):
        """
        Get list of currently blocked IP addresses.
        
        Returns:
            List of blocked IPs with expiration times
        """
        # This would need to query cache keys matching pattern
        # For now, return from cache if stored
        return cache.get('blocked_ips_list', [])
    
    @classmethod
    def alert_security_team(cls, event_type, details, severity=SEVERITY_HIGH):
        """
        Send alert to security team.
        
        Args:
            event_type: Type of security event
            details: Event details dictionary
            severity: Severity level
        """
        # In production, this would send emails, Slack messages, PagerDuty alerts, etc.
        logger.critical(
            f"SECURITY ALERT [{severity}]: {event_type}",
            extra={'details': details}
        )
        
        # Store alert in cache for dashboard
        alerts_key = 'security_alerts'
        alerts = cache.get(alerts_key, [])
        alerts.append({
            'event_type': event_type,
            'details': details,
            'severity': severity,
            'timestamp': datetime.now().isoformat(),
            'acknowledged': False
        })
        cache.set(alerts_key, alerts[-100:], 86400)  # Keep last 100 alerts for 24 hours


class SecurityMetrics:
    """
    Collect and report security metrics.
    """
    
    @classmethod
    def get_authentication_metrics(cls):
        """
        Get authentication-related metrics.
        
        Returns:
            Dictionary with authentication metrics
        """
        events = SecurityMonitor.get_security_events()
        
        login_success = len([e for e in events if e.get('event_type') == 'login_success'])
        login_failed = len([e for e in events if e.get('event_type') == 'login_failed'])
        token_expired = len([e for e in events if e.get('event_type') == 'expired_token_attempt'])
        api_key_used = len([e for e in events if e.get('event_type') == 'api_key_used'])
        
        return {
            'login_success': login_success,
            'login_failed': login_failed,
            'login_success_rate': login_success / (login_success + login_failed) if (login_success + login_failed) > 0 else 0,
            'token_expired': token_expired,
            'api_key_used': api_key_used,
        }
    
    @classmethod
    def get_attack_metrics(cls):
        """
        Get attack detection metrics.
        
        Returns:
            Dictionary with attack metrics
        """
        events = SecurityMonitor.get_security_events()
        
        sql_injection = len([e for e in events if 'sql' in e.get('event_type', '').lower()])
        xss_attempts = len([e for e in events if 'xss' in e.get('event_type', '').lower()])
        brute_force = len([e for e in events if 'brute_force' in e.get('event_type', '')])
        blocked_ips = len(SecurityMonitor.get_blocked_ips())
        
        return {
            'sql_injection_attempts': sql_injection,
            'xss_attempts': xss_attempts,
            'brute_force_attempts': brute_force,
            'blocked_ips': blocked_ips,
            'total_attack_attempts': sql_injection + xss_attempts + brute_force,
        }
    
    @classmethod
    def get_access_metrics(cls):
        """
        Get data access metrics.
        
        Returns:
            Dictionary with access metrics
        """
        events = SecurityMonitor.get_security_events()
        
        data_access = len([e for e in events if e.get('event_type') == 'data_access'])
        permission_denied = len([e for e in events if e.get('event_type') == 'permission_denied'])
        file_uploads = len([e for e in events if 'upload' in e.get('event_type', '')])
        file_downloads = len([e for e in events if 'download' in e.get('event_type', '')])
        
        return {
            'data_access_events': data_access,
            'permission_denied': permission_denied,
            'file_uploads': file_uploads,
            'file_downloads': file_downloads,
        }
    
    @classmethod
    def generate_security_report(cls):
        """
        Generate comprehensive security report.
        
        Returns:
            Dictionary with complete security metrics
        """
        threat_summary = SecurityMonitor.get_threat_summary()
        auth_metrics = cls.get_authentication_metrics()
        attack_metrics = cls.get_attack_metrics()
        access_metrics = cls.get_access_metrics()
        
        return {
            'report_timestamp': datetime.now().isoformat(),
            'threat_summary': threat_summary,
            'authentication': auth_metrics,
            'attacks': attack_metrics,
            'access': access_metrics,
            'overall_security_score': cls._calculate_security_score(
                threat_summary, auth_metrics, attack_metrics
            ),
        }
    
    @classmethod
    def _calculate_security_score(cls, threat_summary, auth_metrics, attack_metrics):
        """
        Calculate overall security score (0-100).
        
        Args:
            threat_summary: Threat summary dict
            auth_metrics: Authentication metrics dict
            attack_metrics: Attack metrics dict
        
        Returns:
            Security score (0-100)
        """
        score = 100
        
        # Deduct for critical events
        score -= threat_summary.get('recent_critical', 0) * 10
        score -= threat_summary.get('recent_high', 0) * 5
        
        # Deduct for failed logins
        login_failed = auth_metrics.get('login_failed', 0)
        if login_failed > 10:
            score -= min(20, login_failed)
        
        # Deduct for attacks
        score -= attack_metrics.get('total_attack_attempts', 0) * 2
        
        return max(0, min(100, score))


class IncidentResponse:
    """
    Automated incident response actions.
    """
    
    @classmethod
    def handle_brute_force_attack(cls, ip_address, user_id=None):
        """
        Handle brute force attack detection.
        
        Args:
            ip_address: Attacking IP address
            user_id: Target user ID (if applicable)
        """
        from designs.security_middleware import IPBlockingMiddleware
        
        # Block IP for 24 hours
        IPBlockingMiddleware.block_ip(ip_address, duration_seconds=86400)
        
        # Alert security team
        SecurityMonitor.alert_security_team(
            'brute_force_attack',
            {
                'ip_address': ip_address,
                'user_id': user_id,
                'action_taken': 'IP blocked for 24 hours'
            },
            severity=SecurityMonitor.SEVERITY_CRITICAL
        )
        
        logger.critical(f"Brute force attack detected and blocked: {ip_address}")
    
    @classmethod
    def handle_account_compromise(cls, user_id, reason):
        """
        Handle suspected account compromise.
        
        Args:
            user_id: Compromised user ID
            reason: Reason for suspicion
        """
        from designs.models import CustomUser
        
        try:
            user = CustomUser.objects.get(id=user_id)
            
            # Revoke all active tokens
            from rest_framework.authtoken.models import Token
            Token.objects.filter(user=user).delete()
            
            # Revoke all API keys
            from designs.models import APIKey
            APIKey.objects.filter(user=user, is_active=True).update(is_active=False)
            
            # Alert security team and user
            SecurityMonitor.alert_security_team(
                'account_compromise',
                {
                    'user_id': user_id,
                    'username': user.username,
                    'reason': reason,
                    'action_taken': 'All tokens and API keys revoked'
                },
                severity=SecurityMonitor.SEVERITY_CRITICAL
            )
            
            logger.critical(f"Account compromise handled for user {user_id}: {reason}")
            
        except CustomUser.DoesNotExist:
            logger.error(f"User {user_id} not found for compromise handling")
    
    @classmethod
    def handle_data_exfiltration(cls, user_id, details):
        """
        Handle suspected data exfiltration.
        
        Args:
            user_id: User ID
            details: Details of suspicious activity
        """
        # Lock account temporarily
        from designs.models import CustomUser
        
        try:
            user = CustomUser.objects.get(id=user_id)
            user.is_active = False
            user.save()
            
            # Alert security team
            SecurityMonitor.alert_security_team(
                'data_exfiltration',
                {
                    'user_id': user_id,
                    'username': user.username,
                    'details': details,
                    'action_taken': 'Account temporarily locked'
                },
                severity=SecurityMonitor.SEVERITY_CRITICAL
            )
            
            logger.critical(f"Data exfiltration suspected for user {user_id}")
            
        except CustomUser.DoesNotExist:
            logger.error(f"User {user_id} not found for exfiltration handling")


class SecurityDashboard:
    """
    Generate data for security dashboard.
    """
    
    @classmethod
    def get_dashboard_data(cls):
        """
        Get all data for security dashboard.
        
        Returns:
            Dictionary with dashboard data
        """
        return {
            'threat_summary': SecurityMonitor.get_threat_summary(),
            'recent_events': SecurityMonitor.get_security_events(limit=20),
            'security_report': SecurityMetrics.generate_security_report(),
            'blocked_ips': SecurityMonitor.get_blocked_ips(),
            'active_alerts': cache.get('security_alerts', []),
            'anomalies': SecurityMonitor.check_anomalies(),
        }
    
    @classmethod
    def get_real_time_stats(cls):
        """
        Get real-time security statistics.
        
        Returns:
            Dictionary with real-time stats
        """
        events = SecurityMonitor.get_security_events(limit=1000)
        
        # Events in last hour
        hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        recent_events = [e for e in events if e.get('timestamp', '') > hour_ago]
        
        return {
            'events_last_hour': len(recent_events),
            'critical_events_last_hour': len([e for e in recent_events if e.get('severity') == SecurityMonitor.SEVERITY_CRITICAL]),
            'failed_logins_last_hour': len([e for e in recent_events if e.get('event_type') == 'login_failed']),
            'attacks_last_hour': len([e for e in recent_events if 'attack' in e.get('event_type', '')]),
        }
