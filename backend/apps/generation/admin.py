from django.contrib import admin
from django.utils.html import format_html

from .models import BlogPost, GeneratedImage, GenerationJob


class GeneratedImageInline(admin.TabularInline):
    model = GeneratedImage
    extra = 0
    readonly_fields = ('image_preview', 'prompt', 'generation_model')
    fields = ('image_type', 'image_preview', 'prompt', 'alt_text')

    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-width: 100px; max-height: 100px;" />', obj.image_url)
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'status', 'source_cluster', 'published_at', 'created_at')
    list_filter = ('status', 'created_by')
    search_fields = ('title', 'content_markdown', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'generation_model')
    raw_id_fields = ('created_by', 'source_cluster')
    filter_horizontal = ('source_articles',)
    inlines = [GeneratedImageInline]

    fieldsets = (
        (None, {'fields': ('title', 'slug', 'created_by', 'status')}),
        ('Content', {'fields': ('excerpt', 'content_markdown')}),
        ('Sources', {'fields': ('source_cluster', 'source_articles')}),
        ('Generation', {'fields': ('generation_prompt', 'generation_model', 'generation_config')}),
        ('SEO', {'fields': ('meta_title', 'meta_description')}),
        ('Publishing', {'fields': ('published_at',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ('blog_post', 'image_type', 'image_preview', 'generation_model', 'created_at')
    list_filter = ('image_type', 'generation_model')
    search_fields = ('prompt', 'alt_text')
    raw_id_fields = ('blog_post',)

    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-width: 50px; max-height: 50px;" />', obj.image_url)
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(GenerationJob)
class GenerationJobAdmin(admin.ModelAdmin):
    list_display = ('job_type', 'user', 'status', 'started_at', 'completed_at')
    list_filter = ('job_type', 'status', 'user')
    readonly_fields = ('started_at', 'completed_at', 'created_at', 'updated_at')
    raw_id_fields = ('user', 'blog_post', 'cluster')
