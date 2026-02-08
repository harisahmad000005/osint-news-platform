from django.db import models

from entities.models import Entity
from sources.models import Source


class TrendingTopic(models.Model):
    """Daily snapshot of trending topics"""
    
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    
    # Metrics
    mention_count = models.IntegerField()
    article_count = models.IntegerField()
    velocity = models.FloatField(
        help_text="Rate of recent mentions vs total"
    )
    
    # Rankings
    rank = models.IntegerField()
    previous_rank = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'analytics_trendingtopic'
        unique_together = [['entity', 'date']]
        ordering = ['-date', 'rank']
        indexes = [
            models.Index(fields=['-date', 'rank']),
        ]
    
    def __str__(self):
        return f"{self.entity.text} - {self.date} (Rank #{self.rank})"


class ScrapingJob(models.Model):
    """Track scraping job executions"""
    
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    task_id = models.CharField(max_length=255, unique=True)
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    # Results
    articles_found = models.IntegerField(default=0)
    articles_created = models.IntegerField(default=0)
    articles_duplicate = models.IntegerField(default=0)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    
    # Errors
    error_message = models.TextField(blank=True)
    
    class Meta:
        db_table = 'monitoring_scrapingjob'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['source', '-started_at']),
            models.Index(fields=['status', '-started_at']),
        ]