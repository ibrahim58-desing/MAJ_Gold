from database.models.base import SessionLocal
import database.models.masters       # noqa: F401
import database.models.stock         # noqa: F401
import database.models.process       # noqa: F401
import database.models.gold_box      # noqa: F401
import database.models.stock_register  # noqa: F401
import database.models.ledger        # noqa: F401
import database.models.daybook       # noqa: F401
import database.models.v_account     # noqa: F401

from database.models.stock import MeltBatch, MeltBatchAlloy, MeltBatchInput
from database.models.masters import Dealer, AlloyType
from database.models.daybook import DaybookEntry

def _get_type_attr():
    mapper_attrs = [c.key for c in DaybookEntry.__mapper__.column_attrs]
    for candidate in ['type', 'entry_type', 'transaction_type', 'entry_kind']:
        if candidate in mapper_attrs:
            return candidate
    return None

def _get_alloy_map(melt_type, subtype):
    if melt_type == "ng_melting":
        if subtype == "ornaments":
            return {"metal_a": "Silver", "metal_b": "Copper"}
        else:
            return {"metal_a": "Silver", "metal_b": "Zinc"}
    else:
        if subtype == "ornaments":
            return {"metal_a": "Silver", "metal_b": "Copper"}
        else:
            return {"metal_a": "Silver", "metal_b": "Zinc"}

def create_batch(data: dict) -> dict:
    session = SessionLocal()
    try:
        # STEP 1 — create daybook entry
        from sqlalchemy import func
        sno = session.query(func.max(DaybookEntry.serial_no)).scalar()
        serial_no = (sno or 55419) + 1

        daybook = DaybookEntry(
            entry_date=data["batch_date"],
            ledger_account="Melting Process",
            particular=f"Melt Batch - {data['melt_type']} {data['subtype']}",
            debit_wt=data["final_916_g"],
            serial_no=serial_no,
            group_type="MELT",
            source_process="melt_batches",
            notes=f"Purity: {data.get('purity_value', '')}"
        )
        session.add(daybook)
        session.flush()

        # STEP 2 — calculate derived fields
        total_alloy = data["metal_a_g"] + data["metal_b_g"] + data["extra_alloy_g"]
        gross_weight = data["weight_in_g"] + total_alloy
        after_melt = data.get("after_melt_weight", 0.0)
        loss = 0.0
        if after_melt > 0:
            # Loss = before melting (final_916) - after melting
            loss = data["final_916_g"] - after_melt

        # STEP 3 — create melt_batch row
        batch = MeltBatch(
            batch_date=data["batch_date"],
            melt_type=data["melt_type"],
            subtype=data["subtype"],
            worker_id=1,  # Required by DB but removed from UI, defaulting to 1 or any valid worker
            supplier_id=data["supplier_id"],
            purity_value=data["purity_value"],
            weight_in_g=data["weight_in_g"],
            input_weight_g=data["weight_in_g"],
            total_alloy_g=total_alloy,
            gross_weight_g=gross_weight,
            metal_a_g=data["metal_a_g"],
            metal_b_g=data["metal_b_g"],
            extra_alloy_g=data["extra_alloy_g"],
            final_916_g=data["final_916_g"],
            weight_out_916_g=after_melt,
            ng_weight_g=0.0,
            kambi_weight_g=0.0,
            loss_g=loss,
            daybook_sno=daybook.serial_no,
            notes=""
        )
        session.add(batch)
        session.flush()

        # STEP 4 — create melt_batch_alloys rows
        alloy_map = _get_alloy_map(data["melt_type"], data["subtype"])
        
        for alloy_name, weight in [
            (alloy_map["metal_a"], data["metal_a_g"]),
            (alloy_map["metal_b"], data["metal_b_g"]),
            ("Extra", data["extra_alloy_g"]),
        ]:
            if weight <= 0:
                continue

            search_name = "Extra Alloy" if alloy_name == "Extra" else alloy_name
            alloy_type = session.query(AlloyType).filter(
                AlloyType.name.ilike(f"%{search_name}%")
            ).first()
            
            if alloy_type:
                alloy_row = MeltBatchAlloy(
                    melt_batch_id=batch.id,
                    alloy_type_id=alloy_type.id,
                    weight_g=weight,
                    daybook_sno=daybook.serial_no
                )
                session.add(alloy_row)

        session.commit()
        return {"id": batch.id, "success": True}

    except Exception as e:
        session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        session.close()

def update_after_melt(batch_id: int, after_melt_weight: float) -> dict:
    session = SessionLocal()
    try:
        batch = session.query(MeltBatch).filter(MeltBatch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Batch #{batch_id} not found")
        
        # Loss = before melting (final_916) - after melting
        loss = batch.final_916_g - after_melt_weight
        
        batch.weight_out_916_g = after_melt_weight
        batch.loss_g = round(loss, 3)
        
        session.commit()
        return {
            "id": batch_id,
            "weight_out_916_g": after_melt_weight,
            "loss_g": round(loss, 3),
            "success": True
        }
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def delete_batch(batch_id: int) -> dict:
    session = SessionLocal()
    try:
        session.query(MeltBatchAlloy).filter(MeltBatchAlloy.melt_batch_id == batch_id).delete()
        session.query(MeltBatchInput).filter(MeltBatchInput.melt_batch_id == batch_id).delete()
        session.query(MeltBatch).filter(MeltBatch.id == batch_id).delete()
        session.commit()
        return {"success": True}
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_all_batches() -> list:
    session = SessionLocal()
    try:
        query = session.query(MeltBatch, Dealer) \
                       .outerjoin(Dealer, MeltBatch.supplier_id == Dealer.id)
        results = query.order_by(MeltBatch.batch_date.desc(), MeltBatch.id.desc()).all()
        
        alloys_query = session.query(MeltBatchAlloy.melt_batch_id, AlloyType.name, MeltBatchAlloy.weight_g) \
                              .join(AlloyType, MeltBatchAlloy.alloy_type_id == AlloyType.id).all()
                              
        alloy_dict = {}
        for b_id, a_name, weight in alloys_query:
            if b_id not in alloy_dict:
                alloy_dict[b_id] = []
            alloy_dict[b_id].append(f"{a_name}: {weight:.3f}g")

        batches = []
        for batch, supplier in results:
            alloys_str = "None"
            if batch.id in alloy_dict:
                alloys_str = ", ".join(alloy_dict[batch.id])

            batches.append({
                "id": batch.id,
                "batch_date": batch.batch_date,
                "melt_type": batch.melt_type,
                "subtype": batch.subtype,
                "supplier_name": supplier.name if supplier else "Unknown",
                "input_weight_g": batch.input_weight_g,
                "final_916_g": batch.final_916_g,
                "weight_out_916_g": batch.weight_out_916_g or 0.0,
                "gross_weight_g": batch.gross_weight_g or 0.0,
                "loss_g": batch.loss_g or 0.0,
                "metal_a_g": batch.metal_a_g or 0.0,
                "metal_b_g": batch.metal_b_g or 0.0,
                "extra_alloy_g": batch.extra_alloy_g or 0.0,
                "alloys_display": alloys_str,
                "notes": batch.notes,
            })
        return batches
    finally:
        session.close()

def get_batch_by_id(batch_id: int) -> dict:
    session = SessionLocal()
    try:
        batch, supplier = session.query(MeltBatch, Dealer) \
                                 .outerjoin(Dealer, MeltBatch.supplier_id == Dealer.id) \
                                 .filter(MeltBatch.id == batch_id).first()
        if not batch:
            return None
            
        return {
            "id": batch.id,
            "batch_date": batch.batch_date,
            "melt_type": batch.melt_type,
            "subtype": batch.subtype,
            "supplier_name": supplier.name if supplier else "Unknown",
            "input_weight_g": batch.input_weight_g,
            "final_916_g": batch.final_916_g,
            "weight_out_916_g": batch.weight_out_916_g or 0.0,
            "gross_weight_g": batch.gross_weight_g or 0.0,
            "loss_g": batch.loss_g or 0.0,
        }
    finally:
        session.close()
