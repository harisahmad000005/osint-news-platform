from django.db import models
from django.utils import timezone
from django.core.validators import  MinValueValidator, MaxValueValidator


class Source(models.Model):
    """News sources (RSS feeds, websites, APIs)"""
    
    SOURCE_TYPES = [
        ('rss', 'RSS Feed'),
        ('atom', 'Atom Feed'),
        ('html', 'HTML Scraping'),
        ('api', 'API'),
        ('telegram', 'Telegram Channel'),
    ]
    
    name = models.CharField(max_length=255, db_index=True)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES, db_index=True)
    feed_url = models.URLField(max_length=2048, unique=True)
    base_url = models.URLField(max_length=1024)
    
    # Health monitoring
    enabled = models.BooleanField(default=True, db_index=True)
    last_polled_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    consecutive_failures = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    last_error = models.TextField(blank=True, default='')
    
    # Quality metrics
    trust_score = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="0-1 score for source reliability"
    )
    avg_quality_score = models.FloatField(null=True, blank=True)
    
    # Discovery tracking
    discovered_at = models.DateTimeField(null=True, blank=True)
    discovery_keyword = models.CharField(max_length=255, blank=True)
    auto_discovered = models.BooleanField(default=False)
    
    # Configuration
    poll_interval_minutes = models.IntegerField(default=30)
    parser_config = models.JSONField(default=dict, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sources_source'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['enabled', '-last_polled_at']),
            models.Index(fields=['source_type', 'enabled']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"
    
    def mark_success(self):
        """Update health metrics after successful poll"""
        self.last_polled_at = timezone.now()
        self.last_success_at = timezone.now()
        self.consecutive_failures = 0
        self.last_error = ''
        self.save(update_fields=['last_polled_at', 'last_success_at', 
                                 'consecutive_failures', 'last_error'])
    
    def mark_failure(self, error_message):
        """Update health metrics after failed poll"""
        self.last_polled_at = timezone.now()
        self.consecutive_failures += 1
        self.last_error = error_message[:500]
        
        # Circuit breaker: disable after 5 consecutive failures
        if self.consecutive_failures >= 5:
            self.enabled = False
        
        self.save(update_fields=['last_polled_at', 'consecutive_failures', 
                                 'last_error', 'enabled'])

