from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ContactMessageSerializer
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


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
class about(APIView):
    def get(self, request):
        # Detailed description for the about page
        return Response({"title": "About"}, status=status.HTTP_200_OK)


# This view handles the services page.
class services(APIView):
    def get(self, request):
        services = [
            "Selling of lands",
            "Selling of homes",
            "Renting of apartments, homes and offices",
            "Construction",
        ]

        return Response(
            {"services": services},
            status=status.HTTP_200_OK,
        )


# This view handles the contact page and form submission.
logger = logging.getLogger(__name__)


# API view for handling contact form submissions
@api_view(["POST"])
@permission_classes([AllowAny])
def contact(request):
    serializer = ContactMessageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    submission = serializer.save()

    submission_dict = {
        "name": submission.name,
        "email": submission.email,
        "subject": submission.subject,
        "message": submission.message,
        "date": submission.submission_date.strftime("%B %d, %Y at %I:%M %p"),
        "site_name": settings.SITE_NAME,
    }

    # store in session for thank-you page
    request.session["recent_submission"] = submission_dict
    request.session.set_expiry(600)
    request.session.modified = True

    try:
        # -------- Admin notification --------
        admin_subject = f"New Contact Submission: {submission.subject[:50]}"
        admin_body = (
            f"New message from {submission.name}\n\n"
            f"Email: {submission.email}\n"
            f"Subject: {submission.subject}\n\n"
            f"Message:\n{submission.message}\n\n"
            f"Date: {submission_dict['date']}"
        )

        admin_email = EmailMultiAlternatives(
            subject=admin_subject,
            body=admin_body,
            from_email=f"{submission.name} <{settings.DEFAULT_FROM_EMAIL}>",  # Shows user name
            to=[settings.ADMIN_EMAIL],
            reply_to=[submission.email],  # Replies go to user
        )
        admin_email.send(fail_silently=False)

        # -------- User confirmation --------
        user_subject = f"Your message has been received - {settings.SITE_NAME}"
        user_body = (
            f"Hi {submission.name},\n\n"
            f"Thank you for contacting {settings.SITE_NAME}! "
            f"We received your message and will get back to you shortly.\n\n"
            f"Your message:\nSubject: {submission.subject}\nMessage: {submission.message}\n\n"
            f"Best regards,\n{settings.SITE_NAME}"
        )

        user_email = EmailMultiAlternatives(
            subject=user_subject,
            body=user_body,
            from_email=f"{submission.name} <{settings.DEFAULT_FROM_EMAIL}>",  # Your site email
            to=[submission.email],
        )
        user_email.send(fail_silently=False)

        return Response(
            {
                "submission": submission_dict,
                "message": "Message received and confirmation email sent.",
                "redirect": "/thank-you",
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.error(f"Email failed for submission {submission.id}: {str(e)}")
        return Response(
            {
                "submission": submission_dict,
                "warning": "Saved, but email sending failed.",
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
