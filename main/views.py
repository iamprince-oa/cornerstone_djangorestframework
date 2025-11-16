from django.contrib import messages
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ContactMessageSerializer
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes


# This file defines the views for the portfolio application.
class index(APIView):
    def get(self, request):

        mission = (
            "At Cornerstone Development and Construction, we help clients secure genuine"
            "lands, own well built properties, and complete construction projects with confidence.\n\n"
            "We work with transparency, deliver on our promises, and focus on long-term value.\n\n"
            " Our aim is to make every step of land acquisition, property buying, and building simple,"
            " clear, and reliable."
        )

        vision = (
            "To become the leading source of trusted lands, quality homes, "
            "and dependable construction services,"
        )

        return Response(
            {
                "welcome": "Welcome To Cornerstone Development and Construction",
                "vision": vision,
                "title": "Home",
                "mission": mission,
            },
            status=status.HTTP_200_OK,
        )


# This view handles the about page.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class about(APIView):
    def get(self, request):
        # Detailed description for the about page
        return Response({"title": "About"}, status=status.HTTP_200_OK)


# This view handles the services page.
class services(APIView):
    def get(self, request):
        services = [
            "Selling of land",
            "Selling of building properties",
            "Renting of apartments",
            "Building construction",
        ]

        return Response(
            {"services": services},
            status=status.HTTP_200_OK,
        )


# This view handles the contact page and form submission.
logger = logging.getLogger(__name__)


# API view for handling contact form submissions
from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def contact(request):
    """
    Handle contact form submission:
    - Saves message to DB
    - Sends admin notification
    - Sends user confirmation
    - Sets session data for thank-you page
    """
    serializer = ContactMessageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    submission = serializer.save()

    # Build dictionary for API response & session
    submission_dict = {
        "name": submission.name,
        "email": submission.email,
        "subject": submission.subject,
        "message": submission.message,
        "date": submission.submission_date.strftime("%B %d, %Y at %I:%M %p"),
        "site_name": settings.SITE_NAME,
    }

    # Store in session for thank-you page (10 min expiry)
    request.session["recent_submission"] = submission_dict
    request.session.set_expiry(timedelta(minutes=10))
    request.session.modified = True

    # Send emails (optional: keep for HTML/plain text)
    try:
        # Admin email
        admin_email = EmailMultiAlternatives(
            subject=f"New Contact: {submission.subject[:50]}",
            body=f"New contact submission:\n\nName: {submission.name}\nEmail: {submission.email}\nSubject: {submission.subject}\nMessage: {submission.message}\nDate: {submission_dict['date']}",
            from_email=f"{settings.SITE_NAME} <{settings.DEFAULT_FROM_EMAIL}>",
            to=[settings.ADMIN_EMAIL],
            reply_to=[f"{submission.name} <{submission.email}>"],
        )
        admin_email.send()

        # User confirmation
        user_email = EmailMultiAlternatives(
            subject=f"Thanks for contacting {settings.SITE_NAME}!",
            body=f"Hi {submission.name},\n\nThanks for reaching out! We received your message:\n\nSubject: {submission.subject}\nMessage: {submission.message}\n\nWe'll get back to you soon.\n\n- {settings.SITE_NAME}",
            from_email=f"{settings.SITE_NAME} <{settings.DEFAULT_FROM_EMAIL}>",
            to=[submission.email],
        )
        user_email.send(fail_silently=True)

        logger.info(f"Contact form submitted by {submission.email}")

        return Response(
            {
                "submission": submission_dict,
                "message": "Your message has been sent successfully!",
                "redirect": "/thank-you",
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.error(f"Email failed for contact submission {submission.id}: {str(e)}")
        return Response(
            {
                "submission": submission_dict,
                "warning": "Message saved, but confirmation email failed to send.",
                "redirect": "/thank-you",
            },
            status=status.HTTP_200_OK,
        )


class ThankYouView(APIView):
    # Optional: Only allow within 5 minutes of submission
    SESSION_TIMEOUT_MINUTES = 5

    def get(self, request):
        recent = request.session.get("recent_submission")

        if not recent:
            return Response(
                {
                    "error": "No recent submission found.",
                    "detail": "Please submit the contact form first.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Optional: Expire old submissions
        submission_time = datetime.fromisoformat(recent["date"].replace("Z", "+00:00"))
        if timezone.now() > submission_time + timedelta(
            minutes=self.SESSION_TIMEOUT_MINUTES
        ):
            del request.session["recent_submission"]
            return Response(
                {"error": "Submission session expired."}, status=status.HTTP_410_GONE
            )

        # Optional: Clear after showing thank you (one-time view)
        submission_data = request.session.pop("recent_submission")  # Remove after use

        return Response(
            {
                "message": "Thank you for contacting us!",
                "name": submission_data["name"],
                "detail": "We will get back to you soon.",
            },
            status=status.HTTP_200_OK,
        )
