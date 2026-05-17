"""Stock Service — FinishedStock, ChainStock, TagStock, StockSummaryDaily."""
from database.models.stock_register import FinishedStock, ChainStock, TagStock, StockSummaryDaily
from services.base_service import BaseService
from sqlalchemy import func


class StockService(BaseService):

    @staticmethod
    def get_finished_stock(stock_category=None, start_date=None, end_date=None):
        with StockService.get_session() as db:
            q = db.query(FinishedStock)
            if stock_category: q = q.filter(FinishedStock.stock_category == stock_category)
            if start_date: q = q.filter(FinishedStock.stocked_date >= start_date)
            if end_date: q = q.filter(FinishedStock.stocked_date <= end_date)
            items = q.order_by(FinishedStock.stocked_date.desc()).all()
            db.expunge_all(); return items

    @staticmethod
    def create_finished_stock(stocked_date, stock_category, weight_in_g, pcs_in,
                               product_type_id=None, design_type_id=None,
                               kambi_batch_id=None, location="MUM", purity="916", notes=None):
        with StockService.get_session() as db:
            fs = FinishedStock(
                stocked_date=stocked_date, stock_category=stock_category,
                product_type_id=product_type_id, design_type_id=design_type_id,
                kambi_batch_id=kambi_batch_id, pcs_in=pcs_in, weight_in_g=weight_in_g,
                pcs_balance=pcs_in, weight_balance_g=weight_in_g,
                location=location, purity=purity, notes=notes,
            )
            db.add(fs); db.flush(); return fs.id

    @staticmethod
    def update_finished_stock(fs_id, **kwargs):
        with StockService.get_session() as db:
            fs = db.query(FinishedStock).get(fs_id)
            if not fs: raise ValueError("Not found")
            for k, v in kwargs.items(): setattr(fs, k, v)

    @staticmethod
    def delete_finished_stock(fs_id):
        with StockService.get_session() as db:
            fs = db.query(FinishedStock).get(fs_id)
            if fs: db.delete(fs)

    @staticmethod
    def get_tot_stock_summary():
        with StockService.get_session() as db:
            rows = db.query(
                FinishedStock.stock_category,
                func.sum(FinishedStock.weight_balance_g).label("wt"),
                func.sum(FinishedStock.pcs_balance).label("pcs"),
            ).group_by(FinishedStock.stock_category).all()
            return [{"category": r[0], "weight": float(r[1] or 0), "pcs": int(r[2] or 0)} for r in rows]

    @staticmethod
    def get_chain_stock(start_date=None, end_date=None, transaction=None):
        with StockService.get_session() as db:
            q = db.query(ChainStock)
            if start_date: q = q.filter(ChainStock.entry_date >= start_date)
            if end_date: q = q.filter(ChainStock.entry_date <= end_date)
            if transaction: q = q.filter(ChainStock.transaction == transaction)
            items = q.order_by(ChainStock.entry_date.desc()).all()
            db.expunge_all(); return items

    @staticmethod
    def create_chain_stock(entry_date, weight_g, pcs, transaction="CREDIT",
                           product_type_id=None, design_type_id=None, notes=None):
        with StockService.get_session() as db:
            db.add(ChainStock(entry_date=entry_date, weight_g=weight_g, pcs=pcs,
                              transaction=transaction, product_type_id=product_type_id,
                              design_type_id=design_type_id, notes=notes))

    @staticmethod
    def get_tag_stock(status=None):
        with StockService.get_session() as db:
            q = db.query(TagStock)
            if status: q = q.filter(TagStock.status == status)
            items = q.order_by(TagStock.tag_no.desc()).all()
            db.expunge_all(); return items

    @staticmethod
    def create_tag(tag_no, tag_date, tagged_weight_g, tagged_pcs, stock_category,
                   location="MUM", product_type_id=None, notes=None):
        with StockService.get_session() as db:
            db.add(TagStock(tag_no=tag_no, tag_date=tag_date, tagged_weight_g=tagged_weight_g,
                            tagged_pcs=tagged_pcs, stock_category=stock_category,
                            location=location, product_type_id=product_type_id,
                            status="TAGGED", notes=notes))

    @staticmethod
    def update_tag_status(tag_id, status, sale_date=None):
        with StockService.get_session() as db:
            t = db.query(TagStock).get(tag_id)
            if t:
                t.status = status
                if sale_date: t.sale_date = sale_date

    @staticmethod
    def get_stock_summary(start_date=None, end_date=None):
        with StockService.get_session() as db:
            q = db.query(StockSummaryDaily)
            if start_date: q = q.filter(StockSummaryDaily.summary_date >= start_date)
            if end_date: q = q.filter(StockSummaryDaily.summary_date <= end_date)
            items = q.order_by(StockSummaryDaily.summary_date.desc()).all()
            db.expunge_all(); return items

    @staticmethod
    def upsert_stock_summary(summary_date, **kwargs):
        with StockService.get_session() as db:
            existing = db.query(StockSummaryDaily).filter_by(summary_date=summary_date).first()
            if existing:
                for k, v in kwargs.items(): setattr(existing, k, v)
            else:
                db.add(StockSummaryDaily(summary_date=summary_date, **kwargs))
