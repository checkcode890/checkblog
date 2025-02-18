from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm


def logout_view(request):
    logout(request)
    return render(request, 'users/logout.html')

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password1')
            hashed_password = make_password(password)
            date_joined = timezone.now()
            try:
                with connection.cursor() as cursor:
                    # Insert into auth_user
                    cursor.execute(
                        """
                        INSERT INTO auth_user 
                        (username, email, password, date_joined, is_active, is_staff, is_superuser)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        [username, email, hashed_password, date_joined, True, False, False]
                    )
                    user_id = cursor.fetchone()[0]
                    # Insert into users_profile with default image
                    cursor.execute(
                        "INSERT INTO users_profile (user_id) VALUES (%s)",
                        [user_id]
                    )
                messages.success(request, "Account created! Please log in.")
                return redirect('login')
            except Exception as e:
                messages.error(request, f"Error: {e}")
                return redirect('register')  # Redirect back to avoid resubmission
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST)
        p_form = ProfileUpdateForm(request.POST, request.FILES)
        if u_form.is_valid() and p_form.is_valid():
            username = u_form.cleaned_data.get('username')
            email = u_form.cleaned_data.get('email')
            image = request.FILES.get('image')
            try:
                with connection.cursor() as cursor:
                    # Update auth_user
                    cursor.execute(
                        """
                        UPDATE auth_user
                        SET username = %s, email = %s
                        WHERE id = %s
                        """,
                        [username, email, request.user.id]
                    )
                    if image:
                        # Get profile ID to generate unique filename
                        cursor.execute(
                            "SELECT id FROM users_profile WHERE user_id = %s",
                            [request.user.id]
                        )
                        profile_id = cursor.fetchone()[0]
                        
                        # Generate unique filename with profile ID and timestamp
                        import os
                        from django.conf import settings
                        from django.utils import timezone
                        
                        file_ext = os.path.splitext(image.name)[1].lower()
                        timestamp = int(timezone.now().timestamp())
                        new_filename = f"profile_{profile_id}_{timestamp}{file_ext}"
                        relative_path = os.path.join('profile_pics', new_filename)
                        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                        
                        # Ensure directory exists
                        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
                        
                        # Save the image file
                        with open(absolute_path, 'wb+') as f:
                            for chunk in image.chunks():
                                f.write(chunk)
                        
                        # Update the profile with the new image path
                        cursor.execute(
                            "UPDATE users_profile SET image = %s WHERE user_id = %s",
                            [relative_path, request.user.id]
                        )
                messages.success(request, "Profile updated!")
                return redirect('profile')
            except Exception as e:
                messages.error(request, f"Error: {e}")
    else:
        # Fetch user and profile data (existing code)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username, email FROM auth_user WHERE id = %s",
                [request.user.id]
            )
            user_data = cursor.fetchone()
            cursor.execute(
                "SELECT image FROM users_profile WHERE user_id = %s",
                [request.user.id]
            )
            profile_data = cursor.fetchone()
        
        initial_user = {
            'username': user_data[0],
            'email': user_data[1],
        }
        initial_profile = {'image': profile_data[0] if profile_data else 'profile_pics/default.jpg'}
        
        u_form = UserUpdateForm(initial=initial_user)
        p_form = ProfileUpdateForm(initial=initial_profile)
    
    return render(request, 'users/profile.html', {'u_form': u_form, 'p_form': p_form})