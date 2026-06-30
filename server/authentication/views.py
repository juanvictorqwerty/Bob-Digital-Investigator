from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.utils import timezone

from .models import CustomUser
from .serializers import UserRegistrationSerializer,UserLoginSerializer

class UserRegistrationView(generics.CreateAPIView):
    """Handles user sign-up and returns a fresh token."""
    queryset = CustomUser.objects.all()
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        # 1. Use the serializer to validate data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 2. Save the user (hashes password automatically via manager)
        user = serializer.save()
        
        # 3. Create or get the token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'email': user.email,
        }, status=status.HTTP_201_CREATED)


class UserLoginView(generics.GenericAPIView):
    """Handles user login, authenticates credentials, and updates/returns a token."""
    serializer_class = UserLoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({'error': 'Please provide both email and password'}, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            if not created:
                token.created = timezone.now()
                token.save()
            return Response({
                'token': token.key,
                'email': user.email
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
