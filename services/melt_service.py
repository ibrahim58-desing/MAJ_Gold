"""
Melt Service — CRUD for GoldReceipt, MeltBatch, MeltBatchAlloy, SolderReturn.
"""
from database.models.stock import GoldReceipt, MeltBatch, MeltBatchInput, MeltBatchAlloy, SolderReturn
from database.models.masters import Dealer, AlloyType
from services.base_service import BaseService
from sqlalchemy import func


class MeltService(BaseService):

    # ─── Gold Receipts ────────────────────────────────────────────────────────
    @staticmethod
    def get_receipts(dealer_id=None, start_date=None, end_date=None):
        with MeltService.get_session() as db:
            q = db.query(GoldReceipt)
            if dealer_id:
                q = q.filter(GoldReceipt.dealer_id == dealer_id)
            if start_date:
                q = q.filter(GoldReceipt.receipt_date >= start_date)
            if end_date:
                q = q.filter(GoldReceipt.receipt_date <= end_date)
            items = q.order_by(GoldReceipt.receipt_date.desc()).all()
            # load dealer name
            for item in items:
                _ = item.dealer.name if item.dealer else None
            db.expunge_all()
            return items

    @staticmethod
    def create_receipt(receipt_date, dealer_id: int, purity: str,
                       weight_g: float, net_weight_g: float = None,
                       receipt_no: str = None, notes: str = None):
        with MeltService.get_session() as db:
            r = GoldReceipt(
                receipt_date=receipt_date,
                dealer_id=dealer_id,
                purity=purity,
                weight_g=weight_g,
                net_weight_g=net_weight_g or weight_g,
                receipt_no=receipt_no,
                notes=notes,
            )
            db.add(r)
            db.flush()
            db.refresh(r)
            db.expunge(r)
            return r

    @staticmethod
    def update_receipt(receipt_id: int, **kwargs):
        with MeltService.get_session() as db:
            r = db.query(GoldReceipt).get(receipt_id)
            if not r:
                raise ValueError("Receipt not found")
            for k, v in kwargs.items():
                setattr(r, k, v)

    @staticmethod
    def delete_receipt(receipt_id: int):
        with MeltService.get_session() as db:
            r = db.query(GoldReceipt).get(receipt_id)
            if r:
                db.delete(r)

    # ─── Melt Batches ─────────────────────────────────────────────────────────
    @staticmethod
    def get_melt_batches(melt_type=None, start_date=None, end_date=None):
        with MeltService.get_session() as db:
            q = db.query(MeltBatch)
            if melt_type:
                q = q.filter(MeltBatch.melt_type == melt_type)
            if start_date:
                q = q.filter(MeltBatch.batch_date >= start_date)
            if end_date:
                q = q.filter(MeltBatch.batch_date <= end_date)
            items = q.order_by(MeltBatch.batch_date.desc()).all()
            for item in items:
                _ = [a.alloy_type.name for a in item.alloy_additions]
            db.expunge_all()
            return items

    @staticmethod
    def create_melt_batch(batch_date, melt_type: str, weight_in_g: float,
                          weight_out_916_g: float, ng_weight_g: float = 0.0,
                          kambi_weight_g: float = 0.0, worker_id: int = None,
                          product_type_id: int = None, notes: str = None,
                          alloy_additions: list = None):
        """
        alloy_additions: list of {"alloy_type_id": int, "weight_g": float}
        """
        with MeltService.get_session() as db:
            total_alloy = sum(a["weight_g"] for a in (alloy_additions or []))
            gross = weight_in_g + total_alloy
            loss = max(0.0, gross - weight_out_916_g)

            batch = MeltBatch(
                batch_date=batch_date,
                melt_type=melt_type,
                worker_id=worker_id,
                weight_in_g=weight_in_g,
                total_alloy_g=total_alloy,
                gross_weight_g=gross,
                weight_out_916_g=weight_out_916_g,
                ng_weight_g=ng_weight_g,
                kambi_weight_g=kambi_weight_g,
                loss_g=loss,
                product_type_id=product_type_id,
                notes=notes,
            )
            db.add(batch)
            db.flush()

            for a in (alloy_additions or []):
                alloy_row = MeltBatchAlloy(
                    melt_batch_id=batch.id,
                    alloy_type_id=a["alloy_type_id"],
                    weight_g=a["weight_g"],
                )
                db.add(alloy_row)

            db.refresh(batch)
            batch_id = batch.id
        return batch_id

    @staticmethod
    def update_melt_batch(batch_id: int, **kwargs):
        with MeltService.get_session() as db:
            b = db.query(MeltBatch).get(batch_id)
            if not b:
                raise ValueError("Melt batch not found")
            for k, v in kwargs.items():
                setattr(b, k, v)
            # recompute derived fields
            gross = b.weight_in_g + b.total_alloy_g
            b.gross_weight_g = gross
            b.loss_g = max(0.0, gross - b.weight_out_916_g)

    @staticmethod
    def delete_melt_batch(batch_id: int):
        with MeltService.get_session() as db:
            b = db.query(MeltBatch).get(batch_id)
            if b:
                db.delete(b)

    # ─── Solder Returns ───────────────────────────────────────────────────────
    @staticmethod
    def get_solder_returns(source_process=None):
        with MeltService.get_session() as db:
            q = db.query(SolderReturn)
            if source_process:
                q = q.filter(SolderReturn.source_process == source_process)
            items = q.order_by(SolderReturn.returned_date.desc()).all()
            db.expunge_all()
            return items

    @staticmethod
    def create_solder_return(returned_date, source_process: str, weight_g: float,
                             source_batch_id: int = None, product_type_id: int = None,
                             notes: str = None):
        with MeltService.get_session() as db:
            sr = SolderReturn(
                returned_date=returned_date,
                source_process=source_process,
                source_batch_id=source_batch_id,
                weight_g=weight_g,
                product_type_id=product_type_id,
                notes=notes,
            )
            db.add(sr)
