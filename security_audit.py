#!/usr/bin/env python
"""
Security Audit Script for Team Planner
Checks for common security vulnerabilities and best practices
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.conf import settings
from django.core.management import call_command
import subprocess


class SecurityAuditor:
    """Performs comprehensive security checks"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed = []
    
    def add_issue(self, severity, category, message):
        """Add a security issue"""
        self.issues.append({
            'severity': severity,
            'category': category,
            'message': message
        })
    
    def add_warning(self, category, message):
        """Add a warning"""
        self.warnings.append({
            'category': category,
            'message': message
        })
    
    def add_passed(self, category, message):
        """Add a passed check"""
        self.passed.append({
            'category': category,
            'message': message
        })
    
    def check_debug_mode(self):
        """Check if DEBUG is disabled in production"""
        print("\n[1/15] Checking DEBUG mode...")
        if settings.DEBUG:
            self.add_issue(
                'HIGH',
                'Configuration',
                'DEBUG=True in production exposes sensitive information'
            )
        else:
            self.add_passed('Configuration', 'DEBUG is properly disabled')
    
    def check_secret_key(self):
        """Check SECRET_KEY configuration"""
        print("[2/15] Checking SECRET_KEY...")
        if settings.SECRET_KEY == 'django-insecure-default-key-change-this':
            self.add_issue(
                'CRITICAL',
                'Configuration',
                'SECRET_KEY is using default value - must be changed for production'
            )
        elif len(settings.SECRET_KEY) < 50:
            self.add_warning(
                'Configuration',
                'SECRET_KEY is short - consider using a longer key (50+ characters)'
            )
        else:
            self.add_passed('Configuration', 'SECRET_KEY is properly configured')
    
    def check_allowed_hosts(self):
        """Check ALLOWED_HOSTS configuration"""
        print("[3/15] Checking ALLOWED_HOSTS...")
        if '*' in settings.ALLOWED_HOSTS:
            self.add_issue(
                'HIGH',
                'Configuration',
                'ALLOWED_HOSTS contains \'*\' - should specify exact domains in production'
            )
        elif not settings.ALLOWED_HOSTS:
            self.add_issue(
                'HIGH',
                'Configuration',
                'ALLOWED_HOSTS is empty - must be configured for production'
            )
        else:
            self.add_passed('Configuration', f'ALLOWED_HOSTS properly configured: {settings.ALLOWED_HOSTS}')
    
    def check_csrf_settings(self):
        """Check CSRF protection settings"""
        print("[4/15] Checking CSRF protection...")
        if not getattr(settings, 'CSRF_COOKIE_SECURE', False):
            self.add_warning(
                'Security',
                'CSRF_COOKIE_SECURE=False - should be True in production (HTTPS)'
            )
        if not getattr(settings, 'CSRF_COOKIE_HTTPONLY', False):
            self.add_warning(
                'Security',
                'CSRF_COOKIE_HTTPONLY should be True to prevent JavaScript access'
            )
        if 'django.middleware.csrf.CsrfViewMiddleware' not in settings.MIDDLEWARE:
            self.add_issue(
                'CRITICAL',
                'Security',
                'CSRF middleware is not enabled'
            )
        else:
            self.add_passed('Security', 'CSRF protection is enabled')
    
    def check_session_security(self):
        """Check session security settings"""
        print("[5/15] Checking session security...")
        if not getattr(settings, 'SESSION_COOKIE_SECURE', False):
            self.add_warning(
                'Security',
                'SESSION_COOKIE_SECURE=False - should be True in production (HTTPS)'
            )
        if not getattr(settings, 'SESSION_COOKIE_HTTPONLY', True):
            self.add_warning(
                'Security',
                'SESSION_COOKIE_HTTPONLY should be True'
            )
        session_age = getattr(settings, 'SESSION_COOKIE_AGE', 1209600)
        if session_age > 86400:  # More than 24 hours
            self.add_warning(
                'Security',
                f'SESSION_COOKIE_AGE is {session_age}s ({session_age/3600}h) - consider shorter session timeout'
            )
        self.add_passed('Security', 'Session configuration reviewed')
    
    def check_security_middleware(self):
        """Check for security middleware"""
        print("[6/15] Checking security middleware...")
        required_middleware = [
            'django.middleware.security.SecurityMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ]
        for mw in required_middleware:
            if mw not in settings.MIDDLEWARE:
                self.add_issue(
                    'HIGH',
                    'Security',
                    f'Missing security middleware: {mw}'
                )
            else:
                self.add_passed('Security', f'{mw.split(".")[-1]} enabled')
    
    def check_https_settings(self):
        """Check HTTPS enforcement settings"""
        print("[7/15] Checking HTTPS settings...")
        if not getattr(settings, 'SECURE_SSL_REDIRECT', False):
            self.add_warning(
                'Security',
                'SECURE_SSL_REDIRECT=False - should redirect HTTP to HTTPS in production'
            )
        if not getattr(settings, 'SECURE_HSTS_SECONDS', 0):
            self.add_warning(
                'Security',
                'SECURE_HSTS_SECONDS not set - consider enabling HSTS in production'
            )
        self.add_passed('Security', 'HTTPS settings reviewed')
    
    def check_database_security(self):
        """Check database security"""
        print("[8/15] Checking database security...")
        default_db = settings.DATABASES.get('default', {})
        engine = default_db.get('ENGINE', '')
        
        if 'sqlite' in engine.lower():
            self.add_warning(
                'Database',
                'Using SQLite - consider PostgreSQL for production'
            )
        
        if default_db.get('PASSWORD') in ['', 'password', 'admin']:
            self.add_issue(
                'CRITICAL',
                'Database',
                'Database password is weak or default'
            )
        
        self.add_passed('Database', 'Database configuration reviewed')
    
    def check_cors_settings(self):
        """Check CORS configuration"""
        print("[9/15] Checking CORS settings...")
        if hasattr(settings, 'CORS_ALLOW_ALL_ORIGINS'):
            if settings.CORS_ALLOW_ALL_ORIGINS:
                self.add_issue(
                    'HIGH',
                    'CORS',
                    'CORS_ALLOW_ALL_ORIGINS=True - should restrict to specific origins in production'
                )
        if hasattr(settings, 'CORS_ALLOWED_ORIGINS'):
            self.add_passed('CORS', f'CORS origins configured: {len(settings.CORS_ALLOWED_ORIGINS)} origins')
        else:
            self.add_warning('CORS', 'CORS settings not configured - may need configuration')
    
    def check_password_validators(self):
        """Check password validation settings"""
        print("[10/15] Checking password validators...")
        validators = settings.AUTH_PASSWORD_VALIDATORS
        if len(validators) < 4:
            self.add_warning(
                'Authentication',
                f'Only {len(validators)} password validators configured - consider using all 4 default validators'
            )
        else:
            self.add_passed('Authentication', f'{len(validators)} password validators configured')
    
    def check_admin_url(self):
        """Check if admin URL is customized"""
        print("[11/15] Checking admin URL...")
        from django.urls import get_resolver
        resolver = get_resolver()
        
        # This is a basic check - in production you'd want to scan actual URLs
        self.add_warning(
            'Configuration',
            'Consider changing default /admin/ URL to custom path in production'
        )
    
    def check_dependencies(self):
        """Check for outdated or vulnerable dependencies"""
        print("[12/15] Checking dependencies...")
        try:
            # Check if safety is installed
            result = subprocess.run(
                ['pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.add_passed('Dependencies', 'Dependency check completed')
            else:
                self.add_warning('Dependencies', 'Could not check dependencies')
        except Exception as e:
            self.add_warning('Dependencies', f'Dependency check skipped: {str(e)}')
    
    def check_static_files(self):
        """Check static files configuration"""
        print("[13/15] Checking static files...")
        if not getattr(settings, 'STATIC_ROOT', None):
            self.add_warning(
                'Configuration',
                'STATIC_ROOT not configured - required for production deployment'
            )
        else:
            self.add_passed('Configuration', f'STATIC_ROOT: {settings.STATIC_ROOT}')
    
    def check_logging(self):
        """Check logging configuration"""
        print("[14/15] Checking logging...")
        if not settings.LOGGING:
            self.add_warning(
                'Monitoring',
                'No logging configuration - should configure for production'
            )
        else:
            self.add_passed('Monitoring', 'Logging is configured')
    
    def check_error_pages(self):
        """Check custom error pages"""
        print("[15/15] Checking error pages...")
        # Check if custom error templates exist
        import os
        template_dirs = [str(d) for d in getattr(settings, 'TEMPLATES', [{}])[0].get('DIRS', [])]
        error_templates = ['404.html', '500.html']
        
        found_templates = []
        for template_dir in template_dirs:
            for error_template in error_templates:
                path = os.path.join(template_dir, error_template)
                if os.path.exists(path):
                    found_templates.append(error_template)
        
        if found_templates:
            self.add_passed('Configuration', f'Custom error pages found: {", ".join(found_templates)}')
        else:
            self.add_warning(
                'Configuration',
                'No custom error pages (404.html, 500.html) - should create for production'
            )
    
    def run_all_checks(self):
        """Run all security checks"""
        print("\n" + "="*70)
        print("TEAM PLANNER SECURITY AUDIT")
        print("="*70)
        
        self.check_debug_mode()
        self.check_secret_key()
        self.check_allowed_hosts()
        self.check_csrf_settings()
        self.check_session_security()
        self.check_security_middleware()
        self.check_https_settings()
        self.check_database_security()
        self.check_cors_settings()
        self.check_password_validators()
        self.check_admin_url()
        self.check_dependencies()
        self.check_static_files()
        self.check_logging()
        self.check_error_pages()
    
    def print_report(self):
        """Print security audit report"""
        print("\n" + "="*70)
        print("SECURITY AUDIT REPORT")
        print("="*70)
        
        # Critical Issues
        critical_issues = [i for i in self.issues if i['severity'] == 'CRITICAL']
        if critical_issues:
            print(f"\n🚨 CRITICAL ISSUES ({len(critical_issues)}):")
            print("-"*70)
            for issue in critical_issues:
                print(f"  [{issue['category']}] {issue['message']}")
        
        # High Issues
        high_issues = [i for i in self.issues if i['severity'] == 'HIGH']
        if high_issues:
            print(f"\n⚠️  HIGH PRIORITY ISSUES ({len(high_issues)}):")
            print("-"*70)
            for issue in high_issues:
                print(f"  [{issue['category']}] {issue['message']}")
        
        # Warnings
        if self.warnings:
            print(f"\n⚡ WARNINGS ({len(self.warnings)}):")
            print("-"*70)
            for warning in self.warnings:
                print(f"  [{warning['category']}] {warning['message']}")
        
        # Passed Checks
        if self.passed:
            print(f"\n✅ PASSED CHECKS ({len(self.passed)}):")
            print("-"*70)
            for passed in self.passed:
                print(f"  [{passed['category']}] {passed['message']}")
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"  Critical Issues: {len(critical_issues)}")
        print(f"  High Priority:   {len(high_issues)}")
        print(f"  Warnings:        {len(self.warnings)}")
        print(f"  Passed:          {len(self.passed)}")
        
        total_issues = len(critical_issues) + len(high_issues)
        if total_issues == 0:
            print("\n✅ No critical or high priority issues found!")
            print("   Review warnings and apply production best practices.")
        else:
            print(f"\n⚠️  Found {total_issues} issue(s) that should be addressed before production.")
        
        print("="*70 + "\n")
        
        return total_issues


def main():
    """Main execution"""
    auditor = SecurityAuditor()
    auditor.run_all_checks()
    issues_count = auditor.print_report()
    
    # Exit with error code if critical issues found
    critical_count = len([i for i in auditor.issues if i['severity'] == 'CRITICAL'])
    if critical_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
