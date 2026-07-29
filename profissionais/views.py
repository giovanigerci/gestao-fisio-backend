from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .serializers import RegistroSerializer, ProfissionalSerializer

class RegistroView(generics.CreateAPIView):
    serializer_class = RegistroSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profissional = serializer.save()

        resposta = ProfissionalSerializer(profissional)
        return Response(resposta.data, status=status.HTTP_201_CREATED)