from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from articles.models import Article


class Entity(models.Model):
    """Named entities (people, orgs, locations, etc)"""
    
    ENTITY_TYPES = [
        ('PERSON', 'Person'),
        ('ORG', 'Organization'),
        ('GPE', 'Geopolitical Entity'),
        ('LOC', 'Location'),
        ('PRODUCT', 'Product'),
        ('EVENT', 'Event'),
        ('DATE', 'Date'),
        ('MONEY', 'Money'),
    ]
    
    type = models.CharField(max_length=20, choices=ENTITY_TYPES, db_index=True)
    text = models.CharField(max_length=255)
    normalized_text = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Lowercased for matching"
    )
    
    # Statistics
    mention_count = models.IntegerField(default=0)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'entities_entity'
        unique_together = [['type', 'normalized_text']]
        ordering = ['-mention_count']
        indexes = [
            models.Index(fields=['type', 'normalized_text']),
            models.Index(fields=['-mention_count']),
        ]
    
    def __str__(self):
        return f"{self.text} ({self.get_type_display()})"
    
    def save(self, *args, **kwargs):
        """Auto-normalize text"""
        if not self.normalized_text:
            self.normalized_text = self.text.lower()
        super().save(*args, **kwargs)


class ArticleEntity(models.Model):
    """Many-to-many link between articles and entities"""
    
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name='entities'
    )
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name='article_mentions'
    )
    
    # Extraction metadata
    confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    start_offset = models.IntegerField(null=True, blank=True)
    end_offset = models.IntegerField(null=True, blank=True)
    extractor_name = models.CharField(max_length=50, default='spacy')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'entities_articleentity'
        unique_together = [['article', 'entity', 'start_offset']]
        indexes = [
            models.Index(fields=['article']),
            models.Index(fields=['entity']),
        ]
    
    def __str__(self):
        return f"{self.entity.text} in {self.article.title[:30]}"
