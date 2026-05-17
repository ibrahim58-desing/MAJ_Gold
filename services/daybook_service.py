"""
Daybook Service — CRUD for DaybookEntry (central double-entry ledger).
"""
from datetime import date as date_type
from database.models.base import SessionLocal
from database.models.daybook import DaybookEntry
from services.base_service import BaseService
from sqlalchemy import func


class DaybookService(BaseService):

    @staticmethod
    def next_serial_no() -> int:
        """Get next available serial number."""
        with DaybookService.get_session() as db:
            max_sno = db.query(func.max(DaybookEntry.serial_no)).scalar()
            return (max_sno or 55419) + 1

    @staticmethod
    def get_entries(start_date=None, end_date=None, ledger_account=None,
                    group_type=None, search=None, limit=500, offset=0):
        with DaybookService.get_session() as db:
            q = db.query(DaybookEntry)
            if start_date:
                q = q.filter(DaybookEntry.entry_date >= start_date)
            if end_date:
                q = q.filter(DaybookEntry.entry_date <= end_date)
            if ledger_account:
                q = q.filter(DaybookEntry.ledger_account.ilike(f"%{ledger_account}%"))
            if group_type:
                q = q.filter(DaybookEntry.group_type == group_type)
            if search:
                q = q.filter(
                    DaybookEntry.particular.ilike(f"%{search}%") |
                    DaybookEntry.ledger_account.ilike(f"%{search}%") |
                    DaybookEntry.notes.ilike(f"%{search}%")
                )
            total = q.count()
            items = q.order_by(DaybookEntry.serial_no.desc()).offset(offset).limit(limit).all()
            db.expunge_all()
            return items, total

    @staticmethod
    def get_entry_by_id(entry_id: int):
        with DaybookService.get_session() as db:
            e = db.query(DaybookEntry).get(entry_id)
            if e:
                db.expunge(e)
            return e

    @staticmethod
    def create_double_entry(entry_date, debit_account: str, credit_account: str,
                            weight: float, pcs: int = 0, group_type: str = None,
                            source_process: str = None, notes: str = None,
                            voucher_ref: str = None) -> tuple:
        """
        Create a double-entry pair in the daybook.
        Returns (debit_entry, credit_entry).
        """
        with DaybookService.get_session() as db:
            sno1 = (db.query(func.max(DaybookEntry.serial_no)).scalar() or 55419) + 1
            sno2 = sno1 + 1
            vref = voucher_ref or f"V{sno1:06d}"

            debit_row = DaybookEntry(
                entry_date=entry_date,
                ledger_account=debit_account,
                particular=credit_account,
                debit_wt=weight,
                debit_pcs=pcs,
                credit_wt=0.0,
                credit_pcs=0,
                serial_no=sno1,
                voucher_ref=vref,
                group_type=group_type,
                source_process=source_process,
                notes=notes,
            )
            credit_row = DaybookEntry(
                entry_date=entry_date,
                ledger_account=credit_account,
                particular=debit_account,
                debit_wt=0.0,
                debit_pcs=0,
                credit_wt=weight,
                credit_pcs=pcs,
                serial_no=sno2,
                voucher_ref=vref,
                group_type=group_type,
                source_process=source_process,
                notes=notes,
            )
            db.add(debit_row)
            db.add(credit_row)
            db.flush()
            db.refresh(debit_row)
            db.refresh(credit_row)
            db.expunge_all()
            return debit_row, credit_row

    @staticmethod
    def update_entry(entry_id: int, **kwargs):
        """Update a daybook entry field(s). Marks is_edited=True."""
        from datetime import datetime
        with DaybookService.get_session() as db:
            e = db.query(DaybookEntry).get(entry_id)
            if not e:
                raise ValueError(f"Entry {entry_id} not found")
            for k, v in kwargs.items():
                setattr(e, k, v)
            e.is_edited = True
            e.edited_at = datetime.utcnow()

    @staticmethod
    def delete_entry(entry_id: int):
        with DaybookService.get_session() as db:
            e = db.query(DaybookEntry).get(entry_id)
            if e:
                db.delete(e)

    @staticmethod
    def get_group_types():
        with DaybookService.get_session() as db:
            rows = db.query(DaybookEntry.group_type).distinct().all()
            return [r[0] for r in rows if r[0]]

    @staticmethod
    def get_summary_by_date(entry_date=None):
        """Sum of debit/credit for a given date."""
        with DaybookService.get_session() as db:
            q = db.query(
                func.sum(DaybookEntry.debit_wt).label("total_debit"),
                func.sum(DaybookEntry.credit_wt).label("total_credit"),
                func.count(DaybookEntry.id).label("count"),
            )
            if entry_date:
                q = q.filter(DaybookEntry.entry_date == entry_date)
            row = q.first()
            return {
                "total_debit":  float(row.total_debit or 0),
                "total_credit": float(row.total_credit or 0),
                "count":        int(row.count or 0),
            }
