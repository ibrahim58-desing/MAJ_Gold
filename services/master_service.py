"""
Master Service — CRUD for Dealers, Workers, Teams, ProductType, DesignType, AlloyType.
"""
from services.base_service import BaseService
from database.models.masters import Dealer, Worker, Team, ProductType, DesignType, AlloyType


class MasterService(BaseService):

    # ─── Dealers ──────────────────────────────────────────────────────────────
    @staticmethod
    def get_dealers(active_only=False):
        with MasterService.get_session() as db:
            q = db.query(Dealer)
            if active_only:
                q = q.filter(Dealer.is_active == True)
            items = q.order_by(Dealer.code).all()
            db.expunge_all()
            return items

    @staticmethod
    def create_dealer(code, name, phone=None, address=None, gstin=None):
        with MasterService.get_session() as db:
            d = Dealer(code=code.upper().strip(), name=name.strip(),
                       phone=phone, address=address, gstin=gstin)
            db.add(d)
            db.flush()
            db.refresh(d)
            db.expunge(d)
            return d

    @staticmethod
    def update_dealer(dealer_id, **kwargs):
        with MasterService.get_session() as db:
            d = db.query(Dealer).get(dealer_id)
            if not d:
                raise ValueError(f"Dealer {dealer_id} not found")
            for k, v in kwargs.items():
                setattr(d, k, v)
            db.flush()

    @staticmethod
    def toggle_dealer_active(dealer_id):
        with MasterService.get_session() as db:
            d = db.query(Dealer).get(dealer_id)
            if d:
                d.is_active = not d.is_active

    # ─── Workers ──────────────────────────────────────────────────────────────
    @staticmethod
    def get_workers(process_type=None, active_only=False):
        with MasterService.get_session() as db:
            q = db.query(Worker)
            if process_type:
                q = q.filter(Worker.process_type == process_type)
            if active_only:
                q = q.filter(Worker.is_active == True)
            items = q.order_by(Worker.code).all()
            db.expunge_all()
            return items

    @staticmethod
    def get_worker_by_id(worker_id):
        with MasterService.get_session() as db:
            w = db.query(Worker).get(worker_id)
            if w:
                db.expunge(w)
            return w

    @staticmethod
    def create_worker(code, name, process_type, pay_type="PER_CHAIN",
                      rate_per_chain=0.0, monthly_wage=0.0, team_id=None, phone=None):
        with MasterService.get_session() as db:
            w = Worker(code=code.upper().strip(), name=name.strip(),
                       process_type=process_type, pay_type=pay_type,
                       rate_per_chain=rate_per_chain, monthly_wage=monthly_wage,
                       team_id=team_id, phone=phone)
            db.add(w)
            db.flush()
            db.refresh(w)
            db.expunge(w)
            return w

    @staticmethod
    def update_worker(worker_id, **kwargs):
        with MasterService.get_session() as db:
            w = db.query(Worker).get(worker_id)
            if not w:
                raise ValueError(f"Worker {worker_id} not found")
            for k, v in kwargs.items():
                setattr(w, k, v)

    @staticmethod
    def toggle_worker_active(worker_id):
        with MasterService.get_session() as db:
            w = db.query(Worker).get(worker_id)
            if w:
                w.is_active = not w.is_active

    # ─── Teams ────────────────────────────────────────────────────────────────
    @staticmethod
    def get_teams(process_type=None):
        with MasterService.get_session() as db:
            q = db.query(Team)
            if process_type:
                q = q.filter(Team.process_type == process_type)
            items = q.order_by(Team.name).all()
            db.expunge_all()
            return items

    @staticmethod
    def create_team(name, process_type):
        with MasterService.get_session() as db:
            t = Team(name=name.strip(), process_type=process_type)
            db.add(t)
            db.flush()
            db.refresh(t)
            db.expunge(t)
            return t

    @staticmethod
    def update_team(team_id, **kwargs):
        with MasterService.get_session() as db:
            t = db.query(Team).get(team_id)
            if not t:
                raise ValueError("Team not found")
            for k, v in kwargs.items():
                setattr(t, k, v)

    # ─── Product Types ────────────────────────────────────────────────────────
    @staticmethod
    def get_product_types():
        with MasterService.get_session() as db:
            items = db.query(ProductType).order_by(ProductType.code).all()
            db.expunge_all()
            return items

    @staticmethod
    def create_product_type(code, name, description=None):
        with MasterService.get_session() as db:
            pt = ProductType(code=code.upper().strip(), name=name.strip(), description=description)
            db.add(pt)

    # ─── Design Types ─────────────────────────────────────────────────────────
    @staticmethod
    def get_design_types():
        with MasterService.get_session() as db:
            items = db.query(DesignType).order_by(DesignType.code).all()
            db.expunge_all()
            return items

    @staticmethod
    def create_design_type(code, name, description=None):
        with MasterService.get_session() as db:
            dt = DesignType(code=code.upper().strip(), name=name.strip(), description=description)
            db.add(dt)

    # ─── Alloy Types ──────────────────────────────────────────────────────────
    @staticmethod
    def get_alloy_types():
        with MasterService.get_session() as db:
            items = db.query(AlloyType).order_by(AlloyType.code).all()
            db.expunge_all()
            return items

    @staticmethod
    def create_alloy_type(code, name):
        with MasterService.get_session() as db:
            at = AlloyType(code=code.upper().strip(), name=name.strip())
            db.add(at)
