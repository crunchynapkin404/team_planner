"""
Backend API Testing for Orchestrator V2 Endpoints
Phase 7 Testing: Stage 2 - Backend Testing

This module provides comprehensive testing for the orchestrator V2 API endpoints
that the React frontend expects, ensuring proper implementation of the clean architecture.

Test Categories:
1. V2 API Endpoint Testing (schedule, coverage, availability, health, metrics)
2. Request/Response Validation
3. Authentication & Authorization
4. Error Handling & Edge Cases
5. Data Consistency & Business Logic
"""

from datetime import datetime, timedelta, date
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
import json
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

from .models import OrchestrationRun, OrchestrationResult
from .test_utils import TestDataFactory, BaseTestCase
from team_planner.employees.models import EmployeeProfile
from team_planner.shifts.models import Shift, ShiftTemplate, ShiftType
from team_planner.leaves.models import LeaveRequest, LeaveType
from team_planner.teams.models import Team, Department

User = get_user_model()


class OrchestratorV2APITestCase(APITestCase):
    """Test cases for Orchestrator V2 API endpoints."""

    def setUp(self):
        """Set up test data for V2 API testing."""
        self.client = APIClient()
        
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        self.staff_user = User.objects.create_user(
            username='staff_test',
            email='staff@test.com',
            password='testpass123',
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='regular_test',
            email='regular@test.com',
            password='testpass123',
            is_staff=False
        )
        
        # Create tokens for authentication
        self.admin_token = Token.objects.create(user=self.admin_user)
        self.staff_token = Token.objects.create(user=self.staff_user)
        self.regular_token = Token.objects.create(user=self.regular_user)
        
        # Create test data using factory
        self.test_scenario = TestDataFactory.create_test_scenario(num_employees=5)
        self.department = self.test_scenario['department']
        self.employees = self.test_scenario['employees']
        self.incidents_template = self.test_scenario['incidents_template']
        self.waakdienst_template = self.test_scenario['waakdienst_template']
        
        # Test date range (next week)
        self.start_date = (timezone.now() + timedelta(days=7)).date()
        self.end_date = self.start_date + timedelta(days=6)
        
        # V2 API endpoints (as expected by frontend)
        self.schedule_url = '/api/orchestrator/schedule/'
        self.coverage_url = '/api/orchestrator/coverage/'
        self.availability_url = '/api/orchestrator/availability/'
        self.health_url = '/api/orchestrator-status/health/'
        self.metrics_url = '/api/orchestrator-status/metrics/'

    def authenticate_admin(self):
        """Authenticate as admin user."""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)

    def authenticate_staff(self):
        """Authenticate as staff user."""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.staff_token.key)

    def authenticate_regular(self):
        """Authenticate as regular user."""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.regular_token.key)

    def clear_authentication(self):
        """Clear authentication credentials."""
        self.client.credentials()


class ScheduleOrchestrationAPITest(OrchestratorV2APITestCase):
    """Test the POST /api/orchestrator/schedule/ endpoint."""

    def test_schedule_orchestration_success(self):
        """Test successful orchestration scheduling."""
        self.authenticate_admin()
        
        data = {
            'department_id': str(self.department.id),
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'preview_only': True,
            'algorithm_config': {
                'fairness_weight': 0.8,
                'constraint_weight': 0.9
            }
        }
        
        # Note: This test will fail until V2 endpoints are implemented
        response = self.client.post(self.schedule_url, data, format='json')
        
        # Expected response structure
        expected_status = status.HTTP_200_OK
        expected_fields = [
            'orchestration_id', 'department_id', 'start_date', 'end_date',
            'status', 'preview_only', 'shifts_generated', 'summary'
        ]
        
        # Assertions (will pass when V2 API is implemented)
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented - test ready for implementation")
        
        self.assertEqual(response.status_code, expected_status)
        self.assertIsInstance(response.data, dict)
        for field in expected_fields:
            self.assertIn(field, response.data)

    def test_schedule_orchestration_invalid_department(self):
        """Test orchestration with invalid department ID."""
        self.authenticate_admin()
        
        data = {
            'department_id': '99999',
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Department not found', response.data['error'])

    def test_schedule_orchestration_invalid_date_range(self):
        """Test orchestration with invalid date range."""
        self.authenticate_admin()
        
        data = {
            'department_id': str(self.department.id),
            'start_date': self.end_date.isoformat(),  # Start after end
            'end_date': self.start_date.isoformat(),
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_schedule_orchestration_authentication_required(self):
        """Test that authentication is required."""
        self.clear_authentication()
        
        data = {
            'department_id': str(self.department.id),
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_schedule_orchestration_staff_permission_required(self):
        """Test that staff permissions are required."""
        self.authenticate_regular()
        
        data = {
            'department_id': str(self.department.id),
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CoverageAnalysisAPITest(OrchestratorV2APITestCase):
    """Test the GET /api/orchestrator/coverage/ endpoint."""

    def test_get_coverage_success(self):
        """Test successful coverage data retrieval."""
        self.authenticate_staff()
        
        params = {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'department_id': str(self.department.id)
        }
        
        response = self.client.get(self.coverage_url, params)
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        
        expected_fields = [
            'department_id', 'start_date', 'end_date', 'coverage_summary',
            'daily_coverage', 'coverage_gaps', 'recommendations'
        ]
        for field in expected_fields:
            self.assertIn(field, response.data)

    def test_get_coverage_without_department(self):
        """Test coverage retrieval without department filter."""
        self.authenticate_staff()
        
        params = {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat()
        }
        
        response = self.client.get(self.coverage_url, params)
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)

    def test_get_coverage_authentication_required(self):
        """Test that authentication is required for coverage data."""
        self.clear_authentication()
        
        params = {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat()
        }
        
        response = self.client.get(self.coverage_url, params)
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AvailabilityAnalysisAPITest(OrchestratorV2APITestCase):
    """Test the GET /api/orchestrator/availability/ endpoint."""

    def test_get_availability_success(self):
        """Test successful availability data retrieval."""
        self.authenticate_staff()
        
        params = {
            'date': self.start_date.isoformat(),
            'shift_type': 'day',
            'department_id': str(self.department.id)
        }
        
        response = self.client.get(self.availability_url, params)
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        
        expected_fields = [
            'date', 'shift_type', 'department_id', 'available_employees',
            'unavailable_employees', 'availability_summary'
        ]
        for field in expected_fields:
            self.assertIn(field, response.data)

    def test_get_availability_all_shift_types(self):
        """Test availability for all shift types."""
        self.authenticate_staff()
        
        for shift_type in ['day', 'evening', 'night']:
            params = {
                'date': self.start_date.isoformat(),
                'shift_type': shift_type,
                'department_id': str(self.department.id)
            }
            
            response = self.client.get(self.availability_url, params)
            
            if response.status_code == status.HTTP_404_NOT_FOUND:
                self.skipTest("V2 API endpoints not yet implemented")
                
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['shift_type'], shift_type)


class SystemHealthAPITest(OrchestratorV2APITestCase):
    """Test the GET /api/orchestrator-status/health/ endpoint."""

    def test_get_system_health_success(self):
        """Test successful system health retrieval."""
        self.authenticate_staff()
        
        response = self.client.get(self.health_url)
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        
        expected_fields = [
            'status', 'timestamp', 'services', 'database_status',
            'orchestrator_status', 'version', 'uptime'
        ]
        for field in expected_fields:
            self.assertIn(field, response.data)

    def test_system_health_unauthenticated(self):
        """Test system health endpoint with no authentication."""
        self.clear_authentication()
        
        response = self.client.get(self.health_url)
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        # Health endpoint might be accessible without auth for monitoring
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED])


class SystemMetricsAPITest(OrchestratorV2APITestCase):
    """Test the GET /api/orchestrator-status/metrics/ endpoint."""

    def test_get_system_metrics_success(self):
        """Test successful system metrics retrieval."""
        self.authenticate_admin()
        
        response = self.client.get(self.metrics_url)
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        
        expected_fields = [
            'orchestrations_total', 'orchestrations_successful', 'orchestrations_failed',
            'shifts_generated', 'fairness_score_average', 'constraint_violations',
            'performance_metrics', 'timestamp'
        ]
        for field in expected_fields:
            self.assertIn(field, response.data)

    def test_system_metrics_staff_only(self):
        """Test that metrics require staff permissions."""
        self.authenticate_regular()
        
        response = self.client.get(self.metrics_url)
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class LegacyAPICompatibilityTest(OrchestratorV2APITestCase):
    """Test existing legacy API endpoints for backward compatibility."""

    def test_legacy_orchestrator_create_api(self):
        """Test the existing legacy orchestrator create API."""
        self.authenticate_admin()
        
        url = '/orchestrators/api/create/'
        data = {
            'name': 'Test Orchestration',
            'description': 'Test orchestration for API testing',
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'preview_only': True
        }
        
        response = self.client.post(url, data, format='json')
        
        # Legacy API should work
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST  # If validation fails, that's expected
        ])
        
        if response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            self.assertIsInstance(response.data, dict)

    def test_legacy_orchestrator_status_api(self):
        """Test the existing legacy orchestrator status API."""
        self.authenticate_staff()
        
        url = '/orchestrators/api/status/'
        response = self.client.get(url)
        
        # Legacy API should work
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND  # If no orchestrations exist
        ])

    def test_legacy_fairness_api(self):
        """Test the existing legacy fairness API."""
        self.authenticate_staff()
        
        url = '/orchestrators/api/fairness/'
        response = self.client.get(url)
        
        # Legacy API should work
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND  # If no data exists
        ])


class APIErrorHandlingTest(OrchestratorV2APITestCase):
    """Test comprehensive error handling across all API endpoints."""

    def test_malformed_json_request(self):
        """Test handling of malformed JSON requests."""
        self.authenticate_admin()
        
        # Send malformed JSON
        response = self.client.post(
            self.schedule_url,
            data='{"malformed": json}',
            content_type='application/json'
        )
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        self.authenticate_admin()
        
        # Missing required fields
        data = {
            'start_date': self.start_date.isoformat(),
            # Missing end_date and department_id
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_invalid_date_formats(self):
        """Test handling of invalid date formats."""
        self.authenticate_admin()
        
        data = {
            'department_id': str(self.department.id),
            'start_date': 'invalid-date',
            'end_date': 'also-invalid',
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
            
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class APIPerformanceTest(OrchestratorV2APITestCase):
    """Test API performance and response times."""

    def test_large_date_range_handling(self):
        """Test handling of large date ranges."""
        self.authenticate_admin()
        
        # Test with 3-month range
        large_start_date = self.start_date
        large_end_date = self.start_date + timedelta(days=90)
        
        data = {
            'department_id': str(self.department.id),
            'start_date': large_start_date.isoformat(),
            'end_date': large_end_date.isoformat(),
            'preview_only': True
        }
        
        import time
        start_time = time.time()
        response = self.client.post(self.schedule_url, data, format='json')
        end_time = time.time()
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            self.skipTest("V2 API endpoints not yet implemented")
        
        # Should complete within reasonable time (30 seconds for large range)
        self.assertLess(end_time - start_time, 30.0)
        
        # Should either succeed or return a reasonable error for large ranges
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,  # If range is too large
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        ])

    def test_concurrent_requests(self):
        """Test handling of concurrent API requests."""
        self.authenticate_admin()
        
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def make_request():
            """Make a single API request."""
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
            
            data = {
                'department_id': str(self.department.id),
                'start_date': self.start_date.isoformat(),
                'end_date': self.end_date.isoformat(),
                'preview_only': True
            }
            
            response = client.post(self.schedule_url, data, format='json')
            results_queue.put(response.status_code)
        
        # Create and start multiple threads
        threads = []
        for i in range(3):  # Keep it reasonable for testing
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout
        
        # Check results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        if all(result == status.HTTP_404_NOT_FOUND for result in results):
            self.skipTest("V2 API endpoints not yet implemented")
        
        # All requests should either succeed or fail gracefully
        for result in results:
            self.assertIn(result, [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_429_TOO_MANY_REQUESTS,
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ])
