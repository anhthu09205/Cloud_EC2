from flask import Flask, jsonify, request, render_template, Response, render_template_string, redirect
import time, requests, os

import json
import pymysql

from jose import jwt, jwk
from jose.utils import base64url_decode

ISSUER   = os.getenv("OIDC_ISSUER",   "http://authentication-identity-server:8080/realms/realm_523H0100")
AUDIENCE = os.getenv("OIDC_AUDIENCE", "account")
JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"

_JWKS = None; _TS = 0
def get_jwks():
    global _JWKS, _TS
    now = time.time()
    if not _JWKS or now - _TS > 600:
        _JWKS = requests.get(JWKS_URL, timeout=5).json()
        _TS = now
    return _JWKS

app = Flask(__name__)
app.json.ensure_ascii = False

from flask import request, jsonify, Response

@app.get("/hello")
def hello():
    data = {"message": "Hello teacher Bui Quy Anh!"}

    # nếu browser → trả HTML
    if "text/html" in request.headers.get("Accept", ""):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Hello API</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial;
                    background: linear-gradient(135deg, #eef2f3, #dfe9f3);
                    padding: 50px;
                    text-align: center;
                }}

                .card {{
                    background: white;
                    padding: 40px;
                    border-radius: 15px;
                    box-shadow: 0 8px 20px rgba(0,0,0,0.15);
                    display: inline-block;
                }}

                h1 {{
                    color: #2c3e50;
                    margin-bottom: 10px;
                }}

                .message {{
                    font-size: 18px;
                    color: #27ae60;
                    margin: 15px 0;
                }}

                .sub {{
                    color: #7f8c8d;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Welcome to MyMiniCloud 🚀</h1>
                <div class="message">{data["message"]}</div>
                <div class="sub">Our backend service is up and running</div>
            </div>
        </body>
        </html>
        """

    # nếu API → trả JSON
    return jsonify(data)


@app.get("/secure")
def secure():
    auth = request.headers.get("Authorization", "")

    if not auth.startswith("Bearer "):
        return {"error": "Missing token"}, 401

    token = auth.split(" ")[1]

    try:
        payload = verify_token(token)

        return {
            "message": "Secure resource OK",
            "preferred_username": payload.get("preferred_username")
        }
    except Exception as e:
        return {"error": str(e)}, 401
    
#=========
#Phần mở rộng blog
#=========
BLOG_FILE = "blogs.json"

def verify_token(token):
    jwks = get_jwks()

    headers = jwt.get_unverified_header(token)
    kid = headers["kid"]

    key = None
    for k in jwks["keys"]:
        if k["kid"] == kid:
            key = k
            break

    if not key:
        raise Exception("Public key not found")

    public_key = jwk.construct(key)

    message, encoded_signature = token.rsplit('.', 1)
    decoded_signature = base64url_decode(encoded_signature.encode())

    if not public_key.verify(message.encode(), decoded_signature):
        raise Exception("Signature verification failed")

    payload = jwt.get_unverified_claims(token)

    # check issuer
    if payload.get("iss") != ISSUER:
        raise Exception("Invalid issuer")

    # check audience
    aud = payload.get("aud")
    if isinstance(aud, str):
        aud = [aud]
    if AUDIENCE not in aud:
        raise Exception("Invalid audience")

    return payload

def load_blogs():
    with open(BLOG_FILE) as f:
        return json.load(f)

def save_blogs(data):
    with open(BLOG_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.get("/blog")
def get_blogs():
    return jsonify(load_blogs())

@app.post("/blog")
def create_blog():
    data = load_blogs()
    new = request.json
    new["id"] = len(data) + 1
    data.append(new)
    save_blogs(data)
    return jsonify(new)

@app.delete("/blog/<int:id>")
def delete_blog(id):
    data = load_blogs()
    data = [b for b in data if b["id"] != id]
    save_blogs(data)
    return jsonify({"status": "deleted"})

@app.put("/blog/<int:id>")
def update_blog(id):
    data = load_blogs()
    new_data = request.json

    for i, b in enumerate(data):
        if b["id"] == id:
            # update dữ liệu
            data[i].update(new_data)

            # lưu lại file
            save_blogs(data)

            return jsonify(data[i])

    return jsonify({"error": "Not found"}), 404

#========
# Phần 2
#========
@app.get("/student")
@app.get("/student/")
def student():
    with open("students.json", encoding="utf-8") as f:
        data = json.load(f)

    # nếu browser → HTML
    if "text/html" in request.headers.get("Accept", ""):
        return render_template("student_json.html", data=data)

    # nếu API → JSON
    return jsonify(data)

@app.get("/student/view")
def student_view():
    with open("students.json", encoding="utf-8") as f:
        data = json.load(f)
    return render_template("student_json.html", data=data)

#========
# Phần 3
#========

# kết nối tới MariaDB container
def get_db():
    return pymysql.connect(
        host="relational-database-server",  # tên service docker
        user="root",
        password="root",
        database="studentdb",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

@app.get("/students-db")
def students_db():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM students")
        data = cur.fetchall()
    conn.close()

    # format date
    for row in data:
        if row["dob"]:
            row["dob"] = row["dob"].strftime("%Y-%m-%d")

    # nếu mở browser → trả HTML
    if "text/html" in request.headers.get("Accept", ""):
        return render_template("student_db.html", data=data)

    # nếu gọi API → trả JSON
    return jsonify(data)

# hiển thị web bảng sinh viên
@app.get("/students-db/view")
def view_students():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM students")
        data = cur.fetchall()
    conn.close()

    # format date
    for row in data:
        if row["dob"]:
            row["dob"] = row["dob"].strftime("%Y-%m-%d")

    return render_template("student_db.html", data=data)

# thêm sinh viên (CREATE)
@app.post("/students-db-add")
def add_student():
    data = request.form

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO students (student_id, fullname, dob, major)
            VALUES (%s, %s, %s, %s)
        """, (data["student_id"], data["fullname"], data["dob"], data["major"]))
        conn.commit()
    conn.close()

    return redirect("/api/students-db")

# sửa sinh viên (UPDATE)
@app.post("/students-db/update/<int:id>")
def update_student(id):
    data = request.json

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE students 
            SET student_id=%s, fullname=%s, dob=%s, major=%s
            WHERE id=%s
        """,(data["student_id"], data["fullname"], data["dob"], data["major"], id))
        conn.commit()
    conn.close()

    return {"msg":"updated"}

# xoá sinh viên (DELETE)
@app.post("/students-db/delete/<int:id>")
def delete_student(id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM students WHERE id=%s",(id,))
        conn.commit()
    conn.close()

    return {"msg":"deleted"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
    
    
