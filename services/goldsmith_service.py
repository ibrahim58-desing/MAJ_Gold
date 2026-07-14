"""Goldsmith Service — Handles issuing gold to goldsmiths and recording their returns."""
from datetime import datetime
from sqlalchemy import func as sa_func

from database.models.base import SessionLocal
from database.models.process import GoldsmithIssue, GoldsmithReturn, WireSheetBatch
from database.models.masters import Team, TeamMember, Worker
from database.models.daybook import DaybookEntry
from database.models.v_account import VAccountEntry
from services.gold_box_service import GoldBoxService


def _get_type_attr():
    mapper_attrs = [c.key for c in DaybookEntry.__mapper__.column_attrs]
    for candidate in ['type', 'entry_type', 'transaction_type', 'entry_kind']:
        if candidate in mapper_attrs:
            return candidate
    return None


def get_totals() -> dict:
    """Returns total dye, wire, strips available."""
    session = SessionLocal()
    try:
        # Sums from wire_sheet_batches
        totals = session.query(
            sa_func.coalesce(sa_func.sum(WireSheetBatch.dye_weight_g), 0.0).label("dye"),
            sa_func.coalesce(sa_func.sum(WireSheetBatch.wire_weight_g), 0.0).label("wire"),
            sa_func.coalesce(sa_func.sum(WireSheetBatch.strips_weight_g), 0.0).label("strips")
        ).first()

        ws_dye, ws_wire, ws_strips = totals.dye, totals.wire, totals.strips

        # Subtract sums from goldsmith_issues
        issues = session.query(
            sa_func.coalesce(sa_func.sum(GoldsmithIssue.dye_issued_g), 0.0).label("dye"),
            sa_func.coalesce(sa_func.sum(GoldsmithIssue.wire_issued_g), 0.0).label("wire"),
            sa_func.coalesce(sa_func.sum(GoldsmithIssue.strips_issued_g), 0.0).label("strips")
        ).first()

        is_dye, is_wire, is_strips = issues.dye, issues.wire, issues.strips

        loss = session.query(
            sa_func.coalesce(sa_func.sum(GoldsmithReturn.loss_g), 0.0)
        ).scalar()

        return {
            "total_dye_available_g": round(ws_dye - is_dye, 3),
            "total_wire_available_g": round(ws_wire - is_wire, 3),
            "total_strips_available_g": round(ws_strips - is_strips, 3),
            "total_loss_g": round(loss, 3)
        }
    finally:
        session.close()


def create_issue(data: dict) -> dict:
    session = SessionLocal()
    try:
        misc_issued_g = data.get("misc_issued_g", 0.0)
        total_issued = (
            data["dye_issued_g"] + data["wire_issued_g"] + data["strips_issued_g"] + misc_issued_g
        )

        # ── daybook entry ──
        sno = session.query(sa_func.max(DaybookEntry.serial_no)).scalar()
        serial_no = (sno or 55419) + 1

        target_name = ""
        if data["issue_type"] == "TEAM" and data.get("team_id"):
            team = session.query(Team).get(data["team_id"])
            target_name = team.team_name if team else "Team"
        elif data["issue_type"] == "INDIVIDUAL" and data.get("worker_id"):
            worker = session.query(Worker).get(data["worker_id"])
            target_name = worker.name if worker else "Worker"

        type_attr = _get_type_attr()
        db_kwargs = {
            "entry_date":     data["issue_date"],
            "ledger_account": "Goldsmith Issue",
            "particular":     f"Issued to {target_name}",
            "debit_wt":       total_issued,
            "serial_no":      serial_no,
            "group_type":     "GOLDSMITH",
            "source_process": "goldsmith_issues",
            "notes":          data.get("notes", ""),
        }
        if type_attr:
            db_kwargs[type_attr] = "GOLDSMITH"

        daybook = DaybookEntry(**db_kwargs)
        session.add(daybook)
        session.flush()

        # ── v account entry (debit worker or team lead) ──
        target_worker_id = None
        if data["issue_type"] == "INDIVIDUAL":
            target_worker_id = data["worker_id"]
        elif data["issue_type"] == "TEAM":
            team = session.query(Team).get(data["team_id"])
            if team and team.team_lead_id:
                target_worker_id = team.team_lead_id
        
        if target_worker_id and not data.get("skip_vaccount_entry"):
            # Complaint-routed issues create their own tagged VAccountEntry
            # (source_type=COMPLAINT_SEND) instead, to avoid double-booking.
            v_entry = VAccountEntry(
                entry_date=data["issue_date"],
                worker_id=target_worker_id,
                particular="Goldsmith Issue",
                debit_g=total_issued,
                daybook_sno=daybook.serial_no,
                notes=data.get("notes", "")
            )
            session.add(v_entry)

        # ── issue row ──
        issue = GoldsmithIssue(
            issue_date      = data["issue_date"],
            issue_type      = data["issue_type"],
            team_id         = data.get("team_id"),
            worker_id       = data.get("worker_id"),
            dye_issued_g    = data["dye_issued_g"],
            wire_issued_g   = data["wire_issued_g"],
            strips_issued_g = data["strips_issued_g"],
            misc_issued_g   = misc_issued_g,
            complaint_id    = data.get("complaint_id"),
            total_issued_g  = total_issued,
            status          = "open",
            daybook_sno     = daybook.serial_no,
            notes           = data.get("notes", "")
        )
        session.add(issue)
        session.commit()
        return {"id": issue.id, "success": True}

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def record_return(data: dict) -> dict:
    session = SessionLocal()
    try:
        issue = session.query(GoldsmithIssue).get(data["issue_id"])
        if not issue:
            raise ValueError("Issue not found")
        if issue.status == "returned":
            raise ValueError("Issue already returned")

        total_issued = issue.total_issued_g
        weight_g = data["weight_g"]
        loss_g = total_issued - weight_g
        loss_pct = (loss_g / total_issued * 100) if total_issued > 0 else 0.0

        # ── daybook entry ──
        sno = session.query(sa_func.max(DaybookEntry.serial_no)).scalar()
        serial_no = (sno or 55419) + 1

        type_attr = _get_type_attr()
        db_kwargs = {
            "entry_date":     data["return_date"],
            "ledger_account": "Goldsmith Return",
            "particular":     f"Goldsmith Return {data['pcs']} pcs",
            "credit_wt":      weight_g,
            "serial_no":      serial_no,
            "group_type":     "GOLDSMITH",
            "source_process": "goldsmith_returns",
            "notes":          data.get("notes", ""),
        }
        if type_attr:
            db_kwargs[type_attr] = "GOLDSMITH"

        daybook = DaybookEntry(**db_kwargs)
        session.add(daybook)
        session.flush()

        # ── v account entry (credit worker or team lead) ──
        target_worker_id = None
        if issue.issue_type == "INDIVIDUAL":
            target_worker_id = issue.worker_id
        elif issue.issue_type == "TEAM":
            team = session.query(Team).get(issue.team_id)
            if team and team.team_lead_id:
                target_worker_id = team.team_lead_id
        
        if target_worker_id and not data.get("skip_vaccount_entry"):
            # Complaint-routed returns create their own tagged VAccountEntry
            # (source_type=COMPLAINT_RETURN) instead, to avoid double-booking.
            v_entry = VAccountEntry(
                entry_date=data["return_date"],
                worker_id=target_worker_id,
                particular="Goldsmith Return",
                credit_g=weight_g,
                daybook_sno=daybook.serial_no,
                notes=data.get("notes", "")
            )
            session.add(v_entry)

        # ── return row ──
        ret = GoldsmithReturn(
            issue_id      = data["issue_id"],
            return_date   = data["return_date"],
            pcs           = data["pcs"],
            inches_per_pc = data["total_inches"] / data["pcs"] if data["pcs"] > 0 else 0,
            total_inches  = data["total_inches"],
            qty_baby      = data.get("qty_baby", 0),
            qty_normal    = data.get("qty_normal", 0),
            qty_30inch    = data.get("qty_30inch", 0),
            weight_g      = weight_g,
            loss_g        = loss_g,
            loss_pct      = loss_pct,
            daybook_sno   = daybook.serial_no,
            notes         = data.get("notes", "")
        )
        session.add(ret)

        issue.status = "returned"
        session.commit()
        ret_id = ret.id

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()

    # Feed the Gold Box with the goldsmith loss — must run after the batch's
    # own session has committed/closed (GoldBoxService opens its own session).
    if loss_g > 0:
        GoldBoxService.add_stock(
            added_date=data["return_date"], source="GOLDSMITH", source_id=ret_id,
            weight_added_g=round(loss_g, 3),
            notes=f"Goldsmith return loss (issue #{data['issue_id']})",
        )

    return {
        "id": ret_id,
        "success": True,
        "loss_pct": loss_pct,
        "loss_alert": loss_pct > 2.0
    }


def get_all_issues() -> list:
    session = SessionLocal()
    try:
        issues = session.query(GoldsmithIssue).order_by(GoldsmithIssue.issue_date.desc(), GoldsmithIssue.id.desc()).all()
        results = []
        for i in issues:
            target_name = ""
            if i.issue_type == "TEAM" and i.team_id:
                team = session.query(Team).get(i.team_id)
                target_name = team.team_name if team and team.team_name else (team.name if team else "Unknown Team")
            elif i.issue_type == "INDIVIDUAL" and i.worker_id:
                worker = session.query(Worker).get(i.worker_id)
                target_name = worker.name if worker else "Unknown Worker"

            ret = session.query(GoldsmithReturn).filter(GoldsmithReturn.issue_id == i.id).first()

            results.append({
                "id": i.id,
                "issue_date": i.issue_date,
                "issue_type": i.issue_type,
                "target_name": target_name,
                "dye_issued_g": i.dye_issued_g,
                "wire_issued_g": i.wire_issued_g,
                "strips_issued_g": i.strips_issued_g,
                "total_issued_g": i.total_issued_g,
                "status": i.status,
                "days_open": (datetime.now().date() - i.issue_date).days if i.status == "open" else 0,
                "return_id": ret.id if ret else None,
                "return_pcs": ret.pcs if ret else None,
                "return_inches": ret.total_inches if ret else None,
                "return_weight_g": ret.weight_g if ret else None,
                "loss_g": ret.loss_g if ret else None,
                "loss_pct": ret.loss_pct if ret else None,
            })
        return results
    finally:
        session.close()


def get_all_teams() -> list:
    session = SessionLocal()
    try:
        teams = session.query(Team).order_by(Team.team_name, Team.name).all()
        results = []
        for t in teams:
            lead = session.query(Worker).get(t.team_lead_id) if t.team_lead_id else None
            members = session.query(TeamMember).filter(TeamMember.team_id == t.id).all()
            member_details = []
            for m in members:
                w = session.query(Worker).get(m.worker_id)
                if w:
                    member_details.append({"id": w.id, "name": w.name, "code": w.code})
            
            t_name = t.team_name if t.team_name else t.name
            results.append({
                "id": t.id,
                "team_name": t_name,
                "lead_name": lead.name if lead else "No Lead",
                "member_count": len(members),
                "members": member_details
            })
        return results
    finally:
        session.close()


def create_team(data: dict) -> dict:
    session = SessionLocal()
    try:
        t = Team(
            team_name=data["team_name"],
            name=data["team_name"], # keeping for backwards compatibility
            process_type="GOLDSMITH",
            team_lead_id=data.get("team_lead_id"),
            is_active=True
        )
        session.add(t)
        session.commit()
        return {"id": t.id, "success": True}
    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def add_team_member(team_id: int, worker_id: int) -> dict:
    session = SessionLocal()
    try:
        m = TeamMember(
            team_id=team_id,
            worker_id=worker_id,
            joined_date=datetime.now().date(),
            is_active=True
        )
        session.add(m)
        session.commit()
        return {"id": m.id, "success": True}
    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()
