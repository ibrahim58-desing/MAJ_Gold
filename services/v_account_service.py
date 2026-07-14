"""V Account Service — VAccountEntry and VAccountDailyBalance."""
from database.models.v_account import VAccountEntry, VAccountDailyBalance
from services.base_service import BaseService
from services.gold_box_service import GoldBoxService
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
    def _prev_balance(db, worker_id):
        last = (
            db.query(VAccountEntry)
            .filter(VAccountEntry.worker_id == worker_id)
            .order_by(VAccountEntry.entry_date.desc(), VAccountEntry.id.desc())
            .first()
        )
        return last.balance_g if last else 0.0

    @staticmethod
    def create_entry(entry_date, worker_id, particular, debit_g=0.0, debit_pcs=0,
                     credit_g=0.0, credit_pcs=0, prev_balance=0.0,
                     voucher_ref=None, notes=None):
        balance = prev_balance + debit_g - credit_g
        with VAccountService.get_session() as db:
            e = VAccountEntry(
                entry_date=entry_date, worker_id=worker_id, particular=particular,
                debit_g=debit_g, debit_pcs=debit_pcs, credit_g=credit_g,
                credit_pcs=credit_pcs, balance_g=balance, source_type="MANUAL",
                status="closed", voucher_ref=voucher_ref, notes=notes,
            )
            db.add(e); db.flush(); return e.id

    @staticmethod
    def create_manual_faceting_entry(entry_date, worker_id, weight_g, qty_baby=0,
                                      qty_normal=0, qty_30inch=0, notes=None):
        """Worker hands over faceted gold (pics + weight), entered by hand —
        not linked to a specific FacetingBatch record. Carries the Baby/
        Normal/30" tally. This gold genuinely has a further loss (final
        handling/packing), so it stays open until Edited with the returned
        weight — mirrors the old Wire two-step pattern."""
        with VAccountService.get_session() as db:
            prev = VAccountService._prev_balance(db, worker_id)
            balance = prev + weight_g
            e = VAccountEntry(
                entry_date=entry_date, worker_id=worker_id, particular="Faceting Output",
                debit_g=weight_g, balance_g=balance,
                source_type="FACETING", status="open",
                qty_baby=qty_baby, qty_normal=qty_normal, qty_30inch=qty_30inch,
                notes=notes,
            )
            db.add(e); db.flush(); return e.id

    @staticmethod
    def close_faceting_entry(entry_id, return_date, returned_weight_g, notes=None):
        """Record the faceted gold actually returned and compute the loss."""
        with VAccountService.get_session() as db:
            entry = db.query(VAccountEntry).get(entry_id)
            if not entry: raise ValueError("Entry not found")
            if entry.source_type != "FACETING" or entry.status != "open":
                raise ValueError("Entry is not an open Faceting entry")

            loss_g = max(0.0, entry.debit_g - returned_weight_g)
            loss_pct = (loss_g / entry.debit_g * 100) if entry.debit_g > 0 else 0.0

            prev = VAccountService._prev_balance(db, entry.worker_id)
            balance = prev - returned_weight_g
            credit = VAccountEntry(
                entry_date=return_date, worker_id=entry.worker_id, particular="Faceting Return",
                credit_g=returned_weight_g, balance_g=balance,
                source_type="FACETING", status="closed", linked_entry_id=entry.id,
                loss_g=loss_g, loss_pct=loss_pct, notes=notes,
            )
            db.add(credit)
            entry.status = "closed"
            db.flush()
            credit_id = credit.id

        if loss_g > 0:
            GoldBoxService.add_stock(
                added_date=return_date, source="VACCOUNT_FACETING", source_id=entry_id,
                weight_added_g=round(loss_g, 3),
                notes=f"V Account faceting loss (entry #{entry_id})",
            )

        return {"id": credit_id, "loss_g": loss_g, "loss_pct": loss_pct, "loss_alert": loss_pct > 2.0}

    @staticmethod
    def create_wire_draw_entry(entry_date, worker_id, weight_g, notes=None):
        """Worker draws raw wire (no pics) for making hooks — it's consumed
        into the finished product, not weighed back in, so there's no loss
        concept here: a single closed debit entry."""
        with VAccountService.get_session() as db:
            prev = VAccountService._prev_balance(db, worker_id)
            balance = prev + weight_g
            e = VAccountEntry(
                entry_date=entry_date, worker_id=worker_id, particular="Wire Draw",
                debit_g=weight_g, balance_g=balance,
                source_type="WIRE", status="closed", notes=notes,
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
