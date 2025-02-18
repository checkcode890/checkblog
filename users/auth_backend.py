from django.contrib.auth.backends import BaseBackend
from django.db import connection
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password

class CustomAuthBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, password 
                FROM auth_user 
                WHERE email = %s
            """, [email])
            user_data = cursor.fetchone()
            if user_data:
                user_id, username, hashed_password = user_data
                if check_password(password, hashed_password):
                    user = User(id=user_id, username=username)
                    return user
        return None

    def get_user(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, username FROM auth_user WHERE id = %s", [user_id])
            user_data = cursor.fetchone()
            if user_data:
                user_id, username = user_data
                return User(id=user_id, username=username)
        return None