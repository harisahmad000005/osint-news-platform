from django.db import models
from django.utils import timezone
from django.core.validators import  MinValueValidator, MaxValueValidator
import hashlib
from sources.models import Source



class ArticleManager(models.Manager):
    """Custom manager with useful querysets"""
    
    def recent(self, days=7):
        """Articles from last N days"""
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.filter(fetched_at__gte=cutoff)
    
    def high_quality(self, min_score=0.7):
        """High quality articles only"""
        return self.filter(
            is_spam=False,
            quality_score__gte=min_score
        )
    
    def by_language(self, lang_code):
        """Filter by language"""
        return self.filter(language=lang_code)
    
    def with_entities(self):
        """Prefetch entities for efficiency"""
        return self.prefetch_related('entities__entity')


class Article(models.Model):
    """
    Main article storage (partitioned by month on fetched_at)
    Partitioning is done via RunSQL migration
    """
    
    # Core fields
    source = models.ForeignKey(
        Source,
        on_delete=models.PROTECT,
        related_name='articles'
    )
    url = models.TextField()
    url_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA256 hash of URL for deduplication"
    )
    canonical_url = models.TextField(blank=True)
    
    title = models.TextField()
    content = models.TextField()
    
    # Extraction results
    language = models.CharField(max_length=10, blank=True, db_index=True)
    
    # Sentiment analysis
    sentiment_label = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('POSITIVE', 'Positive'),
            ('NEGATIVE', 'Negative'),
            ('NEUTRAL', 'Neutral'),
        ],
        db_index=True
    )
    sentiment_score = models.FloatField(null=True, blank=True)
    
    # Quality metrics
    quality_score = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        db_index=True
    )
    is_spam = models.BooleanField(default=False, db_index=True)
    spam_signals = models.JSONField(default=dict, blank=True)
    
    # Clustering
    cluster = models.ForeignKey(
        'clusters.Cluster',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='articles'
    )
    
    # Evidence
    screenshot_path = models.CharField(max_length=1024, blank=True)
    raw_html = models.TextField(blank=True)
    
    # Timestamps (fetched_at is partition key)
    fetched_at = models.DateTimeField(db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Elasticsearch sync
    indexed_at = models.DateTimeField(null=True, blank=True)
    
    objects = ArticleManager()
    
    class Meta:
        db_table = 'articles_article'
        # Note: managed=False in production after partitioning migration
        # managed = False
        ordering = ['-fetched_at']
        indexes = [
            models.Index(fields=['-fetched_at']),
            models.Index(fields=['source', '-fetched_at']),
            models.Index(fields=['language', '-fetched_at']),
            models.Index(fields=['is_spam', 'quality_score', '-fetched_at']),
        ]
    
    def __str__(self):
        return f"{self.title[:50]}..."
    
    def save(self, *args, **kwargs):
        """Auto-generate URL hash if not set"""
        if not self.url_hash:
            self.url_hash = hashlib.sha256(self.url.encode()).hexdigest()
        super().save(*args, **kwargs)
    
    @property
    def is_recent(self):
        """Article fetched in last 24 hours"""
        return self.fetched_at >= timezone.now() - timezone.timedelta(hours=24)

