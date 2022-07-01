from flask import Flask, render_template, request, url_for, redirect, json
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime, timedelta
from random import *
import random
import json
from faker import Faker
from sqlalchemy import desc
import pandas as pd
import sqlite3
from sqlite3 import Error


basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database/products.db'
db = SQLAlchemy(app)
fake = Faker()
name1 = ""

db_local = 'database/products.db'
con = sqlite3.connect(db_local, check_same_thread=False)
c = con.cursor()




# CLASSE USUÁRIOS
class Users(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50))
    name = db.Column(db.String(50))
    surname = db.Column(db.String(50))
    company = db.Column(db.String(50))
    telephone = db.Column(db.Integer)
    address = db.Column(db.String(50))
    nif = db.Column(db.Integer)

    orders = db.relationship('Order', backref='users')


order_kart = db.Table('order_kart',
    db.Column('order_id', db.Integer, db.ForeignKey('order.id')),
    db.Column('kart_serial', db.Integer, db.ForeignKey('kart.serial'))
)


# CLASSE PRODUTO
class Product(db.Model):
    __tablename__ = "product"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    image = db.Column(db.String(260))
    category = db.Column(db.String(50))
    amount = db.Column(db.Integer)
    price = db.Column(db.Integer)
    description = db.Column(db.String(300))
    provider = db.Column(db.String(50))
    origin_price = db.Column(db.Integer)

    def __repr__(self):
        return '<Product %r>' % self.name


# CLASSE KART
class Kart(db.Model):
    __tablename__ = "kart"
    serial = db.Column(db.Integer, primary_key=True)
    client = db.Column(db.String(50))
    product = db.Column(db.String(50))
    amount = db.Column(db.Integer)
    price = db.Column(db.Integer)
    provider = db.Column(db.String(50))

    def __repr__(self):
        return '<Product %r>' % self.name


# CLASSE Pedidos
class Order(db.Model):
    __tablename__ = "order"
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.company'), nullable=False)
    total = db.Column(db.Integer)

    products = db.relationship('Kart', secondary=order_kart)


class Stock(db.Model):
    __tablename__ = "stock"
    id = db.Column(db.Integer, primary_key=True)
    stock_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    provider_company = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total = db.Column(db.Integer)
    amount = db.Column(db.Integer)
    product = db.Column(db.String(50))


db.create_all()  # Criação das tabelas
db.session.commit()  # Execução das tarefas pendentes da base de dados


# Dicionários com os registos de cada tipo de login
database_customer = {'Bill': '9876', 'Cris': '1111'}
database_provider = {'Provider1': '1010', 'Provider2': '2020', 'Provider3': '3030', 'Provider4': '4040'}
database_administrator = {'Jeff': '1234'}



# Rota Inicial
@app.route('/')
def initial():
    return render_template("login.html")


# Rota Login
@app.route('/form_login', methods=['POST', 'GET'])
def login():
    global name1
    name1 = request.form['username']
    pwd = request.form['password']
    if name1 in database_customer:
        if database_customer[name1] != pwd:
            return render_template('login.html', info='Wrong Password')
        else:
            return redirect(url_for('customer'))
    if name1 in database_provider:
        if database_provider[name1] != pwd:
            return render_template('login.html', info='Wrong Password')
        else:
            return redirect(url_for('provider'))
    if name1 in database_administrator:
        if database_administrator[name1] != pwd:
            return render_template('login.html', info='Wrong Password')
        else:
            return redirect(url_for('useradmin'))
    else:
        return render_template('login.html', info='User Not Found')


# Rota administrador
@app.route('/useradmin')
def useradmin():
    if name1 in database_administrator:
        products = Product.query.all()
        product = Product.query.first()
        week_value, date = weekly_sale()
        month_value, month = month_sale()
        day_value, day = daily_sale()
        category_value, category = category_sale()
        top = top_seven()
        product_ending = notification()
        #sold_amount = db.session.query(db.func.sum(Kart.amount)).group_by(Kart.product).filter_by(product=str(product.name)).first()
        c.execute(f"""
        SELECT SUM(kart.amount), kart.product
        FROM kart
        INNER JOIN product
        WHERE kart.product = product.name
        AND product.name = '{product.name}'
        GROUP BY kart.product
        LIMIT 1;
        """)
        query = c.fetchall()
        con.commit()
        month_stock, month_st = monthly_stock()
        return render_template('useradmin.html', nome_utilizador=name1, products=products,
                                   week_value=json.dumps(week_value),
                                   date=json.dumps(date), month_value=json.dumps(month_value), month=json.dumps(month),
                                   day_value=json.dumps(day_value), day=json.dumps(day),
                                   category_value=json.dumps(category_value),
                                   category=json.dumps(category), top=top, product_ending=product_ending,
                                   sold_amount=query[0][:1],
                                   month_stock=json.dumps(month_stock), month_st=json.dumps(month_st))
    else:
        return redirect(request.referrer)


@app.route('/product_painel')
def product_painel():
    products = Product.query.all()
    return render_template('product_painel.html', nome_utilizador=name1, products=products)


@app.route('/sales')
def sales():
    orders = Order.query.order_by(desc(Order.order_date)).all()
    return render_template('sales.html', nome_utilizador=name1, orders=orders)


# Rota Fornecedor
@app.route('/provider', methods=['POST', 'GET'])
def provider():
    user = Users.query.filter_by(login=name1).first()
    if user.company == "Admin":
        products = Product.query.all()
        kart = Kart.query.all()
        sell = provider_sell(user.company)
        stock = db.session.query(Stock).all()
        month_value, month = monthly_sale_provider(user.company)
        return render_template('provider.html', user=user, kart=kart, products=products, sell=sell, stock=stock,
                               month_value=json.dumps(month_value), month=json.dumps(month))
    else:
        user = Users.query.filter_by(login=name1).first()
        products = Product.query.filter_by(provider=str(user.company)).all()
        kart = Kart.query.all()
        sell = provider_sell(user.company)
        stock = db.session.query(Stock).filter_by(provider_company=str(user.company)).all()
        month_value, month = monthly_sale_provider(user.company)
        return render_template('provider.html', user=user, kart=kart, products=products, sell=sell, stock=stock,
                               month_value=json.dumps(month_value), month=json.dumps(month))


# Rota Portal_Fornecedor
@app.route('/provider_portal', methods=['POST', 'GET'])
def provider_portal():
    user = Users.query.filter_by(login=name1).first()
    if user.company == "Admin":
        products = Product.query.all()
        kart = Kart.query.all()
    else:
        products = Product.query.filter_by(provider=str(user.company)).all()
        kart = Kart.query.all()
    return render_template('provider_portal.html', user=user, kart=kart, products=products)


@app.route('/stock_history', methods=['POST', 'GET'])
def stock_history():
    user = Users.query.filter_by(login=name1).first()
    if user.company == "Admin":
        #stock = db.session.query(Stock).order_by(desc(Stock.stock_date)).all()
        c.execute(f"""
                SELECT *
                FROM stock
                ORDER BY stock.stock_date DESC;""")
        query = c.fetchall()
        con.commit()
    else:
        #stock = db.session.query(Stock).filter_by(provider_company=str(user.company)).order_by(desc(Stock.stock_date)).all()
        c.execute(f"""
        SELECT *
        FROM stock
        INNER JOIN users
        WHERE stock.provider_company = users.company
        AND stock.provider_company = '{user.company}'
        ORDER BY stock.stock_date DESC;""")
        query = c.fetchall()
        con.commit()
    return render_template('stock_history.html', nome_utilizador=name1, stock=query)


# Rota Cliente
@app.route('/customer', methods=['POST', 'GET'])
def customer():
    user = Users.query.filter_by(login=name1).first()
    products = Product.query.all()
    kart = Kart.query.filter_by(client=name1)
    return render_template('customer.html', user=user, kart=kart, products=products)


@app.route('/purchase', methods=['POST', 'GET'])
def purchase():
    user = Users.query.filter_by(login=name1).first()
    orders = Order.query.filter_by(customer_id=int(user.id)).order_by(desc(Order.order_date)).all()
    return render_template('purchase.html', nome_utilizador=name1, orders=orders)


# Atualizar Produtos
@app.route('/update_product', methods=['POST'])
def update_product():
    pk = request.form['pk']
    name = request.form['name']
    value = request.form['value']
    item = Product.query.filter_by(id=int(pk)).first()
    if name == 'name':
        item.name = value
    elif name == 'amount':
        item.amount = value
    elif name == 'price':
        item.price = value
    elif name == 'description':
        item.description = value
    elif name == 'image':
        item.image = value
    elif name == 'category':
        item.category = value
    db.session.commit()
    return json.dumps({'status': 'OK'})


# Adicionar Produto
@app.route('/add_product', methods=['POST'])
def add_product():
    try:
        new_product = Product(name=request.form['product_name'], description=request.form['product_description'],
                              category=request.form['product_category'], amount=request.form['product_amount'],
                              price=request.form['product_price'], image=request.form['product_image'], provider=request.form['provider'])
        db.session.add(new_product)
        db.session.commit()
        return redirect(request.referrer)

    except Exception as e:
        print(e)
    finally:
        return redirect(request.referrer)


# Adicionar Stock
@app.route('/add_stock', methods=['POST'])
def add_stock():
    name = request.form['product_name']
    amount = int(request.form['product_amount'])
    item = Product.query.filter_by(name=str(name)).first()
    item.amount += amount
    stock = Stock(
        product=name,
        provider_company=item.provider,
        total=(amount * item.origin_price),
        amount=amount,
        )
    db.session.add(stock)
    db.session.commit()
    return redirect(request.referrer)


# Deletar Produto
@app.route('/delete_product/<id>')
def delete_product(id):
    item = Product.query.filter_by(id=int(id)).delete()
    db.session.commit()
    return redirect(request.referrer)


# Adicionar produto ao carrinho
@app.route('/add_item', methods=['POST'])
def add_item():
    try:
        kart_item = Kart(product=request.form['product_name'], client=request.form['customer_name'],
                         amount=request.form['amount_kart'], price=request.form['product_price'],
                         provider=request.form['product_provider'])
        db.session.add(kart_item)  # Adicionar o objeto da Tarefa à base de dados
        db.session.commit()  # Executar a operação pendente da base de dados
        return redirect(request.referrer)
    except Exception as e:
        print(e)
    finally:
        return redirect(request.referrer)


# Eliminar produto do carrinho
@app.route('/delete_item/<serial>')
def delete(serial):
    item = Kart.query.filter_by(serial=int(serial)).delete()
    db.session.commit()
    return redirect(request.referrer)


# Check out
@app.route('/checkout', methods=['POST'])
def checkout():
    customers = request.form['customer']
    item = Kart.query.filter_by(client=str(customers)).all()
    client = Users.query.filter_by(name=str(customers)).first()
    item_list = []
    total = 0
    for i in item:
        serial = i.serial
        item_product = Product.query.filter_by(name=str(i.product)).first()
        kart_product = Kart.query.filter_by(serial=int(serial)).first()
        price_total = kart_product.price*kart_product.amount
        total += price_total
        item_product.amount = item_product.amount - i.amount
        kart_product.client = ""
        item_list.append(kart_product)
    order = Order(customer_id=client.id, products=item_list, total=total)
    db.session.add(order)
    db.session.commit()
    return redirect(request.referrer)


# >>>>>>>> End Route <<<<<<<<<<<<


def daily_sale():
    day_value = []
    day = []
    time = timedelta(days=1)
    timenow = datetime.now()
    order_past = 0
    for x in range(15):
        d = datetime.now() - timedelta(days=x)
        d1 = datetime.now() - timedelta(days=(x-1))
        day.append(d.strftime("%d-%m-%Y"))
        #orders = db.session.query(db.func.sum(Order.total)).filter(Order.order_date > (timenow - time)).scalar()
        c.execute(f"""
                SELECT SUM(total) 
                FROM "main"."order"
                WHERE "main"."order".order_date > ('{d1}')
                ;""")
        orders = c.fetchall()
        con.commit()
        orders = orders[0][0]
        if orders is None:
            orders = 0
        orders -= order_past
        order_past += orders
        timenow -= time
        day_value.append(orders)
    return day_value, day


def weekly_sale():
    week_value = []
    date = []
    time = timedelta(weeks=1)
    timenow = datetime.now()
    order_past = 0
    true_week_number = 0
    for x in range(12):
        d = datetime.now() - timedelta(weeks=x)
        d1 = datetime.now() - timedelta(weeks=true_week_number)
        date.append(d.strftime("%d-%m-%Y"))
        #orders = db.session.query(db.func.sum(Order.total)).filter(Order.order_date > (timenow - time)).scalar()
        c.execute(f"""
                        SELECT SUM(total) 
                        FROM "main"."order"
                        WHERE "main"."order".order_date > ('{d1}')
                        ;""")
        orders = c.fetchall()
        con.commit()
        orders = orders[0][0]
        if orders == None:
            orders = 0
        orders -= order_past
        order_past += orders
        timenow -= time
        week_value.append(orders)
        true_week_number += 1
    return week_value, date


def month_sale():
    month = []
    month_value = []
    for x in range(0, 180, 30):
        d = datetime.now() - timedelta(days=x)
        month.append(d.strftime("%m-%Y"))
    #month_worth = db.session.query(db.func.sum(Order.total)).group_by(db.func.strftime("%Y-%m", Order.order_date)).order_by(desc(Order.order_date)).all()
    c.execute(f"""
                SELECT SUM(total) 
                FROM "main"."order"
                GROUP BY strftime('%Y %m',order_date)
                ORDER BY order_date DESC
                ;""")
    orders = c.fetchall()
    con.commit()
    for y in orders:
        month_value.append(int(y[0]))
    return orders, month


def monthly_stock():
    month_st = []
    month_stock = []
    for x in range(0, 180, 30):
        d = datetime.now() - timedelta(days=x)
        month_st.append(d.strftime("%m-%Y"))
    #month_worth = db.session.query(db.func.sum(Stock.total)).group_by(db.func.strftime("%Y-%m", Stock.stock_date)).order_by(desc(Stock.stock_date)).all()
    c.execute(f"""
                    SELECT SUM(total) 
                    FROM stock
                    GROUP BY strftime('%Y %m',stock_date)
                    ORDER BY stock_date DESC
                    ;""")
    month_worth = c.fetchall()
    con.commit()
    for y in month_worth:
        month_stock.append(int(y[0]))
    return month_stock, month_st


def monthly_sale_provider(user):
    month_value = []
    month = []
    time = timedelta(days=30)
    timenow = datetime.now()
    stock_past = 0
    for x in range(30, 180, 30):
        d = datetime.now() - timedelta(days=x)
        month.append(d.strftime("%m-%Y"))
        if user == "Admin":
            #stock = db.session.query(db.func.sum(Stock.total)).filter(Stock.stock_date > (timenow - time)).scalar()
            c.execute(f"""
                                SELECT SUM(total) 
                                FROM stock
                                WHERE stock_date > ('{d}')
                                ;""")
            stock = c.fetchall()
            con.commit()
        else:
            #stock = db.session.query(db.func.sum(Stock.total)).filter_by(provider_company=str(user)).filter(Stock.stock_date > (timenow - time)).scalar()
            c.execute(f"""
                        SELECT SUM(total) 
                        FROM stock
                        WHERE stock_date > ('{d}')
                        AND provider_company = '{user}'
                        ;""")
            stock = c.fetchall()
            con.commit()
        stock = stock[0][0]
        if stock == None:
            stock = 0
        stock -= stock_past
        stock_past += stock
        timenow -= time
        month_value.append(stock)
    return month_value, month


def category_sale():
    category = ['Acessórios', 'CPU', 'Monitor', 'Notebook', 'Telemóvel']
    orders = Kart.query.all()
    sale_products = []
    ace = 0
    cpu = 0
    mon = 0
    note = 0
    tel = 0
    for x in orders:
        product_get = Product.query.filter_by(name=str(x.product)).first()

        category_get = product_get.category
        if category_get == 'Acessórios':
            ace += x.amount
        if category_get == 'CPU':
            cpu += x.amount
        if category_get == 'Monitor':
            mon += x.amount
        if category_get == 'Notebook':
            note += x.amount
        if category_get == 'Telemóvel':
            tel += x.amount
    category_value = [ace, cpu, mon, note, tel]
    return category_value, category


def top_seven():
    #top = db.session.query(Kart.product, db.func.sum(Kart.amount)).order_by(desc(db.func.sum(Kart.amount))).group_by(Kart.product).all()
    c.execute(f"""
                        SELECT product, SUM(amount) 
                        FROM kart
                        GROUP BY product
                        ORDER BY SUM(amount) DESC
                        ;""")
    top = c.fetchall()
    con.commit()
    return top[:7]


def notification():
    products = Product.query.all()
    product_ending = []
    for x in products:
        if x.amount < 6:
            product_ending.append(x)
    return product_ending


def provider_sell(user):
    list_provider = []
    if user == 'Admin':
        product = Product.query.all()
    else:
        product = Product.query.filter_by(provider=str(user)).all()
    for x in product:
        sold = sold_amount(x)
        sold_total = sold[1] + x.amount
        list_provider.append((x.name, sold_total))
    sorted_list = sorted(list_provider, key=lambda tup: tup[1], reverse=True)
    return sorted_list


def sold_amount(product):
    soldamount = db.session.query(Kart.product, db.func.sum(Kart.amount)).group_by(
        Kart.product).filter_by(product=str(product.name)).first()
    c.execute(f"""
                        SELECT product, SUM(amount) 
                        FROM kart
                        WHERE product = '{product.name}'
                        GROUP BY product
                        ;""")
    soldamount1 = c.fetchone()
    con.commit()
    print(soldamount)
    print(soldamount1)
    return soldamount


# >>>>>>> ADD FAKE DATA <<<<<<<<<<


def add_customers():
    for _ in range(20):
        namefake = fake.first_name()
        users = Users(
            login=namefake,
            name=namefake,
            surname=fake.last_name(),
            address=fake.street_address()
        )
        db.session.add(users)
    db.session.commit()


def add_stock_history():
    products = Product.query.all()
    completed_products = []
    while len(products) != len(completed_products):
        pick_product = random.choice(products)
        while pick_product.name in completed_products:
            pick_product = random.choice(products)
        amount_total = 0
        sold_qt = sold_amount(pick_product)
        while pick_product.name not in completed_products:
            date = fake.date_time_this_year()
            max_amount = sold_qt[0] + pick_product.amount
            available_amount = max_amount - amount_total
            if available_amount > 50:
                amount = random.randint(50, available_amount)
            else:
                amount = available_amount
            amount_total = amount_total + amount
            total = amount * pick_product.origin_price
            stock = Stock(
                product=pick_product.name,
                provider_company=pick_product.provider,
                total=total,
                amount=amount,
                stock_date=date)
            db.session.add(stock)
            if amount == available_amount:
                completed_products.append(pick_product.name)
    db.session.commit()


def add_orders():
    customer_word = 'Customer'
    customers = Users.query.filter_by(company='Customer').all()
    products = Product.query.all()
    for _ in range(500):
        kart_list = []
        total = 0
        customer = random.choice(customers)
        for _ in range(random.randint(1, 10)):
            pick_product = random.choice(products)
            kart = Kart(
                product=pick_product.name,
                amount=random.randint(1, 3),
                price=pick_product.price,
                provider=pick_product.provider
            )
            db.session.add(kart)
            total_kart = int(kart.amount) * int(kart.price)
            total += total_kart
            kart_list.append(kart)
        date = fake.date_time_this_year()
        order = Order(
            order_date=date,
            customer_id=customer.id,
            products=kart_list,
            total=total
        )
        db.session.add(order)
    db.session.commit()



#w = add_stock_history()
#x = add_customers()
#y = add_orders()


if __name__ == '__main__':
    app.run()

