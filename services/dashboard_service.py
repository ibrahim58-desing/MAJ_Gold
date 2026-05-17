"""Dashboard Service — aggregated KPIs for the dashboard page."""
from database.models.base import SessionLocal
from database.models.gold_box import GoldBoxDailyBalance
from database.models.stock_register import FinishedStock, StockSummaryDaily
from database.models.stock import MeltBatch
from database.models.process import GoldsmithBatch, FacetingBatch, KambiBatch
from database.models.daybook import DaybookEntry
from database.models.masters import Worker
from sqlalchemy import func
from datetime import date, timedelta


class DashboardService:

    @staticmethod
    def get_kpis():
        db = SessionLocal()
        try:
            today = date.today()

            # Gold Box current balance
            gb_row = db.query(GoldBoxDailyBalance).order_by(
                GoldBoxDailyBalance.balance_date.desc()).first()
            gold_box_balance = float(gb_row.closing_g) if gb_row else 0.0

            # Finished stock total weight
            fs_row = db.query(func.sum(FinishedStock.weight_balance_g)).scalar()
            finished_stock_wt = float(fs_row or 0)

            # Finished stock total pcs
            fs_pcs = db.query(func.sum(FinishedStock.pcs_balance)).scalar()
            finished_stock_pcs = int(fs_pcs or 0)

            # Total melt batches
            melt_count = db.query(func.count(MeltBatch.id)).scalar() or 0

            # Total goldsmith batches
            gs_count = db.query(func.count(GoldsmithBatch.id)).scalar() or 0

            # Total faceting batches
            fac_count = db.query(func.count(FacetingBatch.id)).scalar() or 0

            # Total kambi batches
            kambi_count = db.query(func.count(KambiBatch.id)).scalar() or 0

            # Today's daybook entries
            today_entries = db.query(func.count(DaybookEntry.id)).filter(
                DaybookEntry.entry_date == today).scalar() or 0

            # Today's debit total
            today_debit = db.query(func.sum(DaybookEntry.debit_wt)).filter(
                DaybookEntry.entry_date == today).scalar() or 0

            # Active workers
            active_workers = db.query(func.count(Worker.id)).filter(
                Worker.is_active == True).scalar() or 0

            # Stock summary per category
            cat_rows = db.query(
                FinishedStock.stock_category,
                func.sum(FinishedStock.weight_balance_g),
                func.sum(FinishedStock.pcs_balance),
            ).group_by(FinishedStock.stock_category).all()
            categories = [{"cat": r[0], "wt": float(r[1] or 0), "pcs": int(r[2] or 0)} for r in cat_rows]

            # Last 7 days daybook activity
            week_ago = today - timedelta(days=6)
            daily_rows = db.query(
                DaybookEntry.entry_date,
                func.sum(DaybookEntry.debit_wt),
                func.count(DaybookEntry.id),
            ).filter(DaybookEntry.entry_date >= week_ago).group_by(
                DaybookEntry.entry_date).order_by(DaybookEntry.entry_date).all()
            daily_activity = [{"date": str(r[0]), "debit": float(r[1] or 0), "count": int(r[2] or 0)}
                              for r in daily_rows]

            return {
                "gold_box_balance": gold_box_balance,
                "finished_stock_wt": finished_stock_wt,
                "finished_stock_pcs": finished_stock_pcs,
                "melt_count": int(melt_count),
                "gs_count": int(gs_count),
                "fac_count": int(fac_count),
                "kambi_count": int(kambi_count),
                "today_entries": int(today_entries),
                "today_debit": float(today_debit),
                "active_workers": int(active_workers),
                "categories": categories,
                "daily_activity": daily_activity,
            }
        finally:
            db.close()
