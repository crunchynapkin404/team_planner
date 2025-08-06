from django.urls import path
from . import views

app_name = 'teams'

urlpatterns = [
    path('', views.teams_list_api, name='teams_list_api'),
]
