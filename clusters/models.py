from django.db import models
from django.contrib.postgres.fields import ArrayField
from entities.models import Entity



class Cluster(models.Model):
    """Story clusters (groups of related articles)"""
    
    # Cluster metadata
    cluster_label = models.IntegerField(db_index=True)
    summary = models.TextField(blank=True)
    
    # Statistics
    article_count = models.IntegerField(default=0)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    is_trending = models.BooleanField(default=False, db_index=True)
    
    # Computed fields
    dominant_entities = models.JSONField(default=list, blank=True)
    languages = ArrayField(
        models.CharField(max_length=10),
        default=list,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'clusters_cluster'
        ordering = ['-last_seen_at']
        indexes = [
            models.Index(fields=['is_active', '-last_seen_at']),
            models.Index(fields=['is_trending', '-last_seen_at']),
            models.Index(fields=['cluster_label']),
        ]
    
    def __str__(self):
        return f"Cluster {self.cluster_label} ({self.article_count} articles)"
    
    def update_statistics(self):
        """Recalculate cluster statistics"""
        articles = self.articles.all()
        
        self.article_count = articles.count()
        
        if articles.exists():
            self.first_seen_at = articles.order_by('fetched_at').first().fetched_at
            self.last_seen_at = articles.order_by('-fetched_at').first().fetched_at
            
            # Get top entities
            from django.db.models import Count
            top_entities = (
                Entity.objects
                .filter(article_mentions__article__cluster=self)
                .annotate(count=Count('article_mentions'))
                .order_by('-count')[:5]
                .values('text', 'type', 'count')
            )
            self.dominant_entities = list(top_entities)
            
            # Get languages
            self.languages = list(
                articles.values_list('language', flat=True).distinct()
            )
        
        self.save(update_fields=[
            'article_count', 'first_seen_at', 'last_seen_at',
            'dominant_entities', 'languages'
        ])

