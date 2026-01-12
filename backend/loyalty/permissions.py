from rest_framework import permissions


class IsTenantMember(permissions.BasePermission):
    def has_permission(self, request, view):
        tenant = view.get_tenant()
        return request.user.is_authenticated and request.user.tenant_id == tenant.id


class IsClient(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "CLIENT"


class IsCashier(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ("CASHIER", "ADMIN")


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "ADMIN"
