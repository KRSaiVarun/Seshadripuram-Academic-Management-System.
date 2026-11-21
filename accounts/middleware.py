from django.shortcuts import redirect
from django.urls import reverse


class RequirePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and user.must_change_password
            and request.path not in {
                reverse("password-change"),
                reverse("logout"),
            }
            and not request.path.startswith("/static/")
        ):
            return redirect("password-change")
        return self.get_response(request)
