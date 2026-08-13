from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(User)
admin.site.register(Post)
admin.site.register(PostImage)
admin.site.register(PostView)
admin.site.register(Like)
admin.site.register(Share)
admin.site.register(Comment)
admin.site.register(Block)
admin.site.register(Notification)