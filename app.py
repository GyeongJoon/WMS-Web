from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import io
import base64

app = Flask(__name__)
app.secret_key = 'sungkyul'

# 데이터베이스 연결 설정
def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='joon',
            password='1234',
            database='backend'
        )
    except Error as e:
        print(f"Error: '{e}'")
    return connection

# 데이터 가져오기 함수
def fetch_data(query, params=None):
    connection = create_connection()
    if connection is None:
        return []

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        records = cursor.fetchall()
        cursor.close()
    except Error as e:
        print(f"Error: '{e}'")
        records = []
    finally:
        connection.close()
    
    return records


# 차트 생성 함수
def create_chart(df, title, xlabel, ylabel, id_col, value_col, color='blue'):
    fig, ax = plt.subplots(figsize=(3, 2))  # 이미지 크기 조정
    ax.bar(df[id_col].astype(str), df[value_col], color=color)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xticklabels(df[id_col].astype(str), rotation=0)
    fig.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    return base64.b64encode(img.getvalue()).decode('utf8')

@app.route('/')
def index():
    return render_template('index.html')

# 메인 대시보드 라우트
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Incoming data chart
    incoming_query = "SELECT id, product_quantity FROM incoming where user_id = %s"
    incoming_data = fetch_data(incoming_query, (user_id,))
    incoming_df = pd.DataFrame(incoming_data)
    incoming_chart = ""
    if not incoming_df.empty:
        incoming_chart = create_chart(incoming_df, 'Incoming Records', 'ID', 'Quantity', 'id', 'product_quantity', color='blue')

    # Stock data chart
    stock_query = "SELECT id, stock_quantity FROM stock where user_id = %s"
    stock_data = fetch_data(stock_query, (user_id,))
    stock_df = pd.DataFrame(stock_data)
    stock_chart = ""
    if not stock_df.empty:
        stock_chart = create_chart(stock_df, 'Stock Records', 'ID', 'Quantity', 'id', 'stock_quantity', color='green')

    # Outbound registration data chart
    outbound_query = "SELECT id, planned_quantity FROM outbound_registration where user_id = %s"
    outbound_data = fetch_data(outbound_query, (user_id,))
    outbound_df = pd.DataFrame(outbound_data)
    outbound_chart = ""
    if not outbound_df.empty:
        outbound_chart = create_chart(outbound_df, 'Outbound Records', 'ID', 'Quantity', 'id', 'planned_quantity', color='red')

    return render_template('dashboard.html', incoming_chart=incoming_chart, stock_chart=stock_chart, outbound_chart=outbound_chart)

# 회원가입 라우트
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        telephone = request.form['telephone']
        role = request.form['role']
        
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO wms_user (user_id, password, telephone, role) VALUES (%s, %s, %s, %s)", 
                       (user_id, hashed_password, telephone, role))
        connection.commit()
        cursor.close()
        connection.close()
        
        return redirect('/login')
    return render_template('signup.html')

# 로그인 라우트
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM wms_user WHERE user_id=%s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[1]
            session['role'] = user[4]
            return redirect('/dashboard')
        else:
            return "Invalid credentials"
    
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect('/login')

# 기존 코드와 라우트
@app.route('/enterRegist')
def enterRegist():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('enterRegist.html')

@app.route('/submit', methods=['POST'])
def submit():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        consignor = request.form['consignor']
        product_type = request.form['product_type']
        product_quantity = request.form['product_quantity']
        arrival_date = request.form['arrival_date']
        arrival_manager = request.form['arrival_manager']
        storage_location = request.form['storage_location']
        product_status = request.form['product_status']
        progress_status = request.form['progress_status']

        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO incoming (user_id, consignor, product_type, product_quantity, arrival_date, arrival_manager, storage_location, product_status, progress_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, consignor, product_type, product_quantity, arrival_date, arrival_manager, storage_location, product_status, progress_status))

        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for('enterRegist'))

@app.route('/outboundRegist', methods=['GET', 'POST'])
def outboundRegist():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_id = session['user_id']
        consignor = request.form['consignor']
        product_type = request.form['product_type']
        planned_quantity = request.form['planned_quantity']
        planned_date = request.form['planned_date']
        storage_location = request.form['storage_location']
        product_status = request.form['product_status']
        progress_status = request.form['progress_status']

        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO outbound_registration (user_id, consignor, product_type, planned_quantity, planned_date, storage_location, product_status, progress_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, consignor, product_type, planned_quantity, planned_date, storage_location, product_status, progress_status))

        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for('outboundRegist'))

    return render_template('outboundRegist.html')

def update_stock():
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    # 입고 테이블에서 입고완료인 경우만 가져오기
    cursor.execute("""
        SELECT * FROM incoming WHERE progress_status = '입고완료'
    """)
    incoming_data = cursor.fetchall()

    for row in incoming_data:
        user_id = row['user_id']
        consignor = row['consignor']
        product_type = row['product_type']
        product_quantity = row['product_quantity']
        arrival_manager = row['arrival_manager']
        storage_location = row['storage_location']
        product_status = row['product_status']
        progress_status = row['progress_status']

        # 재고 테이블에서 동일한 화주와 상품종류가 있는지 확인
        cursor.execute("""
            SELECT * FROM stock WHERE user_id = %s AND consignor = %s AND product_type = %s AND storage_location = %s ORDER BY stock_update_date DESC LIMIT 1
        """, (user_id, consignor, product_type, storage_location))
        stock_entry = cursor.fetchone()

        if stock_entry:
            # 재고 수량을 계산
            new_quantity = stock_entry['stock_quantity'] + product_quantity
            # 재고 수량 업데이트
            cursor.execute("""
                UPDATE stock SET stock_quantity = %s, stock_update_date = %s, stock_manager = %s WHERE id = %s
            """, (new_quantity, datetime.now(), arrival_manager, stock_entry['id']))
        else:
            # 재고 테이블에 새로운 레코드 추가
            progress_status = "재고"
            cursor.execute("""
                INSERT INTO stock (user_id, consignor, product_type, stock_quantity, stock_update_date, stock_manager, storage_location, product_status, progress_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, consignor, product_type, product_quantity, datetime.now(), arrival_manager, storage_location, product_status, progress_status))

        # incoming 테이블의 progress_status를 '재고반영완료'로 업데이트
        cursor.execute("""
            UPDATE incoming SET progress_status = '재고반영완료' WHERE id = %s
        """, (row['id'],))

    connection.commit()
    cursor.close()
    connection.close()

def update_stock_outbound():
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    # 출고 테이블에서 출고승인인 경우만 가져오기
    cursor.execute("""
        SELECT * FROM outbound_registration WHERE progress_status = '출고승인'
    """)
    outbound_data = cursor.fetchall()

    for row in outbound_data:
        user_id = row['user_id']
        consignor = row['consignor']
        product_type = row['product_type']
        planned_quantity = row['planned_quantity']
        storage_location = row['storage_location']

        # 재고 테이블에서 동일한 화주와 상품종류가 있는지 확인
        cursor.execute("""
            SELECT * FROM stock WHERE user_id = %s, consignor = %s AND product_type = %s AND storage_location = %s ORDER BY stock_update_date DESC LIMIT 1
        """, (user_id, consignor, product_type, storage_location))
        stock_entry = cursor.fetchone()

        if stock_entry and stock_entry['stock_quantity'] >= planned_quantity:
            # 재고 수량을 계산
            new_quantity = stock_entry['stock_quantity'] - planned_quantity
            # 재고 수량 업데이트
            cursor.execute("""
                UPDATE stock SET stock_quantity = %s, stock_update_date = %s WHERE id = %s
            """, (new_quantity, datetime.now(), stock_entry['id']))

            # outbound_registration 테이블의 progress_status를 '출고완료'로 업데이트
            cursor.execute("""
                UPDATE outbound_registration SET progress_status = '출고완료' WHERE id = %s
            """, (row['id'],))

    connection.commit()
    cursor.close()
    connection.close()

@app.route('/enterView', methods=['GET'])
def enterView():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    page = request.args.get('page', 1, type=int)
    per_page = 5

    consignor = request.args.get('consignor', '')
    product_type = request.args.get('product_type', '')
    arrival_date = request.args.get('arrival_date', '')
    arrival_manager = request.args.get('arrival_manager', '')
    progress_status = request.args.get('progress_status', '')

    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT * FROM incoming
        WHERE user_id = %s AND consignor LIKE %s AND product_type LIKE %s AND arrival_date LIKE %s AND arrival_manager LIKE %s AND progress_status LIKE %s
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, (user_id, '%' + consignor + '%', '%' + product_type + '%', '%' + arrival_date + '%', '%' + arrival_manager + '%', '%' + progress_status + '%', per_page, (page-1)*per_page))

    results = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM incoming WHERE user_id = %s AND consignor LIKE %s AND product_type LIKE %s AND arrival_date LIKE %s AND arrival_manager LIKE %s AND progress_status LIKE %s",
                   (user_id, '%' + consignor + '%', '%' + product_type + '%', '%' + arrival_date + '%', '%' + arrival_manager + '%', '%' + progress_status + '%'))
    total = cursor.fetchone()['COUNT(*)']
    total_pages = (total + per_page - 1) // per_page

    cursor.close()
    connection.close()

    prev_url = url_for('enterView', page=page-1, consignor=consignor, product_type=product_type, arrival_date=arrival_date, arrival_manager=arrival_manager, progress_status=progress_status) if page > 1 else None
    next_url = url_for('enterView', page=page+1, consignor=consignor, product_type=product_type, arrival_date=arrival_date, arrival_manager=arrival_manager, progress_status=progress_status) if page < total_pages else None

    return render_template('enterView.html', results=results, total_pages=total_pages, current_page=page, prev_url=prev_url, next_url=next_url, 
                           consignor=consignor, product_type=product_type, arrival_date=arrival_date, arrival_manager=arrival_manager, progress_status=progress_status)

@app.route('/stockView', methods=['GET'])
def stockView():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    update_stock()
    
    user_id = session['user_id']

    page = request.args.get('page', 1, type=int)
    per_page = 5

    consignor = request.args.get('consignor', '')
    product_type = request.args.get('product_type', '')
    stock_manager = request.args.get('stock_manager', '')
    storage_location = request.args.get('storage_location', '')
    product_status = request.args.get('product_status', '')
    progress_status = request.args.get('progress_status', '')

    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT * FROM stock
        WHERE user_id = %s AND consignor LIKE %s AND product_type LIKE %s AND stock_manager LIKE %s AND storage_location LIKE %s AND product_status LIKE %s AND progress_status LIKE %s
        ORDER BY stock_update_date DESC
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, (user_id, '%' + consignor + '%', '%' + product_type + '%', '%' + stock_manager + '%', '%' + storage_location + '%', '%' + product_status + '%', '%' + progress_status + '%', per_page, (page-1)*per_page))

    results = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM stock WHERE user_id = %s AND consignor LIKE %s AND product_type LIKE %s AND stock_manager LIKE %s AND storage_location LIKE %s AND product_status LIKE %s AND progress_status LIKE %s",
                   (user_id, '%' + consignor + '%', '%' + product_type + '%', '%' + stock_manager + '%', '%' + storage_location + '%', '%' + product_status + '%', '%' + progress_status + '%'))
    total = cursor.fetchone()['COUNT(*)']
    total_pages = (total + per_page - 1) // per_page

    cursor.close()
    connection.close()

    prev_url = url_for('stockView', page=page-1, consignor=consignor, product_type=product_type, stock_manager=stock_manager, storage_location=storage_location, product_status=product_status, progress_status=progress_status) if page > 1 else None
    next_url = url_for('stockView', page=page+1, consignor=consignor, product_type=product_type, stock_manager=stock_manager, storage_location=storage_location, product_status=product_status, progress_status=progress_status) if page < total_pages else None

    return render_template('stockView.html', results=results, total_pages=total_pages, current_page=page, prev_url=prev_url, next_url=next_url, 
                           consignor=consignor, product_type=product_type, stock_manager=stock_manager, storage_location=storage_location, product_status=product_status, progress_status=progress_status)

@app.route('/stockManage', methods=['GET', 'POST'])
def stockManage():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        update_ids = request.form.getlist('update_id')
        storage_location = request.form.get('storage_location', '')
        progress_status = request.form.get('progress_status', '')

        connection = create_connection()
        cursor = connection.cursor()

        for update_id in update_ids:
            update_fields = []
            update_values = []

            if storage_location:
                update_fields.append("storage_location = %s")
                update_values.append(storage_location)
            if progress_status:
                update_fields.append("progress_status = %s")
                update_values.append(progress_status)

            update_values.append(user_id)
            update_values.append(update_id)
            if update_fields:
                cursor.execute(f"UPDATE stock SET {', '.join(update_fields)} WHERE user_id = %s AND id = %s", update_values)

        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for('stockManage'))

    page = request.args.get('page', 1, type=int)
    per_page = 5

    consignor = request.args.get('consignor', '')
    product_type = request.args.get('product_type', '')
    stock_manager = request.args.get('stock_manager', '')
    storage_location = request.args.get('storage_location', '')
    product_status = request.args.get('product_status', '')
    progress_status = request.args.get('progress_status', '')

    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT * FROM stock
        WHERE user_id = %s AND consignor LIKE %s AND product_type LIKE %s AND stock_manager LIKE %s AND storage_location LIKE %s AND product_status LIKE %s AND progress_status LIKE %s
        ORDER BY stock_update_date DESC
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, (user_id, '%' + consignor + '%', '%' + product_type + '%', '%' + stock_manager + '%', '%' + storage_location + '%', '%' + product_status + '%', '%' + progress_status + '%', per_page, (page-1)*per_page))

    results = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM stock WHERE user_id = %s AND consignor LIKE %s AND product_type LIKE %s AND stock_manager LIKE %s AND storage_location LIKE %s AND product_status LIKE %s AND progress_status LIKE %s",
                   (user_id, '%' + consignor + '%', '%' + product_type + '%', '%' + stock_manager + '%', '%' + storage_location + '%', '%' + product_status + '%', '%' + progress_status + '%'))
    total = cursor.fetchone()['COUNT(*)']
    total_pages = (total + per_page - 1) // per_page

    cursor.close()
    connection.close()

    prev_url = url_for('stockManage', page=page-1, consignor=consignor, product_type=product_type, stock_manager=stock_manager, storage_location=storage_location, product_status=product_status, progress_status=progress_status) if page > 1 else None
    next_url = url_for('stockManage', page=page+1, consignor=consignor, product_type=product_type, stock_manager=stock_manager, storage_location=storage_location, product_status=product_status, progress_status=progress_status) if page < total_pages else None

    return render_template('stockManage.html', results=results, total_pages=total_pages, current_page=page, prev_url=prev_url, next_url=next_url, 
                           consignor=consignor, product_type=product_type, stock_manager=stock_manager, storage_location=storage_location, product_status=product_status, progress_status=progress_status)

@app.route('/save_changes', methods=['POST'])
def save_changes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session["user_id"]

    update_ids = request.form.getlist('update_id')
    delete_ids = request.form.getlist('delete_id')
    consignor = request.form.get('consignor', '')
    product_type = request.form.get('product_type', '')
    product_quantity = request.form.get('product_quantity', '')
    arrival_date = request.form.get('arrival_date', '')
    arrival_manager = request.form.get('arrival_manager', '')
    storage_location = request.form.get('storage_location', '')
    product_status = request.form.get('product_status', '')
    progress_status = request.form.get('progress_status', '')

    connection = create_connection()
    cursor = connection.cursor()

    for update_id in update_ids:
        update_fields = []
        update_values = []

        if consignor:
            update_fields.append("consignor = %s")
            update_values.append(consignor)
        if product_type:
            update_fields.append("product_type = %s")
            update_values.append(product_type)
        if product_quantity:
            update_fields.append("product_quantity = %s")
            update_values.append(product_quantity)
        if arrival_date:
            update_fields.append("arrival_date = %s")
            update_values.append(arrival_date)
        if arrival_manager:
            update_fields.append("arrival_manager = %s")
            update_values.append(arrival_manager)
        if storage_location:
            update_fields.append("storage_location = %s")
            update_values.append(storage_location)
        if product_status:
            update_fields.append("product_status = %s")
            update_values.append(product_status)
        if progress_status:
            update_fields.append("progress_status = %s")
            update_values.append(progress_status)

        update_values.append(user_id)
        update_values.append(update_id)
        if update_fields:
            cursor.execute(f"UPDATE incoming SET {', '.join(update_fields)} WHERE user_id = %s AND id = %s", update_values)

    for delete_id in delete_ids:
        cursor.execute("DELETE FROM incoming WHERE user_id = %s AND id = %s", (user_id, delete_id))

    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('enterView'))

@app.route('/outboundView', methods=['GET'])
def outboundView():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    update_stock_outbound()
    
    user_id = session['user_id']

    page = request.args.get('page', 1, type=int)
    per_page = 5

    consignor = request.args.get('consignor', '')
    product_type = request.args.get('product_type', '')
    planned_date = request.args.get('planned_date', '')
    storage_location = request.args.get('storage_location', '')
    product_status = request.args.get('product_status', '')
    progress_status = request.args.get('progress_status', '')

    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT * FROM outbound_registration
        WHERE user_id = %s AND consignor LIKE %s AND product_type LIKE %s AND planned_date LIKE %s AND storage_location LIKE %s AND product_status LIKE %s AND progress_status LIKE %s
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, (user_id, '%' + consignor + '%', '%' + product_type + '%', '%' + planned_date + '%', '%' + storage_location + '%', '%' + product_status + '%', '%' + progress_status + '%', per_page, (page-1)*per_page))

    results = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM outbound_registration WHERE user_id = %s AND consignor LIKE %s AND product_type LIKE %s AND planned_date LIKE %s AND storage_location LIKE %s AND product_status LIKE %s AND progress_status LIKE %s",
                   (user_id, '%' + consignor + '%', '%' + product_type + '%', '%' + planned_date + '%', '%' + storage_location + '%', '%' + product_status + '%', '%' + progress_status + '%'))
    total = cursor.fetchone()['COUNT(*)']
    total_pages = (total + per_page - 1) // per_page

    cursor.close()
    connection.close()

    prev_url = url_for('outboundView', page=page-1, consignor=consignor, product_type=product_type, planned_date=planned_date, storage_location=storage_location, product_status=product_status, progress_status=progress_status) if page > 1 else None
    next_url = url_for('outboundView', page=page+1, consignor=consignor, product_type=product_type, planned_date=planned_date, storage_location=storage_location, product_status=product_status, progress_status=progress_status) if page < total_pages else None

    return render_template('outboundView.html', results=results, total_pages=total_pages, current_page=page, prev_url=prev_url, next_url=next_url, 
                           consignor=consignor, product_type=product_type, planned_date=planned_date, storage_location=storage_location, product_status=product_status, progress_status=progress_status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)