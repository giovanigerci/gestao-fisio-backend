from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    authentication_classes = []  
    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request):
        return Response({'status': 'ok'}, headers={'Cache-Control': 'no-store'})
