# transactions/models.py
from django.db import models

from accounts.models import (
    AccountingEvent,
    PostingRule,
    EventType,
    Customer,
    ServiceAgreement,
    Money,
    Entry,
    Account,
    Customer,
    )

class TransactionType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    
class TransactionStatus(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Transaction(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    from_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transactions_from')
    to_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transactions_to', null=True, blank=True)
    amount = models.ForeignKey(Money, on_delete=models.PROTECT)
    transaction_type = models.ForeignKey(TransactionType, on_delete=models.PROTECT)
    transaction_status = models.ForeignKey(TransactionStatus, on_delete=models.PROTECT)
    description = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.status}"

    def create_accounting_event(self):
        event_type = EventType.objects.get(name=self.transaction_type.name)
        if self.transaction_type.name == 'DEPOSIT':
            return DepositEvent.objects.create(
                event_type=event_type,
                when_occurred=self.timestamp,
                when_noticed=self.timestamp, # Rever quando o evento é executado, atualmente é quando ele é criado
                customer=self.customer,
                account=self.from_account,
                amount=self.amount
            )
        elif self.transaction_type.name == 'WITHDRAWAL':
            return WithdrawalEvent.objects.create(
                event_type=event_type,
                when_occurred=self.timestamp,
                when_noticed=self.timestamp,
                customer=self.customer,
                account=self.from_account,
                amount=self.amount,
            )
        elif self.transaction_type.name == 'TRANSFER':
            return TransferEvent.objects.create(
                event_type=event_type,
                when_occurred=self.timestamp,
                when_noticed=self.timestamp,
                customer=self.customer,
                from_account=self.from_account,
                to_account=self.to_account,
                amount=self.amount,
            )

class DepositEvent(AccountingEvent):
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    amount = models.ForeignKey(Money, on_delete=models.PROTECT)

class WithdrawalEvent(AccountingEvent):
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    amount = models.ForeignKey(Money, on_delete=models.PROTECT)

class TransferEvent(AccountingEvent):
    from_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transfer_from')
    to_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transfer_to')
    amount = models.ForeignKey(Money, on_delete=models.PROTECT)

class DepositPR(PostingRule):
    def calculate_amount(self, event):
        return event.amount

class WithdrawalPR(PostingRule):
    def calculate_amount(self, event):
        return event.amount.negate()

class TransferPR(PostingRule):
    def calculate_amount(self, event):
        # Cria duas entradas: uma negativa para a conta de origem e uma positiva para a conta de destino
        from_acount_amount = event.amount.negate()
        to_account_amount = event.amount

        self.make_entry_with_account(event, from_acount_amount, event.from_account)
        self.make_entry_with_account(event, to_account_amount, event.to_account)

        return None
    
    def make_entry_with_account(self, event, amount, account):
        entry = Entry.objects.create(
            account=account,
            entry_type=self.entry_type,
            amount=amount,
            date=event.when_noticed
        )
        print(f"Entrada: {self.entry_type} Valor: {amount} Evento: {event.event_type}")
        #event.customer.add_entry(entry)
        event.resulting_entries.add(entry)
       
class TransactionLog(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='logs')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log for {self.transaction} at {self.timestamp}"
