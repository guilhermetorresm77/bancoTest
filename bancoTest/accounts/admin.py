# myapp/admin.py

from django.contrib import admin
from .models import Currency, Money, PostingRule, Account, AccountType, EntryType, Entry, AccountingEvent, EventType, Customer, ServiceAgreement, DepositoAE, DepositoPR

@admin.register(AccountingEvent)
class AccountingEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'customer')

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')

@admin.register(Money)
class MoneyAdmin(admin.ModelAdmin):
    list_display = ('amount', 'currency')

@admin.register(PostingRule)
class PostingRuleAdmin(admin.ModelAdmin):
    list_display = ('service_agreement', 'event_type', 'entry_type')

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_type', 'currency')

@admin.register(AccountType)
class AccountTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(EntryType)
class EntryTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Entry)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('account', 'entry_type', 'amount', 'date')

@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'service_agreement',)

@admin.register(ServiceAgreement)
class ServiceAgreementAdmin(admin.ModelAdmin):
    list_display = ('rate',)
