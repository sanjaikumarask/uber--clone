from django.contrib import admin
from django.db.models import Sum

from apps.payments.models import Payment, LedgerEntry, Payout


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "ride_id",
        "amount",
        "status",
        "gateway",
        "gateway_order_id",
        "created_at",
    )

    list_filter = ("status", "gateway", "currency")
    search_fields = ("gateway_order_id", "gateway_payment_id", "user__phone")
    readonly_fields = (
        "user",
        "ride_id",
        "amount",
        "refunded_amount",
        "currency",
        "status",
        "gateway",
        "gateway_order_id",
        "gateway_payment_id",
        "gateway_signature",
        "failure_reason",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False  # payments must come from gateway

    def has_delete_permission(self, request, obj=None):
        return False  # NEVER delete payments


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "ride_id",
        "amount",
        "entry_type",
        "reason",
        "reference",
        "created_at",
    )

    list_filter = ("entry_type", "reason")
    search_fields = ("reference", "user__phone")
    readonly_fields = (
        "user",
        "ride_id",
        "payment",
        "amount",
        "entry_type",
        "reason",
        "reference",
        "created_at",
    )

    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False  # ledger is append-only

    def has_change_permission(self, request, obj=None):
        return False  # IMMUTABLE

    def has_delete_permission(self, request, obj=None):
        return False  # IMMUTABLE


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "driver",
        "amount",
        "fee",
        "net_amount",
        "status",
        "reference",
        "created_at",
    )

    list_filter = ("status",)
    search_fields = ("reference", "driver__phone")
    readonly_fields = (
        "driver",
        "amount",
        "fee",
        "net_amount",
        "reference",
        "created_at",
    )

    ordering = ("-created_at",)

    actions = ["mark_processing", "mark_paid", "mark_failed"]

    def mark_processing(self, request, queryset):
        queryset.filter(status=Payout.Status.REQUESTED).update(
            status=Payout.Status.PROCESSING
        )

    mark_processing.short_description = "Mark selected payouts as PROCESSING"

    def mark_paid(self, request, queryset):
        queryset.filter(status=Payout.Status.PROCESSING).update(
            status=Payout.Status.PAID
        )

    mark_paid.short_description = "Mark selected payouts as PAID (manual)"

    def mark_failed(self, request, queryset):
        queryset.exclude(status=Payout.Status.PAID).update(
            status=Payout.Status.FAILED
        )

    mark_failed.short_description = "Mark selected payouts as FAILED"

    def has_delete_permission(self, request, obj=None):
        return False
