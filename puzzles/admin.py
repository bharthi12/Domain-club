from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path

from .models import Puzzle, Submission
from .services import process_expired_puzzles


@admin.register(Puzzle)
class PuzzleAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "start_time",
        "end_time",
        "is_processed",
        "winner",
        "created_at",
    )

    readonly_fields = (
        "is_processed",
        "winner",
        "created_at",
    )

    list_filter = ("is_processed",)

    search_fields = ("title",)

    change_list_template = "admin/puzzles/puzzle/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "process-expired/",
                self.admin_site.admin_view(self.process_expired),
                name="puzzles_puzzle_process_expired",
            ),
        ]

        return custom_urls + urls

    def process_expired(self, request):
        results = process_expired_puzzles()

        self.message_user(
            request,
            f"Processed {len(results)} expired puzzle(s).",
            messages.SUCCESS,
        )

        return HttpResponseRedirect("../")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):

    list_display = (
        "puzzle",
        "user",
        "submitted_value",
        "is_correct",
        "submitted_at",
    )

    list_filter = ("is_correct",)

    search_fields = (
        "user__username",
        "puzzle__title",
    )