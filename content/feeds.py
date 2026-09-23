from django.contrib.syndication.views import Feed
from django.urls import reverse_lazy
from django.utils import timezone

from .models import Article
from .i18n import is_arabic


class LatestArticlesFeed(Feed):
    title = "Elliott Wave Monitor"
    link = reverse_lazy("home")
    description = "Latest Elliott Wave forecasts, market analysis and trading education."

    def items(self):
        articles = Article.objects.filter(status="published", published_at__lte=timezone.now()).select_related("category")
        if is_arabic():
            articles = articles.exclude(title_ar="").exclude(body_ar="")
        return articles[:20]

    def item_title(self, item):
        return item.display_title

    def item_description(self, item):
        return item.display_excerpt

    def item_pubdate(self, item):
        return item.published_at
