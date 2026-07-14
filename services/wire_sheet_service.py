"""Wire & Sheet Service — handles rod conversion to dye, wire, and strips."""
from datetime import datetime
from sqlalchemy import func as sa_func

from database.models.base import SessionLocal
from database.models.process import WireSheetBatch
from database.models.stock import MeltBatch
from database.models.daybook import DaybookEntry
from database.models.masters import Team, Worker
from services.gold_box_service import GoldBoxService


def _get_type_attr():
    mapper_attrs = [c.key for c in DaybookEntry.__mapper__.column_attrs]
    for candidate in ['type', 'entry_type', 'transaction_type', 'entry_kind']:
        if candidate in mapper_attrs:
            return candidate
    return None

def clear_test_data():
    session = SessionLocal()
    try:
        session.query(WireSheetBatch).delete()
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

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
            "particular":     f"Wire & Sheet Issue — {data['rod_weight_g']:.3f}g",
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
        assigned_to_type = data.get("assigned_to_type", "INDIVIDUAL")
        batch = WireSheetBatch(
            batch_date      = data["batch_date"],
            batch_type      = "pending",
            rod_weight_g    = data["rod_weight_g"],
            output_weight_g = 0.0,
            dye_weight_g    = 0.0,
            wire_weight_g   = 0.0,
            strips_weight_g = 0.0,
            loss_g          = 0.0,
            loss_pct        = 0.0,
            status          = "pending",
            assigned_to_type= assigned_to_type,
            team_id         = data.get("team_id"),
            daybook_sno     = daybook.serial_no,
            notes           = data.get("notes", ""),
            # legacy NOT-NULL columns
            weight_in_g     = data["rod_weight_g"],
            weight_out_g    = 0.0,
            melt_batch_id   = 0,
            worker_id       = data.get("worker_id"),
        )
        session.add(batch)
        session.commit()
        return {"id": batch.id, "success": True}

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def record_outputs(batch_id: int, data: dict) -> dict:
    session = SessionLocal()
    try:
        batch = session.query(WireSheetBatch).filter(
            WireSheetBatch.id == batch_id
        ).first()
        if not batch:
            raise ValueError(f"Batch #{batch_id} not found")
        if batch.status == "completed":
            raise ValueError(f"Batch #{batch_id} is already completed")

        dye = data.get("dye_weight_g", 0.0)
        wire = data.get("wire_weight_g", 0.0)
        strips = data.get("strips_weight_g", 0.0)
        
        total_output = dye + wire + strips
        rod = batch.rod_weight_g or 0.0
        
        if total_output > rod:
            raise ValueError("Total output exceeds rod weight")
            
        loss = rod - total_output
        loss_pct = (loss / rod * 100) if rod > 0 else 0.0

        # Determine type based on outputs
        types = []
        if dye > 0: types.append("dye")
        if wire > 0: types.append("wire")
        if strips > 0: types.append("strips")
        batch_type = ", ".join(types) if types else "none"

        batch.dye_weight_g = dye
        batch.wire_weight_g = wire
        batch.strips_weight_g = strips
        batch.output_weight_g = total_output
        batch.weight_out_g    = total_output   # legacy
        batch.batch_type      = batch_type
        batch.loss_g          = round(loss, 3)
        batch.loss_pct        = round(loss_pct, 2)
        batch.status          = "completed"

        session.commit()
        batch_id, batch_date, loss_rounded = batch.id, batch.batch_date, round(loss, 3)

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()

    # Feed the Gold Box with the wire & sheet loss — must run after the batch's
    # own session has committed/closed (GoldBoxService opens its own session).
    if loss_rounded > 0:
        GoldBoxService.add_stock(
            added_date=batch_date, source="WIRE_SHEET", source_id=batch_id,
            weight_added_g=loss_rounded,
            notes=f"Wire & Sheet loss (batch #{batch_id})",
        )

    return {
        "id": batch_id,
        "success": True,
        "loss_pct": round(loss_pct, 2),
    }


def _resolve_target_name(session, batch) -> str:
    if batch.assigned_to_type == "TEAM" and batch.team_id:
        team = session.query(Team).get(batch.team_id)
        return (team.team_name or team.name) if team else "Unknown Team"
    if batch.worker_id:
        worker = session.query(Worker).get(batch.worker_id)
        return worker.name if worker else "Unknown Worker"
    return "—"


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
                "batch_type":      b.batch_type or "",
                "rod_weight_g":    b.rod_weight_g or 0.0,
                "output_weight_g": b.output_weight_g or 0.0,
                "dye_weight_g":    getattr(b, 'dye_weight_g', 0.0) or 0.0,
                "wire_weight_g":   getattr(b, 'wire_weight_g', 0.0) or 0.0,
                "strips_weight_g": getattr(b, 'strips_weight_g', 0.0) or 0.0,
                "loss_g":          b.loss_g or 0.0,
                "loss_pct":        b.loss_pct or 0.0,
                "status":          b.status or "pending",
                "worker_name":     _resolve_target_name(session, b),
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
            "batch_type":      b.batch_type or "",
            "rod_weight_g":    b.rod_weight_g or 0.0,
            "output_weight_g": b.output_weight_g or 0.0,
            "dye_weight_g":    getattr(b, 'dye_weight_g', 0.0) or 0.0,
            "wire_weight_g":   getattr(b, 'wire_weight_g', 0.0) or 0.0,
            "strips_weight_g": getattr(b, 'strips_weight_g', 0.0) or 0.0,
            "loss_g":          b.loss_g or 0.0,
            "loss_pct":        b.loss_pct or 0.0,
            "status":          b.status or "pending",
            "worker_name":     _resolve_target_name(session, b),
            "notes":           b.notes,
        }
    finally:
        session.close()
