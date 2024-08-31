from django.test import TestCase
from django.utils import timezone
from .models import Currency, Money, PostingRule, Account, AccountType, EntryType, Entry, AccountingEvent, EventType, Customer, ServiceAgreement, DepositoAE, DepositoPR
from decimal import Decimal

class TestAccounting(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code='USD', name='US Dollar')
        self.customer = Customer.objects.create(name='Test Customer')
        self.account_type = AccountType.objects.create(name='Popança')
        self.account = Account.objects.create(name='Test Account', currency=self.currency, account_type=self.account_type)
        self.entry_type = EntryType.objects.create(name='Credito', account_type=self.account_type)
        self.event_type = EventType.objects.create(name='Deposito')
        self.money = Money.objects.create(amount=Decimal('100.00'), currency=self.currency)

        # Create ServiceAgreement and associate with Customer
        self.agreement = ServiceAgreement.objects.create(rate=Decimal('10.00'))
        self.customer.service_agreement = self.agreement
        self.customer.accounts.add(self.account)
        self.customer.save()

        
    def test_posting_rule_creation(self):
        self.posting_rule2 = self.agreement.add_posting_rule(
            posting_rule_class=DepositoPR,
            event_type=self.event_type,
            entry_type=self.entry_type,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1)
        )
        self.posting_rule2.save()
        
        # Verifique se a regra específica foi criada
        found_rule = PostingRule.objects.get(event_type=self.event_type)
        self.assertIsInstance(found_rule, DepositoPR, "A regra encontrada não é uma DepositoPR")

    def test_deposit(self):
        # Adicionar a PostingRule
        self.posting_rule = self.agreement.add_posting_rule(
            posting_rule_class=DepositoPR,
            event_type=self.event_type,
            entry_type=self.entry_type,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1)
        )
        print(f"Posting rule created: {self.posting_rule.__class__.__name__}")

        self.posting_rule.save()

        deposit_event = DepositoAE.objects.create(
            amount=self.money,
            account=self.account,
            event_type=self.event_type,
            when_occurred=timezone.now(),
            when_noticed=timezone.now(),
            customer=self.customer
        )
        deposit_event.process()

        # Verificar o saldo
        account_balance = self.account.balance()
        self.assertEqual(account_balance, Decimal('110.00'))  # Esperando que a taxa seja adicionada

        # Opcional: Verificar se a entrada foi criada
        self.assertTrue(Entry.objects.filter(account=self.account).exists())
