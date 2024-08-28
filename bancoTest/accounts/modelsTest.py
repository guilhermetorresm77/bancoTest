from django.db import models
from django.utils import timezone
from decimal import Decimal

class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=50)

class Money(models.Model):
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.amount} {self.currency.code}"

    def add(self, other):
        if self.currency != other.currency:
            raise ValueError("Currencies must match")
        return Money.objects.create(amount=self.amount + other.amount, currency=self.currency)

    def subtract(self, other):
        if self.currency != other.currency:
            raise ValueError("Currencies must match")
        return Money.objects.create(amount=self.amount - other.amount, currency=self.currency)

    def multiply(self, factor):
        return Money.objects.create(amount=self.amount * Decimal(factor), currency=self.currency)

    def is_positive(self):
        return self.amount > 0

    def is_negative(self):
        return self.amount < 0

    def negate(self):
        return Money.objects.create(amount=-self.amount, currency=self.currency)

class EventType(models.Model):
    name = models.CharField(max_length=50, unique=True)

class AccountType(models.Model):
    name = models.CharField(max_length=50, unique=True)

class Account(models.Model):
    name = models.CharField(max_length=100)
    account_type = models.ForeignKey(AccountType, on_delete=models.PROTECT)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)

    def balance(self, date=None):
        entries = self.entries.all()
        if date:
            entries = entries.filter(date__lte=date)
        return sum(entry.amount for entry in entries)

    def add_entry(self, entry):
        entry.account = self
        entry.save()

class Customer(models.Model):
    name = models.CharField(max_length=100)
    accounts = models.ManyToManyField(Account)

    def add_entry(self, entry):
        account = self.accounts.get(account_type=entry.entry_type.account_type)
        account.add_entry(entry)

class EntryType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    account_type = models.ForeignKey(AccountType, on_delete=models.PROTECT)

class Entry(models.Model):
    account = models.ForeignKey(Account, related_name='entries', on_delete=models.PROTECT)
    entry_type = models.ForeignKey(EntryType, on_delete=models.PROTECT)
    amount = models.ForeignKey(Money, on_delete=models.PROTECT)
    date = models.DateTimeField()

class AccountingEvent(models.Model):
    event_type = models.ForeignKey(EventType, on_delete=models.PROTECT)
    when_occurred = models.DateTimeField()
    when_noticed = models.DateTimeField()
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    adjusted_event = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='adjustments')
    resulting_entries = models.ManyToManyField(Entry)

    def process(self):
        if self.adjusted_event:
            self.adjusted_event.reverse()
        self.find_rule().process(self)

    def find_rule(self):
        return self.customer.service_agreement.get_posting_rule(self.event_type, self.when_occurred)

    def reverse(self):
        for entry in self.resulting_entries.all():
            reversing_entry = Entry.objects.create(
                account=entry.account,
                entry_type=entry.entry_type,
                amount=entry.amount.negate(),
                date=timezone.now()
            )
            self.customer.add_entry(reversing_entry)
            self.resulting_entries.add(reversing_entry)
        self.reverse_secondary_events()

    def reverse_secondary_events(self):
        for secondary_event in self.secondary_events.all():
            secondary_event.reverse()

class ServiceAgreement(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE)
    rate = models.DecimalField(max_digits=5, decimal_places=2)

    def get_posting_rule(self, event_type, date):
        return self.posting_rules.filter(event_type=event_type, start_date__lte=date, end_date__gte=date).first()

class PostingRule(models.Model):
    service_agreement = models.ForeignKey(ServiceAgreement, related_name='posting_rules', on_delete=models.CASCADE)
    event_type = models.ForeignKey(EventType, on_delete=models.PROTECT)
    entry_type = models.ForeignKey(EntryType, on_delete=models.PROTECT)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)

    def process(self, event):
        amount = self.calculate_amount(event)
        entry = Entry.objects.create(
            account=event.customer.accounts.get(account_type=self.entry_type.account_type),
            entry_type=self.entry_type,
            amount=amount,
            date=event.when_noticed
        )
        event.customer.add_entry(entry)
        event.resulting_entries.add(entry)

    def calculate_amount(self, event):
        raise NotImplementedError("Subclasses must implement calculate_amount")

class MultiplyByRatePR(PostingRule):
    def calculate_amount(self, event):
        usage_event = event
        return Money.objects.create(
            amount=usage_event.amount * usage_event.customer.service_agreement.rate,
            currency=event.customer.accounts.first().currency
        )

class AmountFormulaPR(PostingRule):
    multiplier = models.DecimalField(max_digits=5, decimal_places=2)
    fixed_fee = models.ForeignKey(Money, on_delete=models.PROTECT)

    def calculate_amount(self, event):
        monetary_event = event
        return monetary_event.amount.multiply(self.multiplier).add(self.fixed_fee)

class Adjustment(AccountingEvent):
    new_events = models.ManyToManyField(AccountingEvent, related_name='adjustments_as_new')
    old_events = models.ManyToManyField(AccountingEvent, related_name='adjustments_as_old')

    def process(self):
        self.adjust()
        self.mark_processed()

    def adjust(self):
        self.snapshot_accounts()
        self.reverse_old_events()
        self.process_replacements()
        self.commit()

    def snapshot_accounts(self):
        # Logic to snapshot accounts would go here
        pass

    def reverse_old_events(self):
        for event in self.old_events.all():
            event.reverse()

    def process_replacements(self):
        for event in self.new_events.all():
            event.process()

    def commit(self):
        for account_type in AccountType.objects.all():
            self.adjust_account(account_type)
        self.restore_accounts()

    def adjust_account(self, account_type):
        # Logic to adjust account would go here
        pass

    def restore_accounts(self):
        # Logic to restore accounts would go here
        pass