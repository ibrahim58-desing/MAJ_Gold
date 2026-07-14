"""Polish Service — Handles Polish batch inputs and outputs (isolated loss)."""
from datetime import datetime
from sqlalchemy import func as sa_func

from database.models.base import SessionLocal
from database.models.process import PolishBatch, GoldsmithReturn
from database.models.daybook import DaybookEntry


def _get_type_attr():
    mapper_attrs = [c.key for c in DaybookEntry.__mapper__.column_attrs]
    for candidate in ['type', 'entry_type', 'transaction_type', 'entry_kind']:
        if candidate in mapper_attrs:
            return candidate
    return None


def get_goldsmith_totals() -> dict:
    session = SessionLocal()
    try:
        returns = session.query(
            sa_func.coalesce(sa_func.sum(GoldsmithReturn.pcs), 0).label("pcs"),
            sa_func.coalesce(sa_func.sum(GoldsmithReturn.total_inches), 0.0).label("inches"),
            sa_func.coalesce(sa_func.sum(GoldsmithReturn.weight_g), 0.0).label("weight")
        ).first()

        polish = session.query(
            sa_func.coalesce(sa_func.sum(PolishBatch.input_pcs), 0).label("pcs"),
            sa_func.coalesce(sa_func.sum(PolishBatch.input_inches), 0.0).label("inches"),
            sa_func.coalesce(sa_func.sum(PolishBatch.input_weight_g), 0.0).label("weight")
        ).first()

        return {
            "total_pcs": int(returns.pcs) - int(polish.pcs),
            "total_inches": round(returns.inches - polish.inches, 2),
            "total_weight_g": round(returns.weight - polish.weight, 3)
        }
    finally:
        session.close()


def create_batch(data: dict) -> dict:
    session = SessionLocal()
    try:
        input_qty_baby = data.get("input_qty_baby", 0)
        input_qty_normal = data.get("input_qty_normal", 0)
        input_qty_30inch = data.get("input_qty_30inch", 0)
        input_pcs = input_qty_baby + input_qty_normal + input_qty_30inch
        input_inches = input_qty_30inch * 30

        # ── daybook entry ──
        sno = session.query(sa_func.max(DaybookEntry.serial_no)).scalar()
        serial_no = (sno or 55419) + 1

        type_attr = _get_type_attr()
        db_kwargs = {
            "entry_date":     data["batch_date"],
            "ledger_account": "Polish Process",
            "particular":     f"Polish Input {input_pcs} pcs",
            "debit_wt":       data["input_weight_g"],
            "serial_no":      serial_no,
            "group_type":     "POLISH",
            "source_process": "polish_batches",
            "notes":          data.get("notes", ""),
        }
        if type_attr:
            db_kwargs[type_attr] = "POLISH"

        daybook = DaybookEntry(**db_kwargs)
        session.add(daybook)
        session.flush()

        # ── batch row ──
        batch = PolishBatch(
            batch_date          = data["batch_date"],
            assigned_to_type    = data.get("assigned_to_type", "INDIVIDUAL"),
            team_id             = data.get("team_id"),
            worker_id           = data.get("worker_id"),
            goldsmith_return_id = data.get("goldsmith_return_id"),
            input_pcs           = input_pcs,
            input_inches        = input_inches,
            input_weight_g      = data["input_weight_g"],
            input_qty_baby      = input_qty_baby,
            input_qty_normal    = input_qty_normal,
            input_qty_30inch    = input_qty_30inch,
            output_pcs          = 0,
            output_inches       = 0.0,
            output_weight_g     = 0.0,
            polish_loss_g       = 0.0,
            polish_loss_pcs     = 0,
            polish_loss_pct     = 0.0,
            status              = "pending",
            daybook_sno         = daybook.serial_no,
            notes               = data.get("notes", "")
        )
        session.add(batch)
        session.commit()
        return {"id": batch.id, "success": True}

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def record_output(data: dict) -> dict:
    # NOTE: Polish loss is "dirt" — it must never be routed to the Gold Box.
    # Do not add a GoldBoxService call here; only Wire&Sheet, Goldsmith,
    # Faceting, and Vaccount losses feed the Gold Box.
    session = SessionLocal()
    try:
        batch = session.query(PolishBatch).get(data["batch_id"])
        if not batch:
            raise ValueError("Polish batch not found")
        if batch.status == "completed":
            raise ValueError("Polish batch already completed")

        output_qty_baby = data.get("output_qty_baby", 0)
        output_qty_normal = data.get("output_qty_normal", 0)
        output_qty_30inch = data.get("output_qty_30inch", 0)
        output_pcs = output_qty_baby + output_qty_normal + output_qty_30inch
        output_inches = output_qty_30inch * 30

        input_weight = batch.input_weight_g
        output_weight = data["output_weight_g"]
        polish_loss_g = input_weight - output_weight
        polish_loss_pct = (polish_loss_g / input_weight * 100) if input_weight > 0 else 0.0

        input_pcs = batch.input_pcs
        polish_loss_pcs = input_pcs - output_pcs

        batch.output_pcs = output_pcs
        batch.output_inches = output_inches
        batch.output_weight_g = output_weight
        batch.output_qty_baby = output_qty_baby
        batch.output_qty_normal = output_qty_normal
        batch.output_qty_30inch = output_qty_30inch
        batch.polish_loss_g = polish_loss_g
        batch.polish_loss_pcs = polish_loss_pcs
        batch.polish_loss_pct = polish_loss_pct
        batch.notes = data.get("notes", batch.notes)
        batch.status = "completed"

        session.commit()

        return {
            "id": batch.id,
            "success": True,
            "polish_loss_pct": polish_loss_pct
        }

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def get_all_batches() -> list:
    session = SessionLocal()
    try:
        from database.models.masters import Worker, Team
        batches = session.query(
            PolishBatch, Worker.name.label("worker_name"), Team.team_name.label("team_name")
        ).outerjoin(
            Worker, PolishBatch.worker_id == Worker.id
        ).outerjoin(
            Team, PolishBatch.team_id == Team.id
        ).order_by(PolishBatch.batch_date.desc(), PolishBatch.id.desc()).all()
        
        results = []
        for b, w_name, t_name in batches:
            name = t_name if b.assigned_to_type == "TEAM" else w_name
            results.append({
                "id": b.id,
                "batch_date": b.batch_date,
                "worker_name": name,
                "worker_id": b.worker_id,
                "input_pcs": b.input_pcs,
                "input_inches": b.input_inches,
                "input_weight_g": b.input_weight_g,
                "input_qty_baby": b.input_qty_baby,
                "input_qty_normal": b.input_qty_normal,
                "input_qty_30inch": b.input_qty_30inch,
                "output_pcs": b.output_pcs,
                "output_inches": b.output_inches,
                "output_weight_g": b.output_weight_g,
                "output_qty_baby": b.output_qty_baby,
                "output_qty_normal": b.output_qty_normal,
                "output_qty_30inch": b.output_qty_30inch,
                "polish_loss_g": b.polish_loss_g,
                "polish_loss_pcs": b.polish_loss_pcs,
                "polish_loss_pct": b.polish_loss_pct,
                "status": b.status,
                "notes": b.notes
            })
        return results
    finally:
        session.close()


def get_polish_loss_summary() -> dict:
    session = SessionLocal()
    try:
        totals = session.query(
            sa_func.coalesce(sa_func.sum(PolishBatch.input_weight_g), 0.0).label("input_weight"),
            sa_func.coalesce(sa_func.sum(PolishBatch.output_weight_g), 0.0).label("output_weight"),
            sa_func.coalesce(sa_func.sum(PolishBatch.polish_loss_g), 0.0).label("loss_g"),
            sa_func.coalesce(sa_func.sum(PolishBatch.polish_loss_pcs), 0).label("loss_pcs")
        ).filter(PolishBatch.status == "completed").first()

        input_wt = totals.input_weight
        loss = totals.loss_g
        avg_loss_pct = (loss / input_wt * 100) if input_wt > 0 else 0.0

        return {
            "total_input_weight_g": round(input_wt, 3),
            "total_output_weight_g": round(totals.output_weight, 3),
            "total_polish_loss_g": round(loss, 3),
            "total_polish_loss_pcs": int(totals.loss_pcs),
            "average_loss_pct": round(avg_loss_pct, 2)
        }
    finally:
        session.close()
