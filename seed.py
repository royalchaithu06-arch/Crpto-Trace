from datetime import datetime, timedelta, timezone
from app.database import Base, engine, SessionLocal
from app.models import User, Wallet, Transaction, Alert, Case
from app.security import pwd_context

Base.metadata.create_all(bind=engine)
db=SessionLocal()
try:
    if not db.query(User).filter_by(email="admin@cryptotrace.local").first():
        db.add(User(name="Demo Administrator",email="admin@cryptotrace.local",password_hash=pwd_context.hash("ChangeMe123!"),role="Administrator"))
    addresses=[("0xDEMO000000000000000000000000000000000001","Treasury-like demo wallet",24),
               ("0xDEMO000000000000000000000000000000000002","High activity demo wallet",82),
               ("0xDEMO000000000000000000000000000000000003","Unlabeled demo wallet",48),
               ("0xDEMO000000000000000000000000000000000004","Exchange-like demo wallet",12),
               ("0xDEMO000000000000000000000000000000000005","Unlabeled demo wallet",65)]
    for a,label,risk in addresses:
        if not db.query(Wallet).filter_by(address=a).first(): db.add(Wallet(address=a,label=label,risk_score=risk,network="Ethereum"))
    db.commit()
    now=datetime.now(timezone.utc)
    pairs=[(0,1,12.5),(1,2,82.0),(2,3,4.2),(1,4,101.0),(4,2,8.3),(0,3,2.1),(3,1,76.0),(2,4,15.4),(4,0,3.3),(1,3,23.5),(0,2,9.1),(3,4,79.0)]
    for i,(s,d,amt) in enumerate(pairs):
        txhash=f"0xDEMO{i+1:060x}"
        if not db.query(Transaction).filter_by(tx_hash=txhash).first():
            db.add(Transaction(tx_hash=txhash,source_wallet=addresses[s][0],destination_wallet=addresses[d][0],asset="ETH" if i%3 else "USDC",amount=amt,timestamp=now-timedelta(hours=i*4),network="Ethereum",status="confirmed"))
    db.commit()
    if db.query(Alert).count()==0:
        db.add_all([
          Alert(title="Large transfer threshold exceeded",severity="High",status="New",rule="large_transfer",evidence="Demo transfer amount crosses the configured threshold. Context and benign explanations must be reviewed.",tx_hash="0xDEMO0000000000000000000000000000000000000000000000000000000000000004"),
          Alert(title="Repeated wallet interaction",severity="Medium",status="Under Review",rule="repeated_interaction",evidence="Several fictional transfers connect the same demo wallets. This pattern alone does not establish wrongdoing.",tx_hash="0xDEMO0000000000000000000000000000000000000000000000000000000000000002")
        ])
    admin=db.query(User).filter_by(email="admin@cryptotrace.local").first()
    if admin and db.query(Case).count()==0:
        db.add(Case(case_code="CT-DEMO001",title="Sample transfer review",status="Open",priority="High",owner_id=admin.id,summary="Fictional training case. Review transaction context and record alternative explanations."))
    db.commit()
    print("Seed complete. DEMO DATA loaded.")
finally: db.close()
