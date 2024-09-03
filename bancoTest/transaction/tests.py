# transactions/tests.py
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from accounts.models import Account, Currency, Customer, ServiceAgreement, AccountType
from .models import Transaction, DepositEvent, WithdrawalEvent, TransferEvent, TransactionType, TransactionStatus, DepositPR, WithdrawalPR, TransferPR
from accounts.models import EventType, EntryType, Money

class TransactionTestCase(TestCase):
    def setUp(self):
        # Criar moedas
        self.currency = Currency.objects.create(code='USD', name='US Dollar')

        # Criar tipos de conta
        self.checking_type = AccountType.objects.create(name='Checking')
        self.savings_type = AccountType.objects.create(name='Savings')

        # Criar tipos de evento
        self.deposit_event_type = EventType.objects.create(name='DEPOSIT')
        self.withdrawal_event_type = EventType.objects.create(name='WITHDRAWAL')
        self.transfer_event_type = EventType.objects.create(name='TRANSFER')

        # Criar tipos de entrada
        self.deposit_entry_type = EntryType.objects.create(name='Deposit', account_type=self.checking_type)
        self.withdrawal_entry_type = EntryType.objects.create(name='Withdrawal', account_type=self.checking_type)
        self.transfer_entry_type = EntryType.objects.create(name='Transfer', account_type=self.checking_type)

        # Criar tipos de transaction
        self.deposit_trasaction_type = TransactionType.objects.create(name='DEPOSIT')
        self.withdrawal_trasaction_type = TransactionType.objects.create(name='WITHDRAWAL')
        self.transfer_trasaction_type = TransactionType.objects.create(name='TRANSFER')

        # Criar status de transaction
        self.completed_status = TransactionStatus.objects.create(name='COMPLETED')
        self.pending_status = TransactionStatus.objects.create(name='PENDING')
        self.cancelled_status = TransactionStatus.objects.create(name='CANCELLED')

        # Criar cliente e acordo de serviço
        self.service_agreement = ServiceAgreement.objects.create(rate=Decimal('0.01'))
        
        # Criar regras de postagem
        self.depositoPR = DepositPR.objects.create(
            service_agreement=self.service_agreement,
            event_type=self.deposit_event_type,
            entry_type=self.deposit_entry_type,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=10)
        )
        self.saquePR = WithdrawalPR.objects.create(
            service_agreement=self.service_agreement,
            event_type=self.withdrawal_event_type,
            entry_type=self.withdrawal_entry_type,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=10)
        )
        self.transferPR = TransferPR.objects.create(
            service_agreement=self.service_agreement,
            event_type=self.transfer_event_type,
            entry_type=self.transfer_entry_type,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=10)
        )

        # Criar cliente
        self.customer = Customer.objects.create(name='John Doe', service_agreement=self.service_agreement)

        # Criar contas
        self.account1 = Account.objects.create(name='John Checking', account_type=self.checking_type, currency=self.currency)
        self.account2 = Account.objects.create(name='John Savings', account_type=self.savings_type, currency=self.currency)
        self.customer.accounts.add(self.account1, self.account2)

        self.customer.save()

    def test_deposit_transaction(self):
        transaction = Transaction.objects.create(
            customer=self.customer,
            from_account=self.account1,
            amount=Money.objects.create(amount=Decimal('100.00'), currency=self.currency),
            transaction_type=self.deposit_trasaction_type,
            transaction_status=self.completed_status
        )
        transaction.save()
        event = transaction.create_accounting_event()
        event.process()

        self.assertIsInstance(event, DepositEvent)
        self.assertEqual(event.event_type, self.deposit_event_type)
        self.assertEqual(event.account, self.account1)
        self.assertEqual(event.amount.amount, Decimal('100.00'))

    def test_withdrawal_transaction(self):
        transaction = Transaction.objects.create(
            customer=self.customer,
            from_account=self.account1,
            amount=Money.objects.create(amount=Decimal('50.00'), currency=self.currency),
            transaction_type=self.withdrawal_trasaction_type,
            transaction_status=self.completed_status
        )
        event = transaction.create_accounting_event()
        event.process()

        self.assertIsInstance(event, WithdrawalEvent)
        self.assertEqual(event.event_type, self.withdrawal_event_type)
        self.assertEqual(event.account, self.account1)
        self.assertEqual(event.amount.amount, Decimal('50.00'))

    def test_transfer_transaction(self):
        
        transaction = Transaction.objects.create(
            customer=self.customer,
            from_account=self.account1,
            amount=Money.objects.create(amount=Decimal('100.00'), currency=self.currency),
            transaction_type=self.deposit_trasaction_type,
            transaction_status=self.completed_status
        )
        transaction.save()
        event = transaction.create_accounting_event()
        event.process()

        transaction2 = Transaction.objects.create(
            customer=self.customer,
            from_account=self.account1,
            to_account=self.account2,
            amount=Money.objects.create(amount=Decimal('75.00'), currency=self.currency),
            transaction_type=self.transfer_trasaction_type,
            transaction_status=self.completed_status
        )
        
        event2 = transaction2.create_accounting_event()
        event2.process()

        self.assertIsInstance(event2, TransferEvent)
        self.assertEqual(event2.event_type, self.transfer_event_type)
        self.assertEqual(event2.from_account, self.account1)
        self.assertEqual(event2.to_account, self.account2)
        self.assertEqual(event2.amount.amount, Decimal('75.00'))
