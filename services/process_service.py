"""
Process Service — CRUD for the full manufacturing chain:
WireSheet → Goldsmith (+ worker logs + design logs) → Polish → Faceting → Kambi
"""
from database.models.process import (
    WireSheetBatch, GoldsmithBatch, GoldsmithWorkerLog,
    GoldsmithDesignLog, PolishBatch, FacetingBatch, KambiBatch
)
from services.base_service import BaseService
from services.melt_service import MeltService
from services.gold_box_service import GoldBoxService
from utils.formatters import calc_pay, calc_ppwl, calc_extra_loss


class ProcessService(BaseService):

    # ─── Wire & Sheet ─────────────────────────────────────────────────────────
    @staticmethod
    def get_wire_sheet_batches(start_date=None, end_date=None):
        with ProcessService.get_session() as db:
            q = db.query(WireSheetBatch)
            if start_date:
                q = q.filter(WireSheetBatch.batch_date >= start_date)
            if end_date:
                q = q.filter(WireSheetBatch.batch_date <= end_date)
            items = q.order_by(WireSheetBatch.batch_date.desc()).all()
            db.expunge_all()
            return items

    @staticmethod
    def create_wire_sheet(batch_date, melt_batch_id, weight_in_g, weight_out_g,
                          chains_count=0, solder_weight_g=0.0, worker_id=None,
                          product_type_id=None, notes=None):
        with ProcessService.get_session() as db:
            ws = WireSheetBatch(
                batch_date=batch_date, melt_batch_id=melt_batch_id, worker_id=worker_id,
                weight_in_g=weight_in_g, weight_out_g=weight_out_g,
                loss_g=max(0.0, weight_in_g - weight_out_g), chains_count=chains_count,
                solder_weight_g=solder_weight_g, product_type_id=product_type_id, notes=notes,
            )
            db.add(ws)
            db.flush(); return ws.id

    @staticmethod
    def update_wire_sheet(ws_id, **kwargs):
        with ProcessService.get_session() as db:
            ws = db.query(WireSheetBatch).get(ws_id)
            if not ws: raise ValueError("Not found")
            for k, v in kwargs.items(): setattr(ws, k, v)
            ws.loss_g = max(0.0, ws.weight_in_g - ws.weight_out_g)

    @staticmethod
    def delete_wire_sheet(ws_id):
        with ProcessService.get_session() as db:
            ws = db.query(WireSheetBatch).get(ws_id)
            if ws: db.delete(ws)

    # ─── Goldsmith Batch ──────────────────────────────────────────────────────
    @staticmethod
    def get_goldsmith_batches(start_date=None, end_date=None):
        with ProcessService.get_session() as db:
            q = db.query(GoldsmithBatch)
            if start_date: q = q.filter(GoldsmithBatch.from_date >= start_date)
            if end_date: q = q.filter(GoldsmithBatch.to_date <= end_date)
            items = q.order_by(GoldsmithBatch.from_date.desc()).all()
            db.expunge_all(); return items

    @staticmethod
    def create_goldsmith_batch(from_date, to_date, weight_in_g, weight_out_g,
                               fin_pcs=0, wire_sheet_batch_id=None, product_type_id=None, notes=None):
        wl = max(0.0, weight_in_g - weight_out_g)
        with ProcessService.get_session() as db:
            gb = GoldsmithBatch(
                from_date=from_date, to_date=to_date,
                wire_sheet_batch_id=wire_sheet_batch_id, weight_in_g=weight_in_g,
                weight_out_g=weight_out_g, weight_loss_g=wl, fin_pcs=fin_pcs,
                per_pc_wl=calc_ppwl(wl, fin_pcs), product_type_id=product_type_id, notes=notes,
            )
            db.add(gb); db.flush(); return gb.id

    @staticmethod
    def update_goldsmith_batch(batch_id, **kwargs):
        with ProcessService.get_session() as db:
            gb = db.query(GoldsmithBatch).get(batch_id)
            if not gb: raise ValueError("Not found")
            for k, v in kwargs.items(): setattr(gb, k, v)
            gb.weight_loss_g = max(0.0, gb.weight_in_g - gb.weight_out_g)
            gb.per_pc_wl = calc_ppwl(gb.weight_loss_g, gb.fin_pcs)

    @staticmethod
    def delete_goldsmith_batch(batch_id):
        with ProcessService.get_session() as db:
            gb = db.query(GoldsmithBatch).get(batch_id)
            if gb: db.delete(gb)

    # ─── Worker Log ───────────────────────────────────────────────────────────
    @staticmethod
    def get_worker_logs(batch_id=None, worker_id=None, start_date=None, end_date=None):
        with ProcessService.get_session() as db:
            q = db.query(GoldsmithWorkerLog)
            if batch_id: q = q.filter(GoldsmithWorkerLog.goldsmith_batch_id == batch_id)
            if worker_id: q = q.filter(GoldsmithWorkerLog.worker_id == worker_id)
            if start_date: q = q.filter(GoldsmithWorkerLog.log_date >= start_date)
            if end_date: q = q.filter(GoldsmithWorkerLog.log_date <= end_date)
            items = q.order_by(GoldsmithWorkerLog.log_date.desc()).all()
            for i in items:
                _ = i.worker.name if i.worker else None
            db.expunge_all(); return items

    @staticmethod
    def create_worker_log(goldsmith_batch_id, worker_id, log_date, debit_g, credit_g,
                          pcs, ppwl=0.0, from_date=None, to_date=None, notes=None):
        from database.models.masters import Worker
        wl = max(0.0, debit_g - credit_g)
        with ProcessService.get_session() as db:
            worker = db.query(Worker).get(worker_id)
            rate = worker.rate_per_chain if worker else 0.0
            log = GoldsmithWorkerLog(
                goldsmith_batch_id=goldsmith_batch_id, worker_id=worker_id,
                log_date=log_date, from_date=from_date, to_date=to_date,
                debit_g=debit_g, credit_g=credit_g, weight_loss_g=wl, pcs=pcs,
                ppwl=ppwl, act_wl=calc_ppwl(wl, pcs),
                extra_loss_g=calc_extra_loss(wl, ppwl, pcs),
                pay_earned=calc_pay(pcs, rate), notes=notes,
            )
            db.add(log); db.flush(); return log.id

    @staticmethod
    def update_worker_log(log_id, **kwargs):
        from database.models.masters import Worker
        with ProcessService.get_session() as db:
            log = db.query(GoldsmithWorkerLog).get(log_id)
            if not log: raise ValueError("Not found")
            for k, v in kwargs.items(): setattr(log, k, v)
            log.weight_loss_g = max(0.0, log.debit_g - log.credit_g)
            log.act_wl = calc_ppwl(log.weight_loss_g, log.pcs)
            log.extra_loss_g = calc_extra_loss(log.weight_loss_g, log.ppwl, log.pcs)
            worker = db.query(Worker).get(log.worker_id)
            log.pay_earned = calc_pay(log.pcs, worker.rate_per_chain if worker else 0.0)

    @staticmethod
    def delete_worker_log(log_id):
        with ProcessService.get_session() as db:
            log = db.query(GoldsmithWorkerLog).get(log_id)
            if log: db.delete(log)

    # ─── Design Log ───────────────────────────────────────────────────────────
    @staticmethod
    def get_design_logs(batch_id=None, worker_id=None, month_year=None):
        with ProcessService.get_session() as db:
            q = db.query(GoldsmithDesignLog)
            if batch_id: q = q.filter(GoldsmithDesignLog.goldsmith_batch_id == batch_id)
            if worker_id: q = q.filter(GoldsmithDesignLog.worker_id == worker_id)
            if month_year: q = q.filter(GoldsmithDesignLog.month_year == month_year)
            items = q.all()
            db.expunge_all(); return items

    @staticmethod
    def create_design_log(goldsmith_batch_id, worker_id, design_type_id,
                          month_year, pieces_count, from_date=None, to_date=None):
        with ProcessService.get_session() as db:
            dl = GoldsmithDesignLog(
                goldsmith_batch_id=goldsmith_batch_id, worker_id=worker_id,
                design_type_id=design_type_id, month_year=month_year,
                pieces_count=pieces_count, from_date=from_date, to_date=to_date,
            )
            db.add(dl)

    # ─── Polish ───────────────────────────────────────────────────────────────
    @staticmethod
    def get_polish_batches(start_date=None, end_date=None):
        with ProcessService.get_session() as db:
            q = db.query(PolishBatch)
            if start_date: q = q.filter(PolishBatch.batch_date >= start_date)
            if end_date: q = q.filter(PolishBatch.batch_date <= end_date)
            items = q.order_by(PolishBatch.batch_date.desc()).all()
            db.expunge_all(); return items

    @staticmethod
    def create_polish_batch(batch_date, goldsmith_batch_id, chains_in, chains_out,
                            worker_id=None, notes=None):
        with ProcessService.get_session() as db:
            pb = PolishBatch(
                batch_date=batch_date, goldsmith_batch_id=goldsmith_batch_id,
                chains_in=chains_in, chains_out=chains_out, worker_id=worker_id, notes=notes,
            )
            db.add(pb); db.flush(); return pb.id

    @staticmethod
    def update_polish_batch(pb_id, **kwargs):
        with ProcessService.get_session() as db:
            pb = db.query(PolishBatch).get(pb_id)
            if not pb: raise ValueError("Not found")
            for k, v in kwargs.items(): setattr(pb, k, v)

    @staticmethod
    def delete_polish_batch(pb_id):
        with ProcessService.get_session() as db:
            pb = db.query(PolishBatch).get(pb_id)
            if pb: db.delete(pb)

    # ─── Faceting ─────────────────────────────────────────────────────────────
    @staticmethod
    def get_faceting_batches(worker_id=None, start_date=None, end_date=None):
        with ProcessService.get_session() as db:
            q = db.query(FacetingBatch)
            if worker_id: q = q.filter(FacetingBatch.worker_id == worker_id)
            if start_date: q = q.filter(FacetingBatch.from_date >= start_date)
            if end_date: q = q.filter(FacetingBatch.to_date <= end_date)
            items = q.order_by(FacetingBatch.from_date.desc()).all()
            db.expunge_all(); return items

    @staticmethod
    def create_faceting_batch(from_date, weight_in_g, assigned_to_type="INDIVIDUAL",
                              worker_id=None, team_id=None, in_qty_baby=0, in_qty_normal=0,
                              in_qty_30inch=0, polish_batch_id=None, product_type_id=None,
                              notes=None):
        """Step 1 of the create->update flow. Faceting can take hours, so only
        the input side (who, how much gold, what chain sizes) is captured now;
        weight-out and loss routing are captured later via update_faceting_output."""
        with ProcessService.get_session() as db:
            fb = FacetingBatch(
                from_date=from_date, to_date=from_date, worker_id=worker_id, team_id=team_id,
                assigned_to_type=assigned_to_type, status="pending",
                polish_batch_id=polish_batch_id, weight_in_g=weight_in_g,
                weight_out_g=0.0, weight_loss_g=0.0,
                in_qty_baby=in_qty_baby, in_qty_normal=in_qty_normal, in_qty_30inch=in_qty_30inch,
                product_type_id=product_type_id, notes=notes,
            )
            db.add(fb); db.flush(); return fb.id

    @staticmethod
    def update_faceting_output(fb_id, to_date, weight_out_g, out_qty_baby=0, out_qty_normal=0,
                               out_qty_30inch=0):
        """Step 2 of the create->update flow: records output weight/chain tally
        and computes the weight loss. Where that loss actually goes (Melting vs
        Gold Box) usually isn't known yet at this point, so it's decided later
        on the Faceting Loss page via route_faceting_loss()."""
        with ProcessService.get_session() as db:
            fb = db.query(FacetingBatch).get(fb_id)
            if not fb: raise ValueError("Not found")
            if fb.status != "pending": raise ValueError("Batch is not pending")

            wl = max(0.0, fb.weight_in_g - weight_out_g)

            fb.to_date = to_date
            fb.weight_out_g = weight_out_g
            fb.weight_loss_g = wl
            fb.out_qty_baby = out_qty_baby
            fb.out_qty_normal = out_qty_normal
            fb.out_qty_30inch = out_qty_30inch
            fb.status = "completed"
            fb.loss_routed = False

        return {"id": fb_id, "weight_loss_g": wl}

    @staticmethod
    def get_unrouted_faceting_losses():
        """Completed Faceting batches whose loss hasn't been assigned to
        Melting/Gold Box yet."""
        with ProcessService.get_session() as db:
            items = (
                db.query(FacetingBatch)
                .filter(FacetingBatch.status == "completed", FacetingBatch.loss_routed == False)
                .order_by(FacetingBatch.to_date.desc())
                .all()
            )
            db.expunge_all(); return items

    @staticmethod
    def route_faceting_loss(fb_id, loss_to_melting_g=0.0, loss_to_gold_box_g=0.0):
        """Decide, after the fact, how much of a completed batch's weight loss
        gets recycled back to Melting vs physically stored in the Gold Box."""
        with ProcessService.get_session() as db:
            fb = db.query(FacetingBatch).get(fb_id)
            if not fb: raise ValueError("Not found")
            if fb.status != "completed": raise ValueError("Batch is not completed yet")
            if fb.loss_routed: raise ValueError("Loss already routed for this batch")

            split = loss_to_melting_g + loss_to_gold_box_g
            if abs(split - fb.weight_loss_g) > 0.001:
                raise ValueError(
                    f"Weight Loss is {fb.weight_loss_g:.3f} g but Melting + Gold Box = {split:.3f} g."
                )

            fb.loss_to_melting_g = loss_to_melting_g
            fb.loss_to_gold_box_g = loss_to_gold_box_g
            fb.loss_routed = True
            to_date = fb.to_date

        if loss_to_melting_g > 0:
            MeltService.create_solder_return(
                returned_date=to_date, source_process="FACETING",
                source_batch_id=fb_id, weight_g=loss_to_melting_g,
                notes=f"Faceting loss recycled to melting (batch #{fb_id})",
            )
        if loss_to_gold_box_g > 0:
            GoldBoxService.add_stock(
                added_date=to_date, source="FACETING", source_id=fb_id,
                weight_added_g=loss_to_gold_box_g,
                notes=f"Faceting loss routed to gold box (batch #{fb_id})",
            )
        return {"id": fb_id}

    @staticmethod
    def update_faceting_batch(fb_id, **kwargs):
        with ProcessService.get_session() as db:
            fb = db.query(FacetingBatch).get(fb_id)
            if not fb: raise ValueError("Not found")
            for k, v in kwargs.items(): setattr(fb, k, v)
            fb.weight_loss_g = max(0.0, fb.weight_in_g - fb.weight_out_g)

    @staticmethod
    def delete_faceting_batch(fb_id):
        with ProcessService.get_session() as db:
            fb = db.query(FacetingBatch).get(fb_id)
            if fb: db.delete(fb)

    # ─── Kambi ────────────────────────────────────────────────────────────────
    @staticmethod
    def get_kambi_batches(start_date=None, end_date=None):
        with ProcessService.get_session() as db:
            q = db.query(KambiBatch)
            if start_date: q = q.filter(KambiBatch.batch_date >= start_date)
            if end_date: q = q.filter(KambiBatch.batch_date <= end_date)
            items = q.order_by(KambiBatch.batch_date.desc()).all()
            db.expunge_all(); return items

    @staticmethod
    def create_kambi_batch(batch_date, weight_in_g, weight_out_g,
                           gold_box_drawn_g=0.0, gold_returned_g=0.0,
                           chains_linked=0, hooks_used=0, worker_id=None,
                           faceting_batch_id=None, solder_weight_g=0.0, notes=None):
        with ProcessService.get_session() as db:
            kb = KambiBatch(
                batch_date=batch_date, worker_id=worker_id, faceting_batch_id=faceting_batch_id,
                weight_in_g=weight_in_g, weight_out_g=weight_out_g,
                loss_g=max(0.0, weight_in_g - weight_out_g),
                gold_box_drawn_g=gold_box_drawn_g, gold_returned_g=gold_returned_g,
                chains_linked=chains_linked, hooks_used=hooks_used,
                solder_weight_g=solder_weight_g, notes=notes,
            )
            db.add(kb); db.flush(); return kb.id

    @staticmethod
    def update_kambi_batch(kb_id, **kwargs):
        with ProcessService.get_session() as db:
            kb = db.query(KambiBatch).get(kb_id)
            if not kb: raise ValueError("Not found")
            for k, v in kwargs.items(): setattr(kb, k, v)
            kb.loss_g = max(0.0, kb.weight_in_g - kb.weight_out_g)

    @staticmethod
    def delete_kambi_batch(kb_id):
        with ProcessService.get_session() as db:
            kb = db.query(KambiBatch).get(kb_id)
            if kb: db.delete(kb)
