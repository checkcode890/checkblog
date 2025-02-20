import os
from django.shortcuts import render, redirect
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.http import Http404, JsonResponse, HttpResponseNotAllowed
from django.conf import settings
from django.utils import timezone

# PostForm with a title, optional image field, and visibility option
class PostForm(forms.Form):
    title = forms.CharField(max_length=200)
    image = forms.ImageField(required=False)
    visibility = forms.ChoiceField(choices=[('public', 'Public'), ('friends', 'Friends Only')], initial='public')

def home(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT bp.id, bp.title, bp.image, bp.date_posted, bp.visibility,
                   au.id, au.username, COALESCE(up.image, 'profile_pics/default.jpg'),
                   (SELECT COUNT(*) FROM post_likes WHERE post_id = bp.id) AS like_count,
                   (SELECT COUNT(*) FROM post_comments WHERE post_id = bp.id) AS comment_count
            FROM blog_post bp
            JOIN auth_user au ON bp.author_id = au.id
            LEFT JOIN users_profile up ON au.id = up.user_id
            LEFT JOIN friends f ON 
                (f.user1_id = %s AND f.user2_id = au.id) OR 
                (f.user1_id = au.id AND f.user2_id = %s)
            WHERE bp.visibility = 'public' OR 
                  (bp.visibility = 'friends' AND (bp.author_id = %s OR f.status = 'accepted'))
            ORDER BY bp.date_posted DESC
        """, [request.user.id, request.user.id, request.user.id])
        posts = cursor.fetchall()

    context = {
        'posts': [
            {
                'id': row[0],
                'title': row[1],
                'image': row[2],
                'date_posted': row[3],
                'visibility': row[4],
                'author': {
                    'id': row[5],
                    'username': row[6],
                    'image': row[7],
                },
                'like_count': row[8],
                'comment_count': row[9],
            } for row in posts
        ]
    }
    return render(request, 'blog/home.html', context)

def about(request):
    return render(request, "blog/about.html")

def user_posts(request, username):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT bp.id, bp.title, bp.image, bp.date_posted, bp.visibility,
                   au.username, COALESCE(up.image, 'profile_pics/default.jpg'),
                   (SELECT COUNT(*) FROM post_likes WHERE post_id = bp.id) AS like_count,
                   (SELECT COUNT(*) FROM post_comments WHERE post_id = bp.id) AS comment_count
            FROM blog_post bp
            JOIN auth_user au ON bp.author_id = au.id
            LEFT JOIN users_profile up ON au.id = up.user_id
            WHERE au.username = %s AND (
                  bp.visibility = 'public' OR 
                  (bp.visibility = 'friends' AND (bp.author_id = %s OR EXISTS (
                      SELECT 1 FROM friends f WHERE 
                      ((f.user1_id = %s AND f.user2_id = au.id) OR 
                       (f.user1_id = au.id AND f.user2_id = %s)) AND 
                      f.status = 'accepted'
                  )))
            )
            ORDER BY bp.date_posted DESC
        """, [username, request.user.id, request.user.id, request.user.id])
        rows = cursor.fetchall()

    posts = [{
        'id': row[0],
        'title': row[1],
        'image': row[2],
        'date_posted': row[3],
        'visibility': row[4],
        'author': {
            'username': row[5],
            'image': row[6],
        },
        'like_count': row[7],
        'comment_count': row[8],
    } for row in rows]

    return render(request, 'blog/user_posts.html', {'posts': posts, 'username': username})

def post_detail(request, post_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT bp.id, bp.title, bp.image, bp.date_posted, bp.visibility, bp.author_id,
                   au.username, COALESCE(up.image, 'profile_pics/default.jpg'),
                   (SELECT COUNT(*) FROM post_likes WHERE post_id = bp.id) AS like_count
            FROM blog_post bp
            JOIN auth_user au ON bp.author_id = au.id
            LEFT JOIN users_profile up ON au.id = up.user_id
            WHERE bp.id = %s
        """, [post_id])
        post = cursor.fetchone()
        
        if not post:
            raise Http404("Post does not exist")

        cursor.execute("""
            SELECT pc.content, pc.created_at, au.username
            FROM post_comments pc
            JOIN auth_user au ON pc.user_id = au.id
            WHERE pc.post_id = %s
            ORDER BY pc.created_at DESC
        """, [post_id])
        comments = cursor.fetchall()

    context = {
        'post': {
            'id': post[0],
            'title': post[1],
            'image': post[2],
            'date_posted': post[3],
            'visibility': post[4],
            'author': {
                'id': post[5],
                'username': post[6],
                'image': post[7],
            },
            'like_count': post[8],
        },
        'comments': [
            {
                'content': row[0],
                'created_at': row[1],
                'username': row[2],
            } for row in comments
        ]
    }
    return render(request, 'blog/post_detail.html', context)

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.cleaned_data['title']
            visibility = form.cleaned_data['visibility']
            uploaded_image = request.FILES.get('image')
            relative_path = None

            if uploaded_image:
                file_ext = os.path.splitext(uploaded_image.name)[1].lower()
                timestamp = int(timezone.now().timestamp())
                new_filename = f"blog_{request.user.id}_{timestamp}{file_ext}"
                relative_path = os.path.join('blog_images', new_filename)
                absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)

                os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

                with open(absolute_path, 'wb+') as f:
                    for chunk in uploaded_image.chunks():
                        f.write(chunk)

            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO blog_post (title, image, author_id, visibility) VALUES (%s, %s, %s, %s) RETURNING id",
                    [title, relative_path, request.user.id, visibility]
                )
                post_id = cursor.fetchone()[0]
            messages.success(request, "Post created successfully!")
            return redirect('post-detail', post_id=post_id)
        else:
            messages.error(request, "Form is invalid. Please try again.")
    else:
        form = PostForm()
    return render(request, 'blog/post_form.html', {'form': form})

@login_required
def update_post(request, post_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT title, image FROM blog_post WHERE id = %s AND author_id = %s", [post_id, request.user.id])
        post = cursor.fetchone()
    if not post:
        raise Http404("Post not found or you are not authorized to edit it.")

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.cleaned_data['title']
            uploaded_image = request.FILES.get('image')
            relative_path = post[1]  # Use current image path by default

            if uploaded_image:
                file_ext = os.path.splitext(uploaded_image.name)[1].lower()
                timestamp = int(timezone.now().timestamp())
                new_filename = f"blog_{request.user.id}_{timestamp}{file_ext}"
                relative_path = os.path.join('blog_images', new_filename)
                absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)

                os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

                with open(absolute_path, 'wb+') as f:
                    for chunk in uploaded_image.chunks():
                        f.write(chunk)

            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE blog_post SET title = %s, image = %s WHERE id = %s AND author_id = %s",
                    [title, relative_path, post_id, request.user.id]
                )
            messages.success(request, "Post updated successfully!")
            return redirect('post-detail', post_id=post_id)
        else:
            messages.error(request, "Form is invalid. Please try again.")
    else:
        form = PostForm(initial={'title': post[0]})
    return render(request, 'blog/post_form.html', {'form': form})

@login_required
def search_users(request):
    query = request.GET.get('q', '')
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, username 
            FROM auth_user 
            WHERE username ILIKE %s AND id != %s
        """, [f'%{query}%', request.user.id])
        users = [{'id': row[0], 'username': row[1]} for row in cursor.fetchall()]
    return render(request, 'blog/search_users.html', {'users': users})

@login_required
def manage_friends(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        friend_id = request.POST.get('friend_id')
        
        if action == 'send_request':
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO friends (user1_id, user2_id)
                    VALUES (%s, %s)
                    ON CONFLICT (user1_id, user2_id) DO NOTHING
                """, [request.user.id, friend_id])
            messages.success(request, "Friend request sent!")
        
        elif action == 'accept_request':
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE friends SET status = 'accepted'
                    WHERE user1_id = %s AND user2_id = %s
                """, [friend_id, request.user.id])
            messages.success(request, "Friend request accepted!")
        
        elif action == 'decline_request':
            with connection.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM friends
                    WHERE (user1_id = %s AND user2_id = %s)
                    OR (user1_id = %s AND user2_id = %s)
                """, [friend_id, request.user.id, request.user.id, friend_id])
            messages.success(request, "Friend request declined!")
    
    return redirect('friends-list')

@login_required
def friends_list(request):
    with connection.cursor() as cursor:
        # Get accepted friends (exclude the current user)
        cursor.execute("""
            SELECT au.id, au.username, f.status 
            FROM friends f
            JOIN auth_user au ON 
                (f.user1_id = au.id OR f.user2_id = au.id)
            WHERE (f.user1_id = %s OR f.user2_id = %s)
              AND au.id != %s
              AND f.status = 'accepted'
        """, [request.user.id, request.user.id, request.user.id])
        friends = cursor.fetchall()

        # Get pending friend requests sent to the current user
        cursor.execute("""
            SELECT au.id, au.username
            FROM friends f
            JOIN auth_user au ON f.user1_id = au.id
            WHERE f.user2_id = %s AND f.status = 'pending'
        """, [request.user.id])
        pending_requests = cursor.fetchall()

    context = {
        'friends': [{'id': row[0], 'username': row[1]} for row in friends],
        'pending_requests': [{'id': row[0], 'username': row[1]} for row in pending_requests]
    }
    return render(request, 'blog/friends_list.html', context)

@login_required
def like_post(request, post_id):
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO post_likes (user_id, post_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, post_id) DO NOTHING
            """, [request.user.id, post_id])
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

@login_required
def post_comments(request, post_id):
    if request.method == 'POST':
        content = request.POST.get('content')
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO post_comments (user_id, post_id, content)
                VALUES (%s, %s, %s)
            """, [request.user.id, post_id, content])
        return redirect('post-detail', post_id=post_id)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT pc.content, pc.created_at, au.username
            FROM post_comments pc
            JOIN auth_user au ON pc.user_id = au.id
            WHERE pc.post_id = %s
            ORDER BY pc.created_at DESC
        """, [post_id])
        comments = cursor.fetchall()
    return JsonResponse({'comments': comments})


@login_required
def delete_post(request, post_id):
    if request.method == 'POST':
        with connection.cursor() as cursor:
            # Fetch the post's image path before deleting the post
            cursor.execute("SELECT image FROM blog_post WHERE id = %s AND author_id = %s", [post_id, request.user.id])
            post = cursor.fetchone()
            
            if post:
                # Delete the post's image file from the filesystem (if it exists)
                if post[0]:  # Check if the post has an image
                    image_path = os.path.join(settings.MEDIA_ROOT, post[0])
                    if os.path.exists(image_path):
                        os.remove(image_path)  # Delete the image file

                # Delete the post from the database
                cursor.execute("DELETE FROM blog_post WHERE id = %s AND author_id = %s", [post_id, request.user.id])
                messages.success(request, "Post deleted successfully!")
            else:
                messages.error(request, "Post not found or you are not authorized to delete it.")
        
        return redirect('home')
    return HttpResponseNotAllowed(['POST'])
