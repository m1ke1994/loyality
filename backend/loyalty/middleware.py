from django.http import Http404
from django.utils.deprecation import MiddlewareMixin
from .models import Tenant


class TenantMiddleware(MiddlewareMixin):
    def __call__(self, request):
        request.tenant = None
        return super().__call__(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        slug = view_kwargs.get("tenant_slug") if view_kwargs else None
        if not slug:
            return None
        try:
            request.tenant = Tenant.objects.get(slug=slug)
        except Tenant.DoesNotExist as exc:
            raise Http404("Tenant not found") from exc
        return None
