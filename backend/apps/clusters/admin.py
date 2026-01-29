from django.contrib import admin

from .models import ClusterMerge, TopicCluster


@admin.register(TopicCluster)
class TopicClusterAdmin(admin.ModelAdmin):
    list_display = ('name', 'article_count', 'priority_score', 'is_active', 'last_article_added_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description', 'master_summary')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('article_count', 'priority_score', 'summary_generated_at', 'last_article_added_at', 'created_at', 'updated_at')
    raw_id_fields = ('primary_article',)

    fieldsets = (
        (None, {'fields': ('name', 'slug', 'description', 'is_active')}),
        ('Primary Article', {'fields': ('primary_article',)}),
        ('AI Summary', {'fields': ('master_summary', 'summary_generated_at')}),
        ('Statistics', {'fields': ('article_count', 'priority_score', 'last_article_added_at')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    actions = ['update_statistics', 'generate_summaries']

    @admin.action(description='Update cluster statistics')
    def update_statistics(self, request, queryset):
        for cluster in queryset:
            cluster.update_statistics()
        self.message_user(request, f'Updated statistics for {queryset.count()} clusters.')


@admin.register(ClusterMerge)
class ClusterMergeAdmin(admin.ModelAdmin):
    list_display = ('source_cluster', 'target_cluster', 'articles_moved', 'created_at')
    raw_id_fields = ('source_cluster', 'target_cluster')
