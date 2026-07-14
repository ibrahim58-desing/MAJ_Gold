"""Complaint Service — routes a small gold-quality issue on a worker's
V Account item through the existing Goldsmith Issue/Return pipeline and
records the linked V Account debit/credit, leaving the original entry
untouched. status: open -> sent_to_goldsmith -> resolved."""
from database.models.base import SessionLocal
from database.models.v_account import Complaint, VAccountEntry
from database.models.process import GoldsmithReturn
from services.v_account_service import VAccountService
from services.goldsmith_service import create_issue, record_return


def create_complaint(complaint_date, worker_id, description, weight_sent_g,
                     qty_baby=0, qty_normal=0, qty_30inch=0,
                     v_account_entry_id=None, notes=None) -> dict:
    session = SessionLocal()
    try:
        c = Complaint(
            complaint_date=complaint_date, worker_id=worker_id, description=description,
            weight_sent_g=weight_sent_g, v_account_entry_id=v_account_entry_id,
            qty_baby=qty_baby, qty_normal=qty_normal, qty_30inch=qty_30inch,
            status="open", notes=notes,
        )
        session.add(c)
        session.commit()
        return {"id": c.id, "success": True}
    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def send_to_goldsmith(complaint_id) -> dict:
    session = SessionLocal()
    try:
        c = session.query(Complaint).get(complaint_id)
        if not c:
            raise ValueError("Complaint not found")
        if c.status != "open":
            raise ValueError("Complaint already sent")

        issue_res = create_issue({
            "issue_date": c.complaint_date,
            "issue_type": "INDIVIDUAL",
            "worker_id": c.worker_id,
            "team_id": None,
            "dye_issued_g": 0.0,
            "wire_issued_g": 0.0,
            "strips_issued_g": 0.0,
            "misc_issued_g": c.weight_sent_g,
            "complaint_id": c.id,
            "notes": f"Complaint #{c.id}: {c.description or ''}",
            # We create our own tagged VAccountEntry below — skip the
            # goldsmith service's automatic one to avoid double-booking.
            "skip_vaccount_entry": True,
        })
        if not issue_res.get("success"):
            raise ValueError(issue_res.get("error", "Failed to issue to goldsmith"))

        prev = VAccountService._prev_balance(session, c.worker_id)
        entry = VAccountEntry(
            entry_date=c.complaint_date, worker_id=c.worker_id,
            particular="Complaint Sent to Goldsmith",
            debit_g=c.weight_sent_g, balance_g=prev + c.weight_sent_g,
            source_type="COMPLAINT_SEND", source_id=c.id, status="closed",
        )
        session.add(entry)
        session.flush()

        c.goldsmith_issue_id = issue_res["id"]
        c.debit_vaccount_entry_id = entry.id
        c.status = "sent_to_goldsmith"
        session.commit()
        return {"id": c.id, "goldsmith_issue_id": issue_res["id"], "success": True}
    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def record_goldsmith_return_for_complaint(complaint_id, return_data: dict) -> dict:
    session = SessionLocal()
    try:
        c = session.query(Complaint).get(complaint_id)
        if not c:
            raise ValueError("Complaint not found")
        if c.status != "sent_to_goldsmith" or not c.goldsmith_issue_id:
            raise ValueError("Complaint has not been sent to goldsmith")

        data = {**return_data, "issue_id": c.goldsmith_issue_id, "skip_vaccount_entry": True}
        ret_res = record_return(data)
        if not ret_res.get("success"):
            raise ValueError(ret_res.get("error", "Failed to record goldsmith return"))

        ret = session.query(GoldsmithReturn).get(ret_res["id"])

        prev = VAccountService._prev_balance(session, c.worker_id)
        entry = VAccountEntry(
            entry_date=ret.return_date, worker_id=c.worker_id,
            particular="Complaint Return from Goldsmith",
            credit_g=ret.weight_g, balance_g=prev - ret.weight_g,
            source_type="COMPLAINT_RETURN", source_id=c.id, status="closed",
            qty_baby=ret.qty_baby, qty_normal=ret.qty_normal, qty_30inch=ret.qty_30inch,
            loss_g=ret.loss_g, loss_pct=ret.loss_pct,
            linked_entry_id=c.debit_vaccount_entry_id,
        )
        session.add(entry)
        session.flush()

        c.credit_vaccount_entry_id = entry.id
        c.loss_g = ret.loss_g
        c.loss_pct = ret.loss_pct
        c.status = "resolved"
        session.commit()
        return {"id": c.id, "loss_pct": ret.loss_pct, "loss_alert": ret.loss_pct > 2.0, "success": True}
    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def get_all_complaints() -> list:
    session = SessionLocal()
    try:
        items = session.query(Complaint).order_by(
            Complaint.complaint_date.desc(), Complaint.id.desc()
        ).all()
        for i in items:
            _ = i.worker.name if i.worker else None
        session.expunge_all()
        return items
    finally:
        session.close()


def get_complaint_by_id(complaint_id):
    session = SessionLocal()
    try:
        c = session.query(Complaint).get(complaint_id)
        if c:
            session.expunge(c)
        return c
    finally:
        session.close()
