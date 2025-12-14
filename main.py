from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import requests
from collections import defaultdict
from starlette.requests import Request

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

SENDSAY_API_URL = "https://api.sendsay.ru"

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload_excel/")
async def upload_excel(
    file: UploadFile = File(...),
    login: str = Form(...),
    api_key: str = Form(...)
):
    df = pd.read_excel(file.file)
    required_columns = [
        "№ позиции","Id Действия","Действие","Дата","Время","Рег.номер билета",
        "Штрихкод/BARCODE","Время создания билета","Оплата  (руб.)","ID места/SEAT_ID",
        "Номер Заказа","Место","ФИО Покупателя","EMAIL Покупателя","Телефон Покупателя","Канал продажи"
    ]
    if not all(col in df.columns for col in required_columns):
        return {"error": "Не все необходимые колонки присутствуют в Excel"}

    orders = defaultdict(list)
    for _, row in df.iterrows():
        email = row["EMAIL Покупателя"]
        ticket = {
            "ticket_number": row["Рег.номер билета"],
            "barcode": row["Штрихкод/BARCODE"],
            "seat_id": row["ID места/SEAT_ID"],
            "place": row["Место"],
            "price": float(row["Оплата  (руб.)"]),
            "date": str(row["Дата"]),
            "time": str(row["Время"]),
            "action_id": row["Id Действия"],
            "action_name": row["Действие"],
            "fio": row["ФИО Покупателя"],
            "phone": row["Телефон Покупателя"],
            "channel": row["Канал продажи"],
            "order_id": str(row["Номер Заказа"])
        }
        orders[email].append(ticket)

    parsed_data = []
    for email, tickets in orders.items():
        parsed_data.append({
            "email": email,
            "order_id": tickets[0]["order_id"],
            "tickets": tickets,
            "total_amount": sum(t["price"] for t in tickets)
        })

    return {"parsed_data": parsed_data}

@app.post("/send_sendsay/")
async def send_sendsay(data: dict):
    login = data.get("login")
    api_key = data.get("api_key")
    sales_data = data.get("sales_data", [])

    if not login or not api_key:
        return {"error": "Не указан login или api_key"}

    payload = {
        "method": "ecom.data.add",
        "params": {"data": sales_data}
    }

    response = requests.post(
        SENDSAY_API_URL,
        json=payload,
        auth=(login, api_key)
    )

    return {"status": response.status_code, "response": response.json()}
