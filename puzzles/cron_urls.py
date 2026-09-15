from django.urls import path
from .views import process_puzzles_cron

urlpatterns = [
    path(
        "process-puzzles/",
        process_puzzles_cron,
        name="process-puzzles-cron",
    ),
]