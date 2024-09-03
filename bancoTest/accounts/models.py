from django.db import models
from django.utils import timezone
from decimal import Decimal

class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

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
    
    def add_value(self, value):
        if not isinstance(value, (Decimal, float)):
            raise TypeError("The value must be a Decimal or float")
        new_amount = self.amount + Decimal(value)
        return Money.objects.create(amount=new_amount, currency=self.currency)
    
    def is_equals(self, other):
        if not isinstance(other, Money):
            raise TypeError("The other value must be a Money instance")
        return self.amount == other.amount

class EventType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class AccountType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Account(models.Model):
    name = models.CharField(max_length=100)
    account_type = models.ForeignKey(AccountType, on_delete=models.PROTECT)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)

    def balance(self, date=None):
        entries = self.entries.all()

        if date:
            entries = entries.filter(date__lte=date)

        total = Decimal('0.00')

        for entry in entries:
            total += entry.amount.amount
        return total

    def add_entry(self, entry):
        entry.account = self
        entry.save()

    def __str__(self):
        return self.name

class Customer(models.Model):
    name = models.CharField(max_length=100)
    accounts = models.ManyToManyField(Account)
    service_agreement = models.ForeignKey('ServiceAgreement', related_name='customer', on_delete=models.PROTECT, null=True)
    
    def add_entry(self, entry):
        account = self.accounts.get(account_type=entry.entry_type.account_type)
        account.add_entry(entry)

    def __str__(self):
        return self.name
    
class EntryType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    account_type = models.ForeignKey(AccountType, on_delete=models.PROTECT)

    def __str__(self):
        return self.name

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
    is_processed = models.BooleanField(default=False)

    def process(self):
        print("Processing")
        if self.is_processed:
            raise ValueError('Cannot process an event twice')
        if self.adjusted_event:
            self.adjusted_event.reverse()
        rule = self.find_rule()
        if rule is not None:
            rule.process(self)
            self.is_processed = True
        else:
            raise ValueError('No posting rule found for this event')

    def find_rule(self):
        print("Procurando Regra de postagem pelo agreement")
        rule = self.customer.service_agreement.get_posting_rule(self.event_type, self.when_occurred)
        print(f"A Posting rule encontrada: {rule.__class__.__name__ if rule else 'None'}")

        if rule:
            return rule
        else:
            raise ValueError('Não foi encontrado uma regra de postagem para esse evento')

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
    rate = models.DecimalField(max_digits=10, decimal_places=2)

    def get_posting_rule(self, event_type, date):

        # Lista de regras de postagem para cada evento
        lista_Posting_rules = ['depositopr', 'saquepr']

        print("Getting posting rule for event", event_type)
        for related_name in lista_Posting_rules:  # Add more as needed
            rules = getattr(self, related_name).filter(
                event_type=event_type, 
                start_date__lte=date
            ).filter(models.Q(end_date__gte=date) | models.Q(end_date__isnull=True))
            rule = rules.first()
            if rule:
                return rule
        return None
    
class PostingRule(models.Model):
    service_agreement = models.ForeignKey(ServiceAgreement, related_name='%(class)s', on_delete=models.PROTECT)
    event_type = models.ForeignKey(EventType, on_delete=models.PROTECT)
    entry_type = models.ForeignKey(EntryType, on_delete=models.PROTECT)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def process(self, event):
        amount = self.calculate_amount(event)
        self.make_entry(event, amount)

    def make_entry(self, event, amount):
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

class DepositoAE(AccountingEvent):
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    amount = models.ForeignKey(Money, on_delete=models.PROTECT)

class DepositoPR(PostingRule):
    
    def calculate_amount(self, event):
        return event.amount

class SaqueAE(AccountingEvent):
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    amount = models.ForeignKey(Money, on_delete=models.PROTECT)

class SaquePR(PostingRule):
    
    def calculate_amount(self, event):
        # Verify that the account amount is more than the saque amount
        if event.amount.amount > event.account.balance():
            raise ValueError("Insufficient funds")
        return event.amount.negate()

