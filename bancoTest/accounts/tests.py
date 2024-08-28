from django.test import TestCase
from django.utils import timezone
from .models import Currency, Money, Account, AccountType, EntryType, Entry, AccountingEvent, EventType, Customer, ServiceAgreement, MultiplyByRatePR, AmountFormulaPR
from decimal import Decimal

class CurrencyModelTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code='USD', name='US Dollar')

    def test_currency_creation(self):
        self.assertEqual(self.currency.code, 'USD')
        self.assertEqual(self.currency.name, 'US Dollar')

class MoneyModelTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code='USD', name='US Dollar')
        self.money = Money.objects.create(amount=Decimal('100.00'), currency=self.currency)

    def test_money_creation(self):
        self.assertEqual(self.money.amount, Decimal('100.00'))
        self.assertEqual(self.money.currency, self.currency)

    def test_money_addition(self):
        other_money = Money.objects.create(amount=Decimal('50.00'), currency=self.currency)
        new_money = self.money.add(other_money)
        self.assertEqual(new_money.amount, Decimal('150.00'))

    def test_money_subtraction(self):
        other_money = Money.objects.create(amount=Decimal('30.00'), currency=self.currency)
        new_money = self.money.subtract(other_money)
        self.assertEqual(new_money.amount, Decimal('70.00'))

class AccountModelTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code='USD', name='US Dollar')
        self.account_type = AccountType.objects.create(name='poupanca')
        self.account = Account.objects.create(name='Test Account', currency=self.currency, account_type=self.account_type)

    def test_account_creation(self):
        self.assertEqual(self.account.name, 'Test Account')
        self.assertEqual(self.account.currency, self.currency)

class EntryModelTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code='USD', name='US Dollar')
        self.money = Money.objects.create(amount=Decimal('100.00'), currency=self.currency)
        self.account_type = AccountType.objects.create(name='poupanca')
        self.account = Account.objects.create(name='Test Account', currency=self.currency, account_type=self.account_type)
        self.entry_type = EntryType.objects.create(name='Test EntryType', account_type=self.account_type)
        self.entry = Entry.objects.create(account=self.account, entry_type=self.entry_type, amount=self.money, date=timezone.now())

    def test_entry_creation(self):
        self.assertEqual(self.entry.account, self.account)
        self.assertEqual(self.entry.entry_type, self.entry_type)
        self.assertEqual(self.entry.amount, self.money)

class AccountingEventModelTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code='USD', name='US Dollar')
        self.customer = Customer.objects.create(name='Test Customer')
        self.account_type = AccountType.objects.create(name='poupanca')
        self.account = Account.objects.create(name='Test Account', currency=self.currency, account_type=self.account_type)
        self.entry_type = EntryType.objects.create(name='Test EntryType', account_type=self.account_type)
        self.money = Money.objects.create(amount=Decimal('100.00'), currency=self.currency)
        self.entry = Entry.objects.create(account=self.account, entry_type=self.entry_type, amount=self.money, date=timezone.now())
        self.event_type = EventType.objects.create(name='Test EventType')
        self.accounting_event = AccountingEvent.objects.create(
            event_type=self.event_type,
            when_occurred=timezone.now(),
            when_noticed=timezone.now(),
            customer=self.customer
        )
        self.accounting_event.resulting_entries.add(self.entry)

    def test_accounting_event_creation(self):
        self.assertEqual(self.accounting_event.event_type, self.event_type)
        self.assertEqual(self.accounting_event.customer, self.customer)
        self.assertIn(self.entry, self.accounting_event.resulting_entries.all())


class DepositoEventModelTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code='USD', name='US Dollar')
        self.customer = Customer.objects.create(name='Test Customer')
        self.account = Account.objects.create(name='Test Account', currency=self.currency, account_type=1)
        self.entry_type_credit = EntryType.objects.create(name='Crédito', account_type=1)
        self.money = Money.objects.create(amount=Decimal('100.00'), currency=self.currency)
        self.deposit_event = DepositoEvent.objects.create(
            event_type=EventType.objects.create(name='Depósito'),
            when_occurred=timezone.now(),
            when_noticed=timezone.now(),
            customer=self.customer,
            deposit_amount=Decimal('50.00')
        )
    
    def test_deposito_event_process(self):
        self.deposit_event.process()
        # Verifica se a entrada foi criada e adicionada
        self.assertEqual(self.customer.accounts.first().entries.count(), 1)
        entry = self.customer.accounts.first().entries.first()
        self.assertEqual(entry.amount.amount, Decimal('50.00'))
        self.assertEqual(entry.entry_type.name, 'Crédito')
