from django.contrib import admin

from .models import ExtractedLink, NewsletterEmail


class ExtractedLinkInline(admin.TabularInline):
    model = ExtractedLink
    extra = 0
    readonly_fields = ('raw_url', 'canonical_url', 'anchor_text', 'status', 'article')
    can_delete = False


@admin.register(NewsletterEmail)
class NewsletterEmailAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sender_name', 'user', 'received_date', 'is_processed', 'link_count')
    list_filter = ('is_processed', 'sender_email', 'user')
    search_fields = ('subject', 'sender_name', 'sender_email')
    date_hierarchy = 'received_date'
    readonly_fields = ('gmail_message_id', 'thread_id', 'processed_at', 'link_count', 'created_at', 'updated_at')
    inlines = [ExtractedLinkInline]

    fieldsets = (
        ('Email Info', {'fields': ('user', 'gmail_message_id', 'thread_id', 'sender_email', 'sender_name', 'subject')}),
        ('Content', {'fields': ('received_date', 'snippet')}),
        ('Processing', {'fields': ('is_processed', 'processed_at', 'link_count')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(ExtractedLink)
class ExtractedLinkAdmin(admin.ModelAdmin):
    list_display = ('canonical_url', 'newsletter_email', 'status', 'is_valid_article', 'article')
    list_filter = ('status', 'is_valid_article')
    search_fields = ('raw_url', 'canonical_url', 'anchor_text')
    raw_id_fields = ('newsletter_email', 'article')
