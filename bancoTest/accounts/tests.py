from django.test import TestCase
from django.utils import timezone
from .models import (
    Currency,
    Money,
    PostingRule,
    Account,
    AccountType,
    EntryType, Entry,
    AccountingEvent,
    EventType,
    Customer,
    ServiceAgreement,
    DepositoAE,
    DepositoPR,
    SaqueAE,
    SaquePR
    )
from decimal import Decimal

class TestAccounting(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code='USD', name='US Dollar')
        self.customer = Customer.objects.create(name='Test Customer')
        self.account_type = AccountType.objects.create(name='Popança')
        self.account = Account.objects.create(name='Test Account', currency=self.currency, account_type=self.account_type)
        self.entry_type = EntryType.objects.create(name='Credito', account_type=self.account_type)
        self.entry_type2 = EntryType.objects.create(name='Debito', account_type=self.account_type)
        
        self.event_type = EventType.objects.create(name='Deposito')
        self.event_type2 = EventType.objects.create(name='Saque')
        
        self.money = Money.objects.create(amount=Decimal('100.00'), currency=self.currency)

        # Create ServiceAgreement and associate with Customer
        self.agreement = ServiceAgreement.objects.create(rate=Decimal('10.00'))
        
        # Adicionar a PostingRule
        self.posting_rule = DepositoPR.objects.create(
            service_agreement = self.agreement,
            event_type=self.event_type,
            entry_type=self.entry_type,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1)
        )


        self.posting_rule.save()
        self.agreement.save()
        self.customer.service_agreement = self.agreement
        self.customer.accounts.add(self.account)
        self.customer.save()
        
    def test_deposit(self):
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
        self.assertEqual(account_balance, Decimal('100.00'))  # Esperando que a taxa seja adicionada


    def test_saque(self):
        
        self.prSaque = SaquePR.objects.create(
            service_agreement = self.agreement,
            event_type=self.event_type2,
            entry_type=self.entry_type2,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1)
        )

        self.prSaque.save()
        self.agreement.save()
        self.customer.save()
        
        saque_event = SaqueAE.objects.create(
            amount=self.money,
            account=self.account,
            event_type=self.event_type2,
            when_occurred=timezone.now(),
            when_noticed=timezone.now(),
            customer=self.customer
        )
        saque_event.process()

        # Verificar o saldo
        account_balance = self.account.balance()
        self.assertEqual(account_balance, Decimal('-100.00'))  # Esperando que a taxa seja adicionada

