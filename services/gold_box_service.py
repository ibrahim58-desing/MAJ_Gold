"""
Gold Box Service — manage GoldBoxStock, GoldBoxIssue, GoldBoxDailyBalance.
"""
from database.models.gold_box import GoldBoxStock, GoldBoxIssue, GoldBoxDailyBalance
from services.base_service import BaseService
from sqlalchemy import func


class GoldBoxService(BaseService):

    # ─── Stock (IN) ───────────────────────────────────────────────────────────
    @staticmethod
    def get_stock_entries(start_date=None, end_date=None):
        with GoldBoxService.get_session() as db:
            q = db.query(GoldBoxStock)
            if start_date:
                q = q.filter(GoldBoxStock.added_date >= start_date)
            if end_date:
                q = q.filter(GoldBoxStock.added_date <= end_date)
            items = q.order_by(GoldBoxStock.added_date.desc()).all()
            db.expunge_all()
            return items

    @staticmethod
    def add_stock(added_date, source: str, weight_added_g: float,
                  source_id: int = None, notes: str = None):
        with GoldBoxService.get_session() as db:
            s = GoldBoxStock(added_date=added_date, source=source,
                             source_id=source_id, weight_added_g=weight_added_g,
                             notes=notes)
            db.add(s)
            db.flush()
            db.refresh(s)
            db.expunge(s)
            return s

    @staticmethod
    def delete_stock(stock_id: int):
        with GoldBoxService.get_session() as db:
            s = db.query(GoldBoxStock).get(stock_id)
            if s:
                db.delete(s)

    # ─── Issues (OUT) ─────────────────────────────────────────────────────────
    @staticmethod
    def get_issues(worker_id=None, start_date=None, end_date=None, process=None):
        with GoldBoxService.get_session() as db:
            q = db.query(GoldBoxIssue)
            if worker_id:
                q = q.filter(GoldBoxIssue.worker_id == worker_id)
            if start_date:
                q = q.filter(GoldBoxIssue.issued_date >= start_date)
            if end_date:
                q = q.filter(GoldBoxIssue.issued_date <= end_date)
            if process:
                q = q.filter(GoldBoxIssue.process == process)
            items = q.order_by(GoldBoxIssue.issued_date.desc()).all()
            for item in items:
                _ = item.worker.name if item.worker else None
            db.expunge_all()
            return items

    @staticmethod
    def create_issue(issued_date, worker_id: int, process: str,
                     weight_issued_g: float, weight_returned_g: float = 0.0,
                     pcs_issued: int = 0, notes: str = None):
        net = max(0.0, weight_issued_g - weight_returned_g)
        with GoldBoxService.get_session() as db:
            issue = GoldBoxIssue(
                issued_date=issued_date,
                worker_id=worker_id,
                process=process,
                weight_issued_g=weight_issued_g,
                weight_returned_g=weight_returned_g,
                net_used_g=net,
                pcs_issued=pcs_issued,
                notes=notes,
            )
            db.add(issue)
            db.flush()
            db.refresh(issue)
            db.expunge(issue)
            return issue

    @staticmethod
    def update_issue(issue_id: int, **kwargs):
        with GoldBoxService.get_session() as db:
            i = db.query(GoldBoxIssue).get(issue_id)
            if not i:
                raise ValueError("Issue not found")
            for k, v in kwargs.items():
                setattr(i, k, v)
            i.net_used_g = max(0.0, i.weight_issued_g - i.weight_returned_g)

    @staticmethod
    def delete_issue(issue_id: int):
        with GoldBoxService.get_session() as db:
            i = db.query(GoldBoxIssue).get(issue_id)
            if i:
                db.delete(i)

    # ─── Daily Balance ────────────────────────────────────────────────────────
    @staticmethod
    def get_daily_balances(start_date=None, end_date=None):
        with GoldBoxService.get_session() as db:
            q = db.query(GoldBoxDailyBalance)
            if start_date:
                q = q.filter(GoldBoxDailyBalance.balance_date >= start_date)
            if end_date:
                q = q.filter(GoldBoxDailyBalance.balance_date <= end_date)
            items = q.order_by(GoldBoxDailyBalance.balance_date.desc()).all()
            db.expunge_all()
            return items

    @staticmethod
    def upsert_daily_balance(balance_date, opening_g: float, total_in_g: float,
                              total_out_g: float, physical_g: float = None, notes: str = None):
        """Create or update daily balance. Closing = opening + in - out."""
        closing = opening_g + total_in_g - total_out_g
        sys_diff = (closing - physical_g) if physical_g is not None else None
        with GoldBoxService.get_session() as db:
            existing = db.query(GoldBoxDailyBalance).filter_by(balance_date=balance_date).first()
            if existing:
                existing.opening_g = opening_g
                existing.total_in_g = total_in_g
                existing.total_out_g = total_out_g
                existing.closing_g = closing
                existing.physical_g = physical_g
                existing.system_diff_g = sys_diff
                existing.notes = notes
            else:
                b = GoldBoxDailyBalance(
                    balance_date=balance_date,
                    opening_g=opening_g,
                    total_in_g=total_in_g,
                    total_out_g=total_out_g,
                    closing_g=closing,
                    physical_g=physical_g,
                    system_diff_g=sys_diff,
                    notes=notes,
                )
                db.add(b)

    @staticmethod
    def get_current_balance():
        """Return latest closing balance."""
        with GoldBoxService.get_session() as db:
            row = db.query(GoldBoxDailyBalance).order_by(
                GoldBoxDailyBalance.balance_date.desc()
            ).first()
            if row:
                val = row.closing_g
                db.expunge(row)
                return val
            return 0.0
