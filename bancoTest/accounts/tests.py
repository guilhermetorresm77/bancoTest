from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from .models import Currency, Money, AccountType, Account, Customer, EventType, EntryType, ServiceAgreement, DepositoAE, SaqueAE, DepositoPR, SaquePR, TaxEvent, AmountAdd

class BankSystemTestCase(TestCase):
    def setUp(self):
        # Criar moeda
        self.currency = Currency.objects.create(code='BRL', name='Real Brasileiro')
        
        # Criar tipos de conta e entrada
        self.account_type = AccountType.objects.create(name='Conta Corrente')
        self.deposit_entry_type = EntryType.objects.create(name='Depósito', account_type=self.account_type)
        self.withdrawal_entry_type = EntryType.objects.create(name='Saque', account_type=self.account_type)
        tax_entry_type = EntryType.objects.create(name='Taxação', account_type=self.account_type)

        # Criar tipos de evento
        self.deposit_event_type = EventType.objects.create(name='Depósito')
        self.withdrawal_event_type = EventType.objects.create(name='Saque')
        self.tax_event_type = EventType.objects.create(name='Taxa')
        
        # Criar acordo de serviço
        self.service_agreement = ServiceAgreement.objects.create(rate=Decimal('10.00'))

        # Criar regras de postagem
        self.depositoPR = DepositoPR.objects.create(
            service_agreement=self.service_agreement,
            event_type=self.deposit_event_type,
            entry_type=self.deposit_entry_type,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1)
        )

        self.saquePR = SaquePR.objects.create(
            service_agreement=self.service_agreement,
            event_type=self.withdrawal_event_type,
            entry_type=self.withdrawal_entry_type,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1)
        )

        """self.tax_post_rule = AmountAdd.objects.create(
            service_agreement=self.service_agreement,
            event_type=new_event_type,
            entry_type=new_entry_type,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1),
            
            multiplier=Decimal("0.10"),
            fixedFee=Money.objects.create(amount=Decimal('2.00'), currency=self.currency)
        )"""
        self.service_agreement.save()
        
        # Criar cliente e conta
        self.customer = Customer.objects.create(name='João Silva', service_agreement=self.service_agreement)
        self.account = Account.objects.create(name='Conta do João', account_type=self.account_type, currency=self.currency)
        self.customer.accounts.add(self.account)

    def test_account_creation(self):
        self.assertEqual(self.account.balance(), Decimal('0.00'))
        self.assertEqual(str(self.account), 'Conta do João')

    def test_deposit(self):
        deposit_amount = Money.objects.create(amount=Decimal('100.00'), currency=self.currency)
        deposit_event = DepositoAE.objects.create(
            event_type=self.deposit_event_type,
            when_occurred=timezone.now(),
            when_noticed=timezone.now(),
            customer=self.customer,
            account=self.account,
            amount=deposit_amount
        )
        deposit_event.process()
        
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance(), Decimal('100.00'))

    def test_withdrawal(self):
        # Primeiro, fazemos um depósito
        deposit_amount = Money.objects.create(amount=Decimal('100.00'), currency=self.currency)
        deposit_event = DepositoAE.objects.create(
            event_type=self.deposit_event_type,
            when_occurred=timezone.now(),
            when_noticed=timezone.now(),
            customer=self.customer,
            account=self.account,
            amount=deposit_amount
        )
        deposit_event.process()
        
        # Agora, fazemos um saque
        withdrawal_amount = Money.objects.create(amount=Decimal('50.00'), currency=self.currency)
        withdrawal_event = SaqueAE.objects.create(
            event_type=self.withdrawal_event_type,
            when_occurred=timezone.now(),
            when_noticed=timezone.now(),
            customer=self.customer,
            account=self.account,
            amount=withdrawal_amount
        )
        withdrawal_event.process()
        
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance(), Decimal('50.00'))

    def test_insufficient_funds(self):
        withdrawal_amount = Money.objects.create(amount=Decimal('50.00'), currency=self.currency)
        withdrawal_event = SaqueAE.objects.create(
            event_type=self.withdrawal_event_type,
            when_occurred=timezone.now(),
            when_noticed=timezone.now(),
            customer=self.customer,
            account=self.account,
            amount=withdrawal_amount
        )
        
        with self.assertRaises(ValueError):
            withdrawal_event.process()

    def test_multiple_transactions(self):
        # Depósito inicial
        deposit_amount1 = Money.objects.create(amount=Decimal('100.00'), currency=self.currency)
        deposit_event1 = DepositoAE.objects.create(
            event_type=self.deposit_event_type,
            when_occurred=timezone.now(),
            when_noticed=timezone.now(),
            customer=self.customer,
            account=self.account,
            amount=deposit_amount1
        )
        deposit_event1.process()
        
        # Saque
        withdrawal_amount = Money.objects.create(amount=Decimal('30.00'), currency=self.currency)
        withdrawal_event = SaqueAE.objects.create(
            event_type=self.withdrawal_event_type,
            when_occurred=timezone.now(),
            when_noticed=timezone.now(),
            customer=self.customer,
            account=self.account,
            amount=withdrawal_amount
        )
        withdrawal_event.process()
        
        # Outro depósito
        deposit_amount2 = Money.objects.create(amount=Decimal('50.00'), currency=self.currency)
        deposit_event2 = DepositoAE.objects.create(
            event_type=self.deposit_event_type,
            when_occurred=timezone.now(),
            when_noticed=timezone.now(),
            customer=self.customer,
            account=self.account,
            amount=deposit_amount2
        )
        deposit_event2.process()
        
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance(), Decimal('120.00'))

    def test_executar_evento_2_vezes(self):
        deposit_amount = Money.objects.create(amount=Decimal('100.00'), currency=self.currency)
        deposit_event = DepositoAE.objects.create(
            event_type=self.deposit_event_type,
            when_occurred=timezone.now(),
            when_noticed=timezone.now(),
            customer=self.customer,
            account=self.account,
            amount=deposit_amount
        )
        deposit_event.process()
        with self.assertRaises(ValueError):
            deposit_event.process()  # Executa o evento 2 vezes

    """def test_new_posting_rule(self):

        tax = Decimal("10.00")

        tax_event = TaxEvent.objects.create(
            event_type=new_event_type,
            when_occurred=timezone.now(),
            when_noticed=timezone.now(),
            customer=self.customer,
            account=self.account,
            tax_rate = Decimal("5.00"),
            amount = Money.objects.create(amount=tax, currency=self.currency)
        )
        tax_event.process()
        
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance(), Decimal('102.00'))  # 10% de taxa + 2.00 de taxa fixa = 12.00
"""