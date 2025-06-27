from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from uuid import uuid4

from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

sessions = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == "mbctennis" and password == "mbctennis":
        sid = str(uuid4())
        sessions[sid] = username
        resp = RedirectResponse("/landing", status_code=303)
        resp.set_cookie("session_id", sid)
        return resp
    raise HTTPException(status_code=403, detail="Invalid credentials")

def check_login(request: Request):
    sid = request.cookies.get("session_id")
    if not sid or sid not in sessions:
        raise HTTPException(status_code=401, detail="Not logged in")

@app.get("/landing", response_class=HTMLResponse)
def landing(request: Request):
    check_login(request)
    return templates.TemplateResponse("landing.html", {"request": request})

# Add player
@app.get("/add_player", response_class=HTMLResponse)
def add_player_form(request: Request):
    check_login(request)
    return templates.TemplateResponse("add_player.html", {"request": request})

@app.post("/add_player")
def add_player(name: str = Form(...), rating: float = Form(...), db: Session = Depends(get_db)):
    if db.query(models.Player).filter(models.Player.name == name).first():
        raise HTTPException(status_code=400, detail="Player exists.")
    db.add(models.Player(name=name, rating=rating))
    db.commit()
    return RedirectResponse("/landing", status_code=303)

# Sort players
@app.get("/sort_players", response_class=HTMLResponse)
def sort_players(request: Request, db: Session = Depends(get_db)):
    check_login(request)
    players = db.query(models.Player).all()
    return templates.TemplateResponse("sort_players.html", {"request": request, "players": players})

@app.post("/sort_players", response_class=HTMLResponse)
def sort_players_post(request: Request, selected: list = Form(...), db: Session = Depends(get_db)):
    players = (
        db.query(models.Player)
        .filter(models.Player.name.in_(selected))
        .order_by(models.Player.rating.desc())
        .all()
    )
    return templates.TemplateResponse(
        "sorted_players.html",
        {"request": request, "players": players},
    )


# New table: step 1 - choose n
@app.get("/new_table", response_class=HTMLResponse)
def new_table_select(request: Request):
    check_login(request)
    return templates.TemplateResponse("new_table_select.html", {"request": request})

# New table: step 2 - build form with n rows
@app.post("/new_table_rows", response_class=HTMLResponse)
def new_table_rows(request: Request, n: int = Form(...), db: Session = Depends(get_db)):
    check_login(request)
    players = db.query(models.Player).all()
    return templates.TemplateResponse("new_table_rows.html", {"request": request, "n": n, "players": players})

@app.post("/save_table")
def save_table(
    n: int = Form(...),
    player: list = Form(...),
    s2: list = Form(...),
    s3: list = Form(...),
    s4: list = Form(...),
    s5: list = Form(...),
    s6: list = Form(...),
    db: Session = Depends(get_db)
):
    table = []
    for i in range(n):
        sum_val = sum(int(x[i]) for x in [s2, s3, s4, s5, s6])
        table.append({
            "player": player[i],
            "sum": sum_val
        })
    db.add(models.TableData(data=table))
    db.commit()
    return RedirectResponse("/landing", status_code=303)

@app.get("/view_tables", response_class=HTMLResponse)
def view_tables(request: Request, db: Session = Depends(get_db)):
    check_login(request)
    tables = db.query(models.TableData).all()
    return templates.TemplateResponse("view_tables.html", {"request": request, "tables": tables})

@app.post("/apply_ratings/{table_id}")
def apply_ratings(table_id: int, db: Session = Depends(get_db)):
    table_obj = db.query(models.TableData).get(table_id)
    if not table_obj:
        raise HTTPException(status_code=404, detail="Not found.")
    table = table_obj.data
    total_sum = sum(r["sum"] for r in table)
    deltas = {}
    player_ratings = {p.name: p.rating for p in db.query(models.Player).all()}
    n = len(table)
    for row in table:
        pid = row["player"]
        opps = [r["player"] for r in table if r["player"] != pid]
        opp_ratings = [player_ratings[o] for o in opps]
        avg_opp = sum(opp_ratings) / len(opp_ratings) if opp_ratings else 0
        me_rating = player_ratings[pid]
        scaled_op = avg_opp - me_rating
        scaled_score = (row["sum"] / total_sum) * n - 1 if total_sum > 0 else 0
        deltas[pid] = scaled_op + scaled_score
    for pid, dr in deltas.items():
        p = db.query(models.Player).filter(models.Player.name == pid).first()
        p.rating += int(dr)
    db.commit()
    return {"updated": deltas}

signup_list = []

@app.get("/signup_list", response_class=HTMLResponse)
def signup_get(request: Request, db: Session = Depends(get_db)):
    players = db.query(models.Player).order_by(models.Player.name).all()
    sorted_list = sorted(signup_list, key=lambda p: p.rating, reverse=True)
    return templates.TemplateResponse("signup_list.html", {
        "request": request,
        "players": players,
        "signup_list": sorted_list
    })

@app.post("/signup_list", response_class=HTMLResponse)
def signup_post(request: Request, name: str = Form(...), db: Session = Depends(get_db)):
    global signup_list
    player = db.query(models.Player).filter(models.Player.name == name).first()
    if player and player not in signup_list:
        signup_list.append(player)
    sorted_list = sorted(signup_list, key=lambda p: p.rating, reverse=True)
    players = db.query(models.Player).order_by(models.Player.name).all()
    return templates.TemplateResponse("signup_list.html", {
        "request": request,
        "players": players,
        "signup_list": sorted_list
    })

@app.post("/signup_discard", response_class=HTMLResponse)
def discard_signup(request: Request):
    global signup_list
    signup_list = []
    return RedirectResponse(url="/signup_list", status_code=303)

