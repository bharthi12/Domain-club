
from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Puzzle(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    correct_answer = models.CharField(max_length=100)

    solution = models.TextField()

    # Admin controls both of these values
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    winner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="puzzle_wins",
    )

    is_processed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-start_time",)
        indexes = [
            models.Index(
                fields=("start_time", "end_time", "is_processed")
            )
        ]

    def clean(self):
        # Validate answer
        try:
            Decimal(self.correct_answer)
        except (InvalidOperation, TypeError):
            raise ValidationError(
                {
                    "correct_answer": (
                        "Enter a valid integer or decimal."
                    )
                }
            )

        # Validate puzzle time window
        if self.end_time <= self.start_time:
            raise ValidationError(
                {
                    "end_time": (
                        "End time must be after start time."
                    )
                }
            )

    def save(self, *args, **kwargs):
        # Do NOT automatically calculate end_time.
        # The admin chooses both start_time and end_time.
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        """
        Puzzle is active only between start_time and end_time.
        """
        now = timezone.now()

        return (
            self.start_time <= now < self.end_time
            and not self.is_processed
        )

    @property
    def is_closed(self):
        """
        Puzzle has reached its admin-defined end time.
        """
        return timezone.now() >= self.end_time

    def __str__(self):
        return self.title


class Submission(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    puzzle = models.ForeignKey(
        Puzzle,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    submitted_value = models.CharField(max_length=100)

    is_correct = models.BooleanField(default=False)

    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "puzzle"),
                name="unique_submission_per_puzzle",
            )
        ]

        indexes = [
            models.Index(
                fields=("puzzle", "is_correct", "submitted_at")
            )
        ]

        ordering = ("submitted_at",)