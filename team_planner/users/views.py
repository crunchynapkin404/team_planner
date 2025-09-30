from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView

from team_planner.users.forms import RecurringLeavePatternInlineFormSet
from team_planner.users.forms import UserProfileForm
from team_planner.users.models import User


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from team_planner.employees.models import RecurringLeavePattern

        user_obj = self.get_object()
        context["recurring_patterns"] = RecurringLeavePattern.objects.filter(
            employee=user_obj, is_active=True,
        ).order_by("day_of_week", "coverage_type")
        return context


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = "users/user_form.html"
    # Align with tests expecting this exact message
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return reverse("users:detail", kwargs={"username": self.request.user.username})

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return User.objects.get(pk=self.request.user.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.get_object()
        if self.request.POST:
            context["recurring_patterns_formset"] = RecurringLeavePatternInlineFormSet(
                self.request.POST, instance=user_obj, user=user_obj,
            )
        else:
            context["recurring_patterns_formset"] = RecurringLeavePatternInlineFormSet(
                instance=user_obj, user=user_obj,
            )
        return context

    def form_valid(self, form):
        # Ensure self.object is set for UpdateView before accessing context
        self.object = self.get_object()

        # If this isn't a POST (e.g., tests calling form_valid on a GET request),
        # skip formset validation and let SuccessMessageMixin handle messaging.
        if self.request.method != "POST":
            return super().form_valid(form)

        context = self.get_context_data()
        recurring_patterns_formset = context["recurring_patterns_formset"]
        user_obj = self.object

        if recurring_patterns_formset.is_valid():
            response = super().form_valid(form)
            recurring_patterns_formset.instance = user_obj
            recurring_patterns_formset.save()

            # Count active patterns
            from team_planner.employees.models import RecurringLeavePattern

            active_patterns = RecurringLeavePattern.objects.filter(
                employee=user_obj, is_active=True,
            ).count()
            if active_patterns == 0:
                messages.info(
                    self.request,
                    _(
                        "No recurring leave patterns are currently active. You're available for all shifts.",
                    ),
                )
            else:
                messages.success(
                    self.request,
                    _(
                        f"Successfully updated {active_patterns} recurring leave pattern(s).",
                    ),
                )

            return response
        messages.error(
            self.request,
            _("Please correct the errors in your recurring leave patterns."),
        )
        return self.render_to_response(self.get_context_data(form=form))


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()
