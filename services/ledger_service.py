"""Ledger Service — LedgerAccount and LedgerEntry."""
from database.models.ledger import LedgerAccount, LedgerEntry
from services.base_service import BaseService
from sqlalchemy import func


class LedgerService(BaseService):

    @staticmethod
    def get_accounts(account_type=None, active_only=True):
        with LedgerService.get_session() as db:
            q = db.query(LedgerAccount)
            if account_type: q = q.filter(LedgerAccount.account_type == account_type)
            if active_only: q = q.filter(LedgerAccount.is_active == True)
            items = q.order_by(LedgerAccount.code).all()
            db.expunge_all(); return items

    @staticmethod
    def get_account_by_code(code: str):
        with LedgerService.get_session() as db:
            a = db.query(LedgerAccount).filter_by(code=code).first()
            if a: db.expunge(a)
            return a

    @staticmethod
    def create_account(code, name, account_type, opening_balance_g=0.0,
                       opening_balance_date=None, linked_worker_id=None):
        with LedgerService.get_session() as db:
            a = LedgerAccount(
                code=code.upper().strip(), name=name.strip(),
                account_type=account_type, opening_balance_g=opening_balance_g,
                opening_balance_date=opening_balance_date,
                linked_worker_id=linked_worker_id,
            )
            db.add(a)

    @staticmethod
    def get_entries(account_id=None, account_code=None, start_date=None, end_date=None):
        with LedgerService.get_session() as db:
            q = db.query(LedgerEntry)
            if account_id:
                q = q.filter(LedgerEntry.account_id == account_id)
            elif account_code:
                acct = db.query(LedgerAccount).filter_by(code=account_code).first()
                if acct: q = q.filter(LedgerEntry.account_id == acct.id)
            if start_date: q = q.filter(LedgerEntry.entry_date >= start_date)
            if end_date: q = q.filter(LedgerEntry.entry_date <= end_date)
            items = q.order_by(LedgerEntry.entry_date, LedgerEntry.id).all()
            db.expunge_all(); return items

    @staticmethod
    def create_entry(account_id, entry_date, particular, debit_g=0.0, debit_pcs=0,
                     credit_g=0.0, credit_pcs=0, prev_balance=0.0,
                     voucher_ref=None, source_process=None, notes=None):
        balance = prev_balance + debit_g - credit_g
        with LedgerService.get_session() as db:
            e = LedgerEntry(
                account_id=account_id, entry_date=entry_date, particular=particular,
                debit_g=debit_g, debit_pcs=debit_pcs, credit_g=credit_g,
                credit_pcs=credit_pcs, balance_g=balance,
                voucher_ref=voucher_ref, source_process=source_process, notes=notes,
            )
            db.add(e); db.flush(); return e.id

    @staticmethod
    def update_entry(entry_id, **kwargs):
        with LedgerService.get_session() as db:
            e = db.query(LedgerEntry).get(entry_id)
            if not e: raise ValueError("Not found")
            for k, v in kwargs.items(): setattr(e, k, v)

    @staticmethod
    def delete_entry(entry_id):
        with LedgerService.get_session() as db:
            e = db.query(LedgerEntry).get(entry_id)
            if e: db.delete(e)

    @staticmethod
    def get_account_totals(account_id):
        with LedgerService.get_session() as db:
            row = db.query(
                func.sum(LedgerEntry.debit_g).label("total_dr"),
                func.sum(LedgerEntry.credit_g).label("total_cr"),
                func.sum(LedgerEntry.debit_pcs).label("total_dr_pcs"),
                func.sum(LedgerEntry.credit_pcs).label("total_cr_pcs"),
            ).filter(LedgerEntry.account_id == account_id).first()
            return {
                "total_dr": float(row.total_dr or 0),
                "total_cr": float(row.total_cr or 0),
                "total_dr_pcs": int(row.total_dr_pcs or 0),
                "total_cr_pcs": int(row.total_cr_pcs or 0),
                "balance": float((row.total_dr or 0) - (row.total_cr or 0)),
            }
