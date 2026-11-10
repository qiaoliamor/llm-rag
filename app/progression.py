"""Local demo economy and per-character growth; never real billing or authentication."""
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, CheckConstraint, select, text
from sqlalchemy.orm import declarative_base

from .dialogue import CHARACTER, ProviderFailure
from .memory import Player

Base = declarative_base()
THRESHOLDS = {'memory':30, 'weather':60, 'emotion':90}
GIFTS = {
    'bookmark':{'name':'纸页书签', 'price':20, 'points':5, 'description':'把今天读到的那一页，轻轻留住。'},
    'tea':{'name':'一杯热茶', 'price':60, 'points':12, 'description':'忙碌的间隙，也记得歇一会儿。'},
    'lamp':{'name':'暖光小灯', 'price':120, 'points':20, 'description':'让晚一点的聊天，也有温柔的光。'},
}


class Account(Base):
    __tablename__ = 'companion_accounts'
    user_id = Column(String, primary_key=True)
    name = Column(String(40), default='', nullable=False)
    email = Column(String(254), default='', nullable=False)
    phone = Column(String(24), default='', nullable=False)
    coins = Column(Integer, default=100, nullable=False)
    credit_day = Column(String, default='', nullable=False)
    credits_today = Column(Integer, default=0, nullable=False)
    __table_args__ = (CheckConstraint('coins >= 0'),)


class Bond(Base):
    __tablename__ = 'companion_bonds'
    user_id = Column(String, primary_key=True)
    character_id = Column(String, primary_key=True)
    score = Column(Integer, default=0, nullable=False)
    last_turn = Column(DateTime, nullable=True)
    active_seconds = Column(Integer, default=0, nullable=False)
    pending_seconds = Column(Integer, default=0, nullable=False)
    talk_day = Column(String, default='', nullable=False)
    talk_points_today = Column(Integer, default=0, nullable=False)
    __table_args__ = (CheckConstraint('score >= 0 AND score <= 100'),)


class Entry(Base):
    __tablename__ = 'companion_ledger'
    user_id = Column(String, primary_key=True)
    request_id = Column(String(36), primary_key=True)
    action = Column(String, nullable=False)
    character_id = Column(String, nullable=False)
    coins_delta = Column(Integer, nullable=False)
    points_delta = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)


class Progression:
    def __init__(self, store, clock=None):
        self.store = store
        self.clock = clock or (lambda:datetime.now(timezone.utc).replace(tzinfo=None))
        Base.metadata.create_all(store.engine)
        with store.engine.begin() as connection:
            connection.execute(text('INSERT INTO schema_versions(version) VALUES (5) ON CONFLICT (version) DO NOTHING'))

    @contextmanager
    def transaction(self, uid):
        with self.store.db() as db:
            if self.store.engine.dialect.name == 'sqlite':
                db.execute(text('BEGIN IMMEDIATE'))
            try:
                player = db.scalar(select(Player).where(Player.id==uid).with_for_update())
                if player is None:
                    raise ProviderFailure('identity_missing','本地账户失效，请刷新。',401)
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    def rows(self, db, uid):
        account = db.get(Account, uid)
        if account is None:
            account = Account(user_id=uid)
            db.add(account)
        bond = db.get(Bond, (uid,CHARACTER['id']))
        if bond is None:
            bond = Bond(user_id=uid,character_id=CHARACTER['id'])
            db.add(bond)
        db.flush()
        return account,bond

    def snapshot(self, db, account, bond):
        abilities = {k:bond.score>=v for k,v in THRESHOLDS.items()}
        ledger = db.scalars(select(Entry).where(Entry.user_id==account.user_id)
            .order_by(Entry.created_at.desc(), Entry.request_id).limit(10))
        return {'profile':{'name':account.name,'email':account.email,'phone':account.phone},
                'coins':account.coins,'currency_mode':'demo','starting_coins':100,
                'character':{'id':CHARACTER['id'],'name':CHARACTER['name'],'score':bond.score,
                             'active_seconds':bond.active_seconds,'abilities':abilities},
                'thresholds':THRESHOLDS,'gifts':[{'id':key,**gift} for key,gift in GIFTS.items()],
                'ledger':[{'request_id':e.request_id,'action':e.action,'character_id':e.character_id,
                           'coins_delta':e.coins_delta,'points_delta':e.points_delta,
                           'created_at':e.created_at.isoformat()+'Z'} for e in ledger]}

    def get(self, uid):
        with self.transaction(uid) as db:
            account,bond = self.rows(db,uid)
            return self.snapshot(db,account,bond)

    def require(self, uid, ability):
        if not self.get(uid)['character']['abilities'][ability]:
            raise ProviderFailure('ability_locked',f'亲密度达到{THRESHOLDS[ability]}分后可解锁这项能力；已有资料仍可查看和删除。',403)

    def profile(self, uid, values):
        with self.transaction(uid) as db:
            account,bond = self.rows(db,uid)
            for key in ('name','email','phone'):
                setattr(account,key,values[key])
            return self.snapshot(db,account,bond)

    def action(self, uid, request_id, gift_id=None, character_id=None):
        if character_id is not None and character_id!=CHARACTER['id']:
            raise ProviderFailure('character_not_found','尚未开放这个角色。',404)
        if gift_id is not None and gift_id not in GIFTS:
            raise ProviderFailure('gift_not_found','未找到这份礼物。',422)
        action = 'gift:'+gift_id if gift_id else 'demo_credit'
        now = self.clock()
        with self.transaction(uid) as db:
            account,bond = self.rows(db,uid)
            previous = db.get(Entry,(uid,request_id))
            if previous:
                if previous.action!=action or previous.character_id!=bond.character_id:
                    raise ProviderFailure('request_conflict','这次操作标识已用于另一项操作，请刷新。',409)
                return self.snapshot(db,account,bond)
            if gift_id:
                gift = GIFTS[gift_id]
                if bond.score>=100:
                    raise ProviderFailure('bond_full','亲密度已满，不再扣币送礼；仍可继续聊天。',409)
                if account.coins<gift['price']:
                    raise ProviderFailure('insufficient_coins','演示币不足，可以继续免费聊天积累亲密度。',409)
                delta = -gift['price']
                points = min(gift['points'],100-bond.score)
                bond.score += points
            else:
                day = now.date().isoformat()  # Server UTC day; client clock is never accepted.
                if account.credit_day!=day:
                    account.credit_day=day; account.credits_today=0
                if account.credits_today>=5:
                    raise ProviderFailure('demo_daily_limit','今天已领取500演示币，明天再来；聊天不受影响。',429)
                account.credits_today+=1
                delta,points = 100,0
            account.coins += delta
            db.add(Entry(user_id=uid, request_id=request_id, action=action,
                         character_id=bond.character_id, coins_delta=delta,points_delta=points,created_at=now))
            db.flush()
            return self.snapshot(db,account,bond)

    def successful_turn(self, uid, started_at):
        account, _ = self.complete_turn(uid, started_at)
        return account

    def complete_turn(self, uid, started_at, *, facts=(), source=None, epoch=None):
        """Commit candidate memories and time credit together, before session history."""
        with self.transaction(uid) as db:
            if epoch is not None and db.get(Player, uid).epoch != epoch:
                raise ProviderFailure('memory_changed', '设置已变化，本轮回复已撤销，请重新发送。', 409)
            account,bond = self.rows(db,uid)
            candidates = []
            for fact in facts:
                candidate = self.store.candidate(uid, fact, source, epoch, transaction=db)
                if candidate and candidate['status']=='candidate': candidates.append(candidate)
            if started_at is not None:
                self._credit_time(bond, started_at)
            return self.snapshot(db,account,bond),candidates

    def _credit_time(self, bond, started_at):
        # Only count the interval BEFORE generation. Stale/overlapping responses
        # must not rewind either the daily allowance or the completion anchor.
        if bond.last_turn is None or started_at > bond.last_turn:
            day = started_at.date().isoformat()
            if bond.talk_day!=day:
                bond.talk_day=day; bond.talk_points_today=0; bond.pending_seconds=0
            if bond.last_turn is not None:
                elapsed = int((started_at-bond.last_turn).total_seconds())
                if 0<elapsed<=300 and bond.talk_points_today<10:
                    seconds = min(elapsed,60)
                    bond.active_seconds+=seconds
                    points,remainder = divmod(bond.pending_seconds+seconds,60)
                    points = min(points,10-bond.talk_points_today,100-bond.score)
                    bond.score+=points; bond.talk_points_today+=points
                    bond.pending_seconds=remainder
        completed_at=self.clock()
        if bond.last_turn is None or completed_at>bond.last_turn:
            bond.last_turn=completed_at
