from django.urls import path
from . import views

app_name = 'orchestrators'

urlpatterns = [
    # Dashboard
    path('', views.orchestrator_dashboard, name='dashboard'),
    
    # Orchestration management
    path('create/', views.create_orchestration, name='create'),
    path('detail/<int:pk>/', views.orchestration_detail, name='detail'),
    path('<int:pk>/', views.orchestration_detail, name='run_detail'),  # Keep for compatibility
    
    # Preview system (placeholder views for now)
    # path('preview/', views.preview_view, name='preview'),
    # path('apply-preview/', views.apply_preview, name='apply_preview'),
    
    # Fairness dashboard (placeholder for now)
    # path('fairness/', views.fairness_dashboard, name='fairness'),
    # path('api/fairness/', views.fairness_api, name='fairness_api'),
]
