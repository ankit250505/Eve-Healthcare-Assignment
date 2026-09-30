from rest_framework import generics, permissions

from accounts.serializers import SignupSerializer, UserSerializer


class SignupView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = SignupSerializer


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
