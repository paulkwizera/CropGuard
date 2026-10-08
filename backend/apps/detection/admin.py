from django.contrib import admin

from .models import Detection


@admin.register(Detection)
class DetectionAdmin(admin.ModelAdmin):
    list_display = ("top_label", "top_confidence", "user", "created_at")
    list_filter = ("top_label",)
