from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "tally/home.html"
