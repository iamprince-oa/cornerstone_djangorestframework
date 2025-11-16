from django.urls import path
from .views import contact, index, about, services, ThankYouView

urlpatterns = [
    path("api/contact/", contact, name="contact-api"),
    path("", index.as_view(), name="index-api"),
    path("api/about/", about.as_view(), name="about-api"),
    path("api/services/", services.as_view(), name="services-api"),
    path("api/thank-you/", ThankYouView.as_view(), name="thank-you-api"),
]
