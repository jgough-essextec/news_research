from django.contrib import admin
from django.utils.html import format_html

from .models import Article, ArticleDuplicate


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title_display', 'publication', 'scrape_status', 'topic_cluster', 'word_count', 'publication_date')
    list_filter = ('scrape_status', 'publication', 'topic_cluster')
    search_fields = ('title', 'canonical_url', 'content_text')
    date_hierarchy = 'publication_date'
    readonly_fields = (
        'url_hash', 'word_count', 'embedding_model', 'similarity_to_cluster',
        'scrape_attempts', 'last_scrape_at', 'created_at', 'updated_at'
    )
    raw_id_fields = ('topic_cluster',)

    fieldsets = (
        ('URL', {'fields': ('canonical_url', 'url_hash')}),
        ('Metadata', {'fields': ('title', 'author', 'publication', 'publication_date', 'og_image', 'language')}),
        ('Content', {'fields': ('excerpt', 'word_count')}),
        ('AI Processing', {'fields': ('summary', 'embedding_model', 'topic_cluster', 'similarity_to_cluster')}),
        ('Scraping', {'fields': ('scrape_status', 'scrape_error', 'scrape_attempts', 'last_scrape_at')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    def title_display(self, obj):
        title = obj.title or '(No title)'
        if len(title) > 60:
            title = title[:60] + '...'
        return format_html('<a href="{}" target="_blank">{}</a>', obj.canonical_url, title)
    title_display.short_description = 'Title'


@admin.register(ArticleDuplicate)
class ArticleDuplicateAdmin(admin.ModelAdmin):
    list_display = ('duplicate_article', 'primary_article', 'similarity_score')
    list_filter = ('similarity_score',)
    raw_id_fields = ('primary_article', 'duplicate_article')
