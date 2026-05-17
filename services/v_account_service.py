"""V Account Service — VAccountEntry and VAccountDailyBalance."""
from database.models.v_account import VAccountEntry, VAccountDailyBalance
from services.base_service import BaseService
from sqlalchemy import func


class VAccountService(BaseService):

    @staticmethod
    def get_entries(worker_id=None, start_date=None, end_date=None):
        with VAccountService.get_session() as db:
            q = db.query(VAccountEntry)
            if worker_id: q = q.filter(VAccountEntry.worker_id == worker_id)
            if start_date: q = q.filter(VAccountEntry.entry_date >= start_date)
            if end_date: q = q.filter(VAccountEntry.entry_date <= end_date)
            items = q.order_by(VAccountEntry.entry_date, VAccountEntry.id).all()
            for i in items:
                _ = i.worker.name if i.worker else None
            db.expunge_all(); return items

    @staticmethod
    def create_entry(entry_date, worker_id, particular, debit_g=0.0, debit_pcs=0,
                     credit_g=0.0, credit_pcs=0, prev_balance=0.0,
                     voucher_ref=None, notes=None):
        balance = prev_balance + debit_g - credit_g
        with VAccountService.get_session() as db:
            e = VAccountEntry(
                entry_date=entry_date, worker_id=worker_id, particular=particular,
                debit_g=debit_g, debit_pcs=debit_pcs, credit_g=credit_g,
                credit_pcs=credit_pcs, balance_g=balance,
                voucher_ref=voucher_ref, notes=notes,
            )
            db.add(e); db.flush(); return e.id

    @staticmethod
    def update_entry(entry_id, **kwargs):
        with VAccountService.get_session() as db:
            e = db.query(VAccountEntry).get(entry_id)
            if not e: raise ValueError("Not found")
            for k, v in kwargs.items(): setattr(e, k, v)

    @staticmethod
    def delete_entry(entry_id):
        with VAccountService.get_session() as db:
            e = db.query(VAccountEntry).get(entry_id)
            if e: db.delete(e)

    @staticmethod
    def get_daily_balances(start_date=None, end_date=None):
        with VAccountService.get_session() as db:
            q = db.query(VAccountDailyBalance)
            if start_date: q = q.filter(VAccountDailyBalance.balance_date >= start_date)
            if end_date: q = q.filter(VAccountDailyBalance.balance_date <= end_date)
            items = q.order_by(VAccountDailyBalance.balance_date.desc()).all()
            db.expunge_all(); return items

    @staticmethod
    def upsert_daily_balance(balance_date, opening_g, total_in_g, total_out_g,
                              physical_g=None, notes=None):
        closing = opening_g + total_in_g - total_out_g
        sys_diff = (closing - physical_g) if physical_g is not None else None
        with VAccountService.get_session() as db:
            existing = db.query(VAccountDailyBalance).filter_by(balance_date=balance_date).first()
            if existing:
                existing.opening_g = opening_g; existing.total_in_g = total_in_g
                existing.total_out_g = total_out_g; existing.closing_g = closing
                existing.physical_g = physical_g; existing.sys_diff_g = sys_diff
            else:
                db.add(VAccountDailyBalance(
                    balance_date=balance_date, opening_g=opening_g,
                    total_in_g=total_in_g, total_out_g=total_out_g,
                    closing_g=closing, physical_g=physical_g,
                    sys_diff_g=sys_diff, notes=notes,
                ))

    @staticmethod
    def get_totals(worker_id=None):
        with VAccountService.get_session() as db:
            q = db.query(
                func.sum(VAccountEntry.debit_g).label("dr"),
                func.sum(VAccountEntry.credit_g).label("cr"),
                func.sum(VAccountEntry.debit_pcs).label("dr_pcs"),
                func.sum(VAccountEntry.credit_pcs).label("cr_pcs"),
            )
            if worker_id: q = q.filter(VAccountEntry.worker_id == worker_id)
            row = q.first()
            return {
                "total_dr": float(row.dr or 0), "total_cr": float(row.cr or 0),
                "total_dr_pcs": int(row.dr_pcs or 0), "total_cr_pcs": int(row.cr_pcs or 0),
                "balance": float((row.dr or 0) - (row.cr or 0)),
            }
