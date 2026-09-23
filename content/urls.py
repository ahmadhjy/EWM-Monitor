from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("contact-us/", views.contact, name="contact"),
    path("newsletter/subscribe/", views.newsletter_subscribe, name="newsletter_subscribe"),
    path("<slug:slug>/", views.content_detail, name="content_detail"),
]
