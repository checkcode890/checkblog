# from django.contrib import admin
# from django.db import models

# # Create unmanaged model for auth_user
# class CustomUser(models.Model):
#     class Meta:
#         managed = False
#         db_table = 'auth_user'
#         verbose_name = 'User'
#         verbose_name_plural = 'Users'

# # Create unmanaged model for users_profile
# class CustomProfile(models.Model):
#     class Meta:
#         managed = False
#         db_table = 'users_profile'
#         verbose_name = 'Profile'
#         verbose_name_plural = 'Profiles'

# class CustomUserAdmin(admin.ModelAdmin):
#     list_display = ('id', 'username', 'email', 'date_joined')
#     search_fields = ('username', 'email')
    
#     def get_queryset(self, request):
#         return CustomUser.objects.raw('SELECT * FROM auth_user')

# class CustomProfileAdmin(admin.ModelAdmin):
#     list_display = ('user_id', 'image_preview')
    
#     def get_queryset(self, request):
#         return CustomProfile.objects.raw('SELECT * FROM users_profile')
    
#     def image_preview(self, obj):
#         return f'<img src="/media/{obj.image}" width="50" />'
#     image_preview.allow_tags = True

# admin.site.register(CustomUser, CustomUserAdmin)
# admin.site.register(CustomProfile, CustomProfileAdmin)