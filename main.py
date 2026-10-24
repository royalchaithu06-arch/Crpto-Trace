import os, csv, io, secrets
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from .database import Base, engine, get_db
from .models import User, Wallet, Transaction, Alert, Case, CaseNote, AuditEvent, MentorProgress, SessionToken
from .security import pwd_context, current_user, create_session, hash_token, require_roles

Base.metadata.create_all(bind=engine)
app = FastAPI(title="CryptoTrace API", version="1.0.0", description="Fictional demo data only. Alerts are investigative leads, not proof.")
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET","POST","PATCH","DELETE"], allow_headers=["Authorization","Content-Type"])

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=72)
    terms_accepted: bool
class LoginIn(BaseModel):
    email: EmailStr
    password: str
class CaseIn(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    priority: str = "Medium"
    summary: str = ""
class NoteIn(BaseModel):
    note: str = Field(min_length=1, max_length=5000)
class AlertUpdate(BaseModel):
    status: str
class ProgressIn(BaseModel):
    lesson_key: str
    completed: bool = True

def audit(db, user_id, action, detail=""):
    db.add(AuditEvent(user_id=user_id, action=action, detail=detail[:1000]))
    db.commit()

@app.get("/")
def root():
    return {"name":"CryptoTrace API","docs":"/docs","mode":"DEMO DATA"}

@app.post("/api/auth/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if not payload.terms_accepted:
        raise HTTPException(400, "Terms acceptance is required")
    email = payload.email.lower()
    if db.query(User).filter(func.lower(User.email)==email).first():
        raise HTTPException(409, "Unable to create account with these details")
    user = User(name=payload.name.strip(), email=email, password_hash=pwd_context.hash(payload.password), role="Investigator")
    db.add(user); db.commit(); db.refresh(user)
    token = create_session(db, user); audit(db, user.id, "account.registered")
    return {"token":token,"user":{"id":user.id,"name":user.name,"email":user.email,"role":user.role}}

@app.post("/api/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email)==payload.email.lower()).first()
    if not user or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    token = create_session(db, user); audit(db, user.id, "auth.login")
    return {"token":token,"user":{"id":user.id,"name":user.name,"email":user.email,"role":user.role}}

@app.post("/api/auth/logout")
def logout(user: User = Depends(current_user), db: Session = Depends(get_db), creds=Depends(__import__("fastapi.security", fromlist=["HTTPBearer"]).HTTPBearer())):
    row = db.query(SessionToken).filter_by(token_hash=hash_token(creds.credentials), revoked=False).first()
    if row: row.revoked = True; db.commit()
    audit(db, user.id, "auth.logout")
    return {"ok":True}

@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return {"id":user.id,"name":user.name,"email":user.email,"role":user.role}

@app.get("/api/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    txs = db.query(Transaction).all()
    return {"demo":True,"transaction_count":len(txs),"wallet_count":db.query(Wallet).count(),
            "volume":round(sum(t.amount for t in txs),2),"open_alerts":db.query(Alert).filter(Alert.status!="Closed").count(),
            "case_count":db.query(Case).count(),"risk_distribution":{"high":db.query(Alert).filter(Alert.severity=="High").count(),"medium":db.query(Alert).filter(Alert.severity=="Medium").count(),"low":db.query(Alert).filter(Alert.severity=="Low").count()},
            "recent_transactions":[tx_out(t) for t in sorted(txs,key=lambda t:t.timestamp,reverse=True)[:6]]}

def tx_out(t):
    return {"id":t.id,"hash":t.tx_hash,"source":t.source_wallet,"destination":t.destination_wallet,"asset":t.asset,"amount":t.amount,"timestamp":t.timestamp.isoformat(),"network":t.network,"status":t.status}

@app.get("/api/transactions")
def transactions(q: str = "", network: str = "", asset: str = "", min_amount: float | None = None, max_amount: float | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = db.query(Transaction)
    if q: query = query.filter(or_(Transaction.tx_hash.ilike(f"%{q[:100]}%"), Transaction.source_wallet.ilike(f"%{q[:100]}%"), Transaction.destination_wallet.ilike(f"%{q[:100]}%")))
    if network: query = query.filter(Transaction.network==network)
    if asset: query = query.filter(Transaction.asset==asset)
    if min_amount is not None: query = query.filter(Transaction.amount>=min_amount)
    if max_amount is not None: query = query.filter(Transaction.amount<=max_amount)
    total = query.count()
    items = query.order_by(Transaction.timestamp.desc()).offset(offset).limit(limit).all()
    return {"items":[tx_out(t) for t in items],"total":total,"limit":limit,"offset":offset,"demo":True}

@app.get("/api/wallets")
def wallets(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"address":w.address,"network":w.network,"label":w.label,"risk_score":w.risk_score,
             "incoming":round(sum(t.amount for t in db.query(Transaction).filter_by(destination_wallet=w.address).all()),2),
             "outgoing":round(sum(t.amount for t in db.query(Transaction).filter_by(source_wallet=w.address).all()),2)} for w in db.query(Wallet).all()]

@app.get("/api/wallets/{address}")
def wallet_detail(address: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    w = db.query(Wallet).filter_by(address=address).first()
    if not w: raise HTTPException(404,"Wallet not found")
    txs = db.query(Transaction).filter(or_(Transaction.source_wallet==address,Transaction.destination_wallet==address)).order_by(Transaction.timestamp.desc()).limit(100).all()
    return {"wallet":{"address":w.address,"network":w.network,"label":w.label,"risk_score":w.risk_score},"transactions":[tx_out(t) for t in txs],"notice":"Wallet addresses alone do not establish real-world identity."}

@app.get("/api/graph")
def graph(user: User = Depends(current_user), db: Session = Depends(get_db)):
    wallets = db.query(Wallet).all(); txs = db.query(Transaction).all()
    return {"nodes":[{"id":w.address,"label":w.address[:10]+"…","risk":w.risk_score} for w in wallets],
            "edges":[{"id":t.tx_hash,"source":t.source_wallet,"target":t.destination_wallet,"amount":t.amount,"asset":t.asset} for t in txs]}

@app.get("/api/alerts")
def alerts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id":a.id,"title":a.title,"severity":a.severity,"status":a.status,"rule":a.rule,"evidence":a.evidence,"tx_hash":a.tx_hash,"created_at":a.created_at.isoformat()} for a in db.query(Alert).order_by(Alert.created_at.desc()).all()]

@app.patch("/api/alerts/{alert_id}")
def update_alert(alert_id: int, payload: AlertUpdate, user: User = Depends(require_roles("Administrator","Investigator","Analyst")), db: Session = Depends(get_db)):
    if payload.status not in {"New","Under Review","Escalated","Closed"}: raise HTTPException(422,"Invalid alert status")
    a = db.query(Alert).filter_by(id=alert_id).first()
    if not a: raise HTTPException(404,"Alert not found")
    a.status=payload.status; db.commit(); audit(db,user.id,"alert.status_changed",f"{alert_id}:{payload.status}")
    return {"ok":True,"status":a.status}

@app.post("/api/detection/run")
def run_detection(user: User = Depends(require_roles("Administrator","Analyst")), db: Session = Depends(get_db)):
    txs = db.query(Transaction).all(); created = []
    for t in txs:
        if t.amount >= 75:
            exists = db.query(Alert).filter_by(tx_hash=t.tx_hash,rule="large_transfer").first()
            if not exists:
                a=Alert(title="Large transfer threshold exceeded",severity="High" if t.amount>=100 else "Medium",rule="large_transfer",tx_hash=t.tx_hash,evidence=f"Amount {t.amount} {t.asset} meets demo threshold >= 75. This deterministic rule may produce false positives.")
                db.add(a); created.append(t.tx_hash)
    db.commit(); audit(db,user.id,"detection.run",f"new_alerts={len(created)}")
    return {"created":len(created),"transaction_hashes":created,"rule":"large_transfer","threshold":75,"limitation":"A rule match is an investigative lead, not proof of fraud."}

@app.get("/api/cases")
def cases(user: User = Depends(current_user), db: Session = Depends(get_db)):
    query=db.query(Case)
    if user.role != "Administrator": query=query.filter(Case.owner_id==user.id)
    return [{"id":c.id,"code":c.case_code,"title":c.title,"status":c.status,"priority":c.priority,"summary":c.summary,"created_at":c.created_at.isoformat()} for c in query.order_by(Case.created_at.desc()).all()]

@app.post("/api/cases")
def create_case(payload: CaseIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    case=Case(case_code="CT-"+secrets.token_hex(4).upper(),title=payload.title,priority=payload.priority if payload.priority in {"Low","Medium","High"} else "Medium",summary=payload.summary[:5000],owner_id=user.id)
    db.add(case); db.commit(); db.refresh(case); audit(db,user.id,"case.created",case.case_code)
    return {"id":case.id,"code":case.case_code,"title":case.title,"status":case.status,"priority":case.priority}

@app.get("/api/cases/{case_id}/notes")
def get_notes(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c=db.query(Case).filter_by(id=case_id).first()
    if not c or (user.role!="Administrator" and c.owner_id!=user.id): raise HTTPException(404,"Case not found")
    return [{"id":n.id,"note":n.note,"created_at":n.created_at.isoformat()} for n in db.query(CaseNote).filter_by(case_id=case_id).order_by(CaseNote.created_at.desc()).all()]

@app.post("/api/cases/{case_id}/notes")
def add_note(case_id: int, payload: NoteIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c=db.query(Case).filter_by(id=case_id).first()
    if not c or (user.role!="Administrator" and c.owner_id!=user.id): raise HTTPException(404,"Case not found")
    n=CaseNote(case_id=case_id,user_id=user.id,note=payload.note); db.add(n); db.commit(); audit(db,user.id,"case.note_added",c.case_code)
    return {"ok":True,"id":n.id}

@app.get("/api/reports/transactions.csv")
def export_csv(user: User = Depends(current_user), db: Session = Depends(get_db)):
    output=io.StringIO(); writer=csv.writer(output)
    writer.writerow(["Transaction Hash","Source Wallet","Destination Wallet","Asset","Amount","Timestamp","Network","Status"])
    for t in db.query(Transaction).order_by(Transaction.timestamp.desc()).all():
        values=[t.tx_hash,t.source_wallet,t.destination_wallet,t.asset,str(t.amount),t.timestamp.isoformat(),t.network,t.status]
        safe=[("'"+v if isinstance(v,str) and v.startswith(("=","+","-","@","\t","\r")) else v) for v in values]
        writer.writerow(safe)
    audit(db,user.id,"report.csv_exported")
    return Response(content=output.getvalue(),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=cryptotrace-transactions-demo.csv"})

LESSONS = [
 {"key":"blockchain-basics","title":"Blockchain transaction basics","level":"Beginner","body":"A transaction records a value transfer or contract interaction on a network. Check its hash, network, timestamp, asset and status."},
 {"key":"wallet-graph","title":"Reading wallet graphs","level":"Beginner","body":"Nodes represent wallets and directed edges represent transfers. A connection indicates transaction flow, not common ownership."},
 {"key":"anomaly-detection","title":"Explainable anomaly detection","level":"Intermediate","body":"Rules flag activity that crosses a defined threshold. Review context, baseline, window, data quality and plausible benign explanations."},
 {"key":"false-positives","title":"False positives and limitations","level":"Intermediate","body":"High-value or rapid transfers may be legitimate. A rule match is a lead for review, not proof of fraud or identity."},
 {"key":"case-notes","title":"Investigation documentation","level":"Beginner","body":"Record the question, data source, timestamps, evidence references, alternatives considered, conclusion and limitations."}
]
@app.get("/api/mentor/lessons")
def lessons(user: User = Depends(current_user), db: Session = Depends(get_db)):
    done={p.lesson_key for p in db.query(MentorProgress).filter_by(user_id=user.id,completed=True).all()}
    return [{"key":x["key"],"title":x["title"],"level":x["level"],"body":x["body"],"completed":x["key"] in done} for x in LESSONS]

@app.post("/api/mentor/progress")
def progress(payload: ProgressIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if payload.lesson_key not in {x["key"] for x in LESSONS}: raise HTTPException(404,"Lesson not found")
    row=db.query(MentorProgress).filter_by(user_id=user.id,lesson_key=payload.lesson_key).first()
    if row: row.completed=payload.completed
    else: db.add(MentorProgress(user_id=user.id,lesson_key=payload.lesson_key,completed=payload.completed))
    db.commit(); return {"ok":True}

@app.get("/api/admin/audit")
def audit_log(user: User = Depends(require_roles("Administrator")), db: Session = Depends(get_db)):
    return [{"id":a.id,"user_id":a.user_id,"action":a.action,"detail":a.detail,"created_at":a.created_at.isoformat()} for a in db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(200).all()]
