"""Wire & Sheet Service — single output type per batch (dye / wire / strip)."""
from datetime import datetime
from sqlalchemy import func as sa_func

from database.models.base import SessionLocal
from database.models.process import WireSheetBatch
from database.models.stock import MeltBatch
from database.models.daybook import DaybookEntry


def _get_type_attr():
    mapper_attrs = [c.key for c in DaybookEntry.__mapper__.column_attrs]
    for candidate in ['type', 'entry_type', 'transaction_type', 'entry_kind']:
        if candidate in mapper_attrs:
            return candidate
    return None


def get_total_rod_received():
    """Sum of all melt-batch after-melt weights (weight_out_916_g)."""
    session = SessionLocal()
    try:
        total = session.query(
            sa_func.coalesce(sa_func.sum(MeltBatch.weight_out_916_g), 0.0)
        ).scalar()
        return round(total, 3)
    finally:
        session.close()


def create_batch(data: dict) -> dict:
    session = SessionLocal()
    try:
        # ── daybook entry ──
        sno = session.query(sa_func.max(DaybookEntry.serial_no)).scalar()
        serial_no = (sno or 55419) + 1

        type_attr = _get_type_attr()
        db_kwargs = {
            "entry_date":     data["batch_date"],
            "ledger_account": "Wire & Sheet",
            "particular":     f"Wire & Sheet — {data['batch_type']} — {data['rod_weight_g']:.3f}g",
            "debit_wt":       data["rod_weight_g"],
            "serial_no":      serial_no,
            "group_type":     "WIRE_SHEET",
            "source_process": "wire_sheet_batches",
            "notes":          data.get("notes", ""),
        }
        if type_attr:
            db_kwargs[type_attr] = "WIRE_SHEET"

        daybook = DaybookEntry(**db_kwargs)
        session.add(daybook)
        session.flush()

        # ── batch row ──
        batch = WireSheetBatch(
            batch_date      = data["batch_date"],
            batch_type      = data["batch_type"],
            rod_weight_g    = data["rod_weight_g"],
            output_weight_g = 0.0,
            loss_g          = 0.0,
            loss_pct        = 0.0,
            status          = "pending",
            daybook_sno     = daybook.serial_no,
            notes           = data.get("notes", ""),
            # legacy NOT-NULL columns
            weight_in_g     = data["rod_weight_g"],
            weight_out_g    = 0.0,
            melt_batch_id   = 0,
        )
        session.add(batch)
        session.commit()
        return {"id": batch.id, "success": True}

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def complete_batch(batch_id: int, output_weight_g: float) -> dict:
    session = SessionLocal()
    try:
        batch = session.query(WireSheetBatch).filter(
            WireSheetBatch.id == batch_id
        ).first()
        if not batch:
            raise ValueError(f"Batch #{batch_id} not found")
        if batch.status == "completed":
            raise ValueError(f"Batch #{batch_id} is already completed")

        rod = batch.rod_weight_g or 0.0
        loss = rod - output_weight_g
        loss_pct = (loss / rod * 100) if rod > 0 else 0.0

        batch.output_weight_g = output_weight_g
        batch.weight_out_g    = output_weight_g   # legacy
        batch.loss_g          = round(loss, 3)
        batch.loss_pct        = round(loss_pct, 2)
        batch.status          = "completed"

        session.commit()
        return {
            "id": batch.id,
            "success": True,
            "loss_pct": round(loss_pct, 2),
        }

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def get_all_batches() -> list:
    session = SessionLocal()
    try:
        rows = (
            session.query(WireSheetBatch)
            .order_by(WireSheetBatch.batch_date.desc(), WireSheetBatch.id.desc())
            .all()
        )
        return [
            {
                "id":              b.id,
                "batch_date":      b.batch_date,
                "batch_type":      b.batch_type or "wire",
                "rod_weight_g":    b.rod_weight_g or 0.0,
                "output_weight_g": b.output_weight_g or 0.0,
                "loss_g":          b.loss_g or 0.0,
                "loss_pct":        b.loss_pct or 0.0,
                "status":          b.status or "pending",
                "notes":           b.notes,
            }
            for b in rows
        ]
    finally:
        session.close()


def get_batch_by_id(batch_id: int) -> dict | None:
    session = SessionLocal()
    try:
        b = session.query(WireSheetBatch).filter(
            WireSheetBatch.id == batch_id
        ).first()
        if not b:
            return None
        return {
            "id":              b.id,
            "batch_date":      b.batch_date,
            "batch_type":      b.batch_type or "wire",
            "rod_weight_g":    b.rod_weight_g or 0.0,
            "output_weight_g": b.output_weight_g or 0.0,
            "loss_g":          b.loss_g or 0.0,
            "loss_pct":        b.loss_pct or 0.0,
            "status":          b.status or "pending",
            "notes":           b.notes,
        }
    finally:
        session.close()
