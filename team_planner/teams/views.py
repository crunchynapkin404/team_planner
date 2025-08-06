from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Team

@api_view(['GET'])
def teams_list_api(request):
    """API endpoint to list all teams."""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    teams = Team.objects.all().values('id', 'name')
    return Response(list(teams))
