#!/usr/bin/env python
"""
Test script for the orchestrator algorithms.
"""
import os
import sys
import django

# Setup Django
sys.path.append('/home/bart/VsCode/TeamPlanner/team_planner')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from datetime import datetime, timedelta
from team_planner.orchestrators.algorithms import ShiftOrchestrator, FairnessCalculator

def test_orchestrator():
    """Test the orchestrator algorithm."""
    print("🚀 Testing ShiftOrchestrator...")
    
    # Test with a simple 4-week period
    start_date = datetime(2025, 8, 11)  # Monday 
    end_date = datetime(2025, 9, 5)     # End of 4th week
    
    print(f"📅 Planning period: {start_date.date()} to {end_date.date()}")
    
    orchestrator = ShiftOrchestrator(start_date, end_date)
    
    # Test preview mode (doesn't save to database)
    print("🔍 Running preview...")
    try:
        result = orchestrator.preview_schedule()
        
        print(f"✅ Total shifts: {result['total_shifts']}")
        print(f"🔧 Incident shifts: {result['incident_shifts']}")
        print(f"📞 Waakdienst shifts: {result['waakdienst_shifts']}")
        print(f"👥 Employees assigned: {result['employees_assigned']}")
        print(f"⚖️ Average fairness: {result['average_fairness']:.2f}")
        
        print("\\n🎉 Preview completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during orchestration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_fairness_calculator():
    """Test the fairness calculator."""
    print("\\n📊 Testing FairnessCalculator...")
    
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 12, 31)
    
    calculator = FairnessCalculator(start_date, end_date)
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get active users
        users = User.objects.filter(is_active=True)[:5]  # Limit to 5 for testing
        
        assignments = calculator.calculate_current_assignments(list(users))
        fairness_scores = calculator.calculate_fairness_score(assignments)
        
        print(f"✅ Calculated assignments for {len(assignments)} employees")
        print(f"✅ Calculated fairness scores for {len(fairness_scores)} employees")
        
        print("\\n🎉 Fairness calculator test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error in fairness calculator: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Phase 2 Orchestrator Algorithm Tests")
    print("=" * 50)
    
    # Test 1: Orchestrator
    success1 = test_orchestrator()
    
    # Test 2: Fairness Calculator
    success2 = test_fairness_calculator()
    
    print("\\n" + "=" * 50)
    if success1 and success2:
        print("🎉 All tests passed! Phase 2 orchestrator is working.")
    else:
        print("❌ Some tests failed. Check the errors above.")
