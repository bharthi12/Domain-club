
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from .forms import SubmissionForm
from .models import Puzzle, Submission
from .services import answers_match, process_expired_puzzles


@require_GET
def process_puzzles_cron(request):
    cron_secret = os.environ.get("CRON_SECRET")

    if not cron_secret:
        return JsonResponse(
            {"error": "CRON_SECRET is not configured"},
            status=500,
        )

    authorization = request.headers.get("Authorization")

    if authorization != f"Bearer {cron_secret}":
        return JsonResponse(
            {"error": "Unauthorized"},
            status=401,
        )

    results = process_expired_puzzles()

    return JsonResponse({
        "success": True,
        "processed": len(results),
    })


def current_puzzle(request):
    now = timezone.now()

    active_puzzles = Puzzle.objects.filter(
        start_time__lte=now,
        end_time__gt=now,
        is_processed=False,
    ).order_by("start_time")

    return render(
        request,
        "puzzles/puzzle_list.html",
        {"puzzles": active_puzzles},
    )


def puzzle_detail(request, pk):
    puzzle = get_object_or_404(Puzzle, pk=pk)

    submission = (
        request.user.submissions.filter(puzzle=puzzle).first()
        if request.user.is_authenticated
        else None
    )

    now = timezone.now()

    if now < puzzle.start_time:
        status = "upcoming"
    elif now < puzzle.end_time and not puzzle.is_processed:
        status = "active"
    else:
        status = "closed"

    return render(
        request,
        "puzzles/puzzle.html",
        {
            "puzzle": puzzle,
            "submission": submission,
            "form": SubmissionForm(),
            "status": status,
        },
    )


@login_required
def submit(request, pk):
    if request.method != "POST":
        return redirect("puzzles:detail", pk=pk)

    puzzle = get_object_or_404(Puzzle, pk=pk)

    now = timezone.now()

    # Puzzle must be within its admin-defined time window
    # and must not already be processed.
    if puzzle.is_processed or not (
        puzzle.start_time <= now < puzzle.end_time
    ):
        messages.error(
            request,
            "This puzzle is not accepting submissions.",
        )
        return redirect("puzzles:detail", pk=pk)

    # Only one submission per user per puzzle.
    if Submission.objects.filter(
        user=request.user,
        puzzle=puzzle,
    ).exists():
        messages.error(
            request,
            "You have already submitted an answer for this puzzle.",
        )
        return redirect("puzzles:detail", pk=pk)

    form = SubmissionForm(request.POST)

    if not form.is_valid():
        return render(
            request,
            "puzzles/puzzle.html",
            {
                "puzzle": puzzle,
                "form": form,
                "submission": None,
                "status": "active",
            },
        )

    answer = form.cleaned_data["answer"]

    try:
        submission = Submission.objects.create(
            user=request.user,
            puzzle=puzzle,
            submitted_value=answer,
            is_correct=answers_match(
                answer,
                puzzle.correct_answer,
            ),
        )

    except IntegrityError:
        messages.error(
            request,
            "You have already submitted an answer for this puzzle.",
        )

    else:
        messages.success(
            request,
            "Answer submitted. Results are revealed when the puzzle closes.",
        )

    return redirect("puzzles:detail", pk=pk)


def archive(request):
    now = timezone.now()

    puzzles = Puzzle.objects.filter(
        end_time__lte=now,
    ).order_by("-end_time")

    return render(
        request,
        "puzzles/puzzle_archive.html",
        {"puzzles": puzzles},
    )