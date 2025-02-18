# from django.contrib import admin
# from django.db import models

# # Create unmanaged model for blog_post
# class CustomPost(models.Model):
#     class Meta:
#         managed = False
#         db_table = 'blog_post'
#         verbose_name = 'Post'
#         verbose_name_plural = 'Posts'

# class CustomPostAdmin(admin.ModelAdmin):
#     list_display = ('title', 'author', 'date_posted', 'content_preview')
    
#     def get_queryset(self, request):
#         return CustomPost.objects.raw('''
#             SELECT bp.*, au.username as author_name 
#             FROM blog_post bp
#             JOIN auth_user au ON bp.author_id = au.id
#         ''')
    
#     def author(self, obj):
#         return obj.author_name
    
#     def content_preview(self, obj):
#         return f"{obj.content[:50]}..." if len(obj.content) > 50 else obj.content

# admin.site.register(CustomPost, CustomPostAdmin)