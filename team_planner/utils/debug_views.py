import json

from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer

from team_planner.users.models import User
from team_planner.utils.seeding import seed_demo_data


@csrf_exempt
def create_test_users(request):
    """Create test users in the same database context as the HTTP server"""
    if request.method == "POST":
        try:


            body = (
                json.loads(request.body or "{}")
                if request.content_type == "application/json"
                else {}
            )
            dept = body.get("department", "Operations")
            team = body.get("team", "A-Team")
            count = int(body.get("count", 12))
            prefix = body.get("prefix", "demo")
            password = body.get("password", "ComplexPassword123!")
            reset = bool(body.get("reset", False))
            create_admin = bool(body.get("create_admin", True))
            admin_username = body.get("admin_username", "admin")
            admin_password = body.get("admin_password", "AdminPassword123!")

            summary = seed_demo_data(
                dept_name=dept,
                team_name=team,
                count=count,
                prefix=prefix,
                password=password,
                reset=reset,
                create_admin=create_admin,
                admin_username=admin_username,
                admin_password=admin_password,
            )

            return JsonResponse(
                {
                    "success": True,
                    "department": summary.department,
                    "team": summary.team,
                    "team_id": summary.team_id,
                    "users_created_or_updated": summary.created + summary.updated,
                    "count_requested": summary.count,
                    "categories": summary.categories,
                    "usernames_preview": summary.usernames[:6],
                    "password": summary.password,
                    "admin": summary.admin_username,
                },
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return JsonResponse({"error": str(e), "success": False}, status=500)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def custom_auth_token(request):
    """Custom auth token endpoint for debugging"""
    if request.method == "POST":
        try:
            if request.content_type == "application/json":
                data = json.loads(request.body)
            else:
                data = dict(request.POST)


            # Check what database is being used


            # Check what users exist in the database
            all_users = User.objects.all()
            for _u in all_users:
                pass

            # Test direct authentication first
            username = data.get("username")
            password = data.get("password")

            auth_user = authenticate(username=username, password=password)

            if auth_user:
                pass
            else:
                pass

            # Check if user exists
            try:
                user = User.objects.get(username=username)
                if password:
                    pass
            except User.DoesNotExist:
                pass

            # Now test the serializer
            serializer = AuthTokenSerializer(data=data)

            if serializer.is_valid():
                user = serializer.validated_data["user"]
                token, created = Token.objects.get_or_create(user=user)
                return JsonResponse({"token": token.key, "success": True})
            return JsonResponse(
                {"errors": serializer.errors, "success": False}, status=400,
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return JsonResponse({"error": str(e), "success": False}, status=500)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)
