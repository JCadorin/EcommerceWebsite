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
# Cursor
c = con.cursor()




# CLASS Users
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
    
    # Relationship to save orders made by users
    orders = db.relationship('Order', backref='users')


# Table to link the kart with the order after the purchase
order_kart = db.Table('order_kart',
    db.Column('order_id', db.Integer, db.ForeignKey('order.id')),
    db.Column('kart_serial', db.Integer, db.ForeignKey('kart.serial'))
)


# CLASS Product
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


# CLASS Kart
class Kart(db.Model):
    __tablename__ = "kart"
    serial = db.Column(db.Integer, primary_key=True)
    client = db.Column(db.String(50))
    product = db.Column(db.String(50))
    amount = db.Column(db.Integer)
    price = db.Column(db.Integer)
    provider = db.Column(db.String(50))


# CLASS Orders
class Order(db.Model):
    __tablename__ = "order"
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.company'), nullable=False)
    total = db.Column(db.Integer)

    products = db.relationship('Kart', secondary=order_kart)


# CLASS Stock
class Stock(db.Model):
    __tablename__ = "stock"
    id = db.Column(db.Integer, primary_key=True)
    stock_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    provider_company = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total = db.Column(db.Integer)
    amount = db.Column(db.Integer)
    product = db.Column(db.String(50))


db.create_all()  # Table creation
db.session.commit()  # Execution of all the pending task on database 


# Dictionary of each login access by level
database_customer = {'Bill': '9876', 'Cris': '1111'}
database_provider = {'Provider1': '1010', 'Provider2': '2020', 'Provider3': '3030', 'Provider4': '4040'}
database_administrator = {'Jeff': '1234'}



# Initial Route
@app.route('/')
def initial():
    return render_template("login.html")


# Login Route
@app.route('/form_login', methods=['POST', 'GET'])
def login():
    global name1
    # Username variable to acess user information after login
    name1 = request.form['username']
    pwd = request.form['password']
    # Customer access
    if name1 in database_customer:
        if database_customer[name1] != pwd:
            return render_template('login.html', info='Wrong Password')
        else:
            return redirect(url_for('customer'))
    # Provider access
    if name1 in database_provider:
        if database_provider[name1] != pwd:
            return render_template('login.html', info='Wrong Password')
        else:
            return redirect(url_for('provider'))
    # Administrator access
    if name1 in database_administrator:
        if database_administrator[name1] != pwd:
            return render_template('login.html', info='Wrong Password')
        else:
            return redirect(url_for('useradmin'))
    else:
        return render_template('login.html', info='User Not Found')


# Administrator Route
@app.route('/useradmin')
def useradmin():
    if name1 in database_administrator:
        # Querying all products
        products = Product.query.all()
        product = Product.query.first()
        # Getting weekly sales and the correspoding date
        week_value, date = weekly_sale()
        # Getting monthly sales and the correspoding date
        month_value, month = month_sale()
        # Getting daily sales and the correspoding date
        day_value, day = daily_sale()
        # Getting product sale count by category
        category_value, category = category_sale()
        # Getting top seven products sale
        top = top_seven()
        # Getting any products with amount avaliable close to end
        product_ending = notification()
        # Querying the sold amount of each product
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
        # Monthly stock injected in the inventory
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

    
# Product Painel Route
@app.route('/product_painel')
def product_painel():
    products = Product.query.all()
    return render_template('product_painel.html', nome_utilizador=name1, products=products)


# Sales Route 
@app.route('/sales')
def sales():
    orders = Order.query.order_by(desc(Order.order_date)).all()
    return render_template('sales.html', nome_utilizador=name1, orders=orders)


# Provider Route
@app.route('/provider', methods=['POST', 'GET'])
def provider():
    user = Users.query.filter_by(login=name1).first()
    # Checking if the access request comes from the administrator or any provider
    if user.company == "Admin":
        # Querying all products
        products = Product.query.all()
        kart = Kart.query.all()
        #  Function getting sell History of each product
        sell = provider_sell(user.company)
        # Product amount avaliable in stock
        stock = db.session.query(Stock).all()
        # Monthly sell value variable with corresponding date
        month_value, month = monthly_sale_provider(user.company)
        return render_template('provider.html', user=user, kart=kart, products=products, sell=sell, stock=stock,
                               month_value=json.dumps(month_value), month=json.dumps(month))
    else:
        # Querying products that belongs to provider's company
        user = Users.query.filter_by(login=name1).first()
        products = Product.query.filter_by(provider=str(user.company)).all()
        kart = Kart.query.all()
        # Function getting sell History of each product
        sell = provider_sell(user.company)
        # Product amount avaliable in stock
        stock = db.session.query(Stock).filter_by(provider_company=str(user.company)).all()
        # Monthly sell value variable with corresponding date
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
    # Checking from who the request access came
    if user.company == "Admin":
        # Querying stock history
        c.execute(f"""
                SELECT *
                FROM stock
                ORDER BY stock.stock_date DESC;""")
        query = c.fetchall()
        con.commit()
    else:
        # Querying stock history
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


# Customer Route
@app.route('/customer', methods=['POST', 'GET'])
def customer():
    user = Users.query.filter_by(login=name1).first()
    products = Product.query.all()
    kart = Kart.query.filter_by(client=name1)
    return render_template('customer.html', user=user, kart=kart, products=products)


@app.route('/purchase', methods=['POST', 'GET'])
def purchase():
    user = Users.query.filter_by(login=name1).first()
    # Querying order history
    orders = Order.query.filter_by(customer_id=int(user.id)).order_by(desc(Order.order_date)).all()
    return render_template('purchase.html', nome_utilizador=name1, orders=orders)


# Product Update Route
@app.route('/update_product', methods=['POST'])
def update_product():
    # getting information about the value we want to change
    pk = request.form['pk']
    name = request.form['name']
    value = request.form['value']
    # getting the product
    item = Product.query.filter_by(id=int(pk)).first()
    # updating the chosen product
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


# Add Product Route
@app.route('/add_product', methods=['POST'])
def add_product():
    new_product = Product(name=request.form['product_name'], description=request.form['product_description'],
                          category=request.form['product_category'], amount=request.form['product_amount'],
                          price=request.form['product_price'], image=request.form['product_image'], provider=request.form['provider'])
    db.session.add(new_product)
    db.session.commit()
    return redirect(request.referrer)


# Add Stock Route
@app.route('/add_stock', methods=['POST'])
def add_stock():
    # Getting the product we want to update
    name = request.form['product_name']
    # Getting the amount we want to add
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


# Delete Product Route
@app.route('/delete_product/<id>')
def delete_product(id):
    item = Product.query.filter_by(id=int(id)).delete()
    db.session.commit()
    return redirect(request.referrer)


# Add Item to kart Route
@app.route('/add_item', methods=['POST'])
def add_item():
    try:
        # Creating a new item to kart
        kart_item = Kart(product=request.form['product_name'], client=request.form['customer_name'],
                         amount=request.form['amount_kart'], price=request.form['product_price'],
                         provider=request.form['product_provider'])
        db.session.add(kart_item)  
        db.session.commit()  
        return redirect(request.referrer)
    except Exception as e:
        print(e)
    finally:
        return redirect(request.referrer)


# Delete Item from Kart Route
@app.route('/delete_item/<serial>')
def delete(serial):
    item = Kart.query.filter_by(serial=int(serial)).delete()
    db.session.commit()
    return redirect(request.referrer)


# Check Out Route
@app.route('/checkout', methods=['POST'])
def checkout():
    # Getting information from customer's kart
    customers = request.form['customer']
    item = Kart.query.filter_by(client=str(customers)).all()
    client = Users.query.filter_by(name=str(customers)).first()
    # List for kart's product
    item_list = []
    # Total purchase value variable
    total = 0
    # Loop in each product of the kart
    for i in item:
        # getting serial number
        serial = i.serial
        # getting product name
        item_product = Product.query.filter_by(name=str(i.product)).first()
        #getting the product inside kart database
        kart_product = Kart.query.filter_by(serial=int(serial)).first()
        # calculating price of each product times the amount
        price_total = kart_product.price*kart_product.amount
        #adding the price to the total
        total += price_total
        # reducing the stock
        item_product.amount = item_product.amount - i.amount
        # taking off the product from the kart and adding to the sold list by cleaning the client name register
        kart_product.client = ""
        item_list.append(kart_product)
    # Saving the kart in the order history
    order = Order(customer_id=client.id, products=item_list, total=total)
    db.session.add(order)
    db.session.commit()
    return redirect(request.referrer)


# >>>>>>>> End Route <<<<<<<<<<<<

# Daily Sale Function to get the total of sales by each day
def daily_sale():
    # List of total sale of each day
    day_value = []
    # List of days
    day = []
    # timedelta variable to get the conventional date setup
    time = timedelta(days=1)
    # getting the actual date to use
    timenow = datetime.now()
    # variable of order past to subtract 
    order_past = 0
    # looping 15 times to get the order of the past 15 days
    for x in range(15):
        # Variables subtracting the actual date from the loop number (d1 to avoid the 0 index problem)
        d = datetime.now() - timedelta(days=x)
        d1 = datetime.now() - timedelta(days=(x-1))
        # saving the variable in a visualization setup date
        day.append(d.strftime("%d-%m-%Y"))
        # querying all orders from the past x days established by the loop range
        c.execute(f"""
                SELECT SUM(total) 
                FROM "main"."order"
                WHERE "main"."order".order_date > ('{d1}')
                ;""")
        orders = c.fetchall()
        con.commit()
        # getting just the number from the list of the sql query
        orders = orders[0][0]
        # giving to the 'orders' a neutral number if the variable is empty
        if orders is None:
            orders = 0
        # subtracting the total orders by the previous one just the total of selected day
        orders -= order_past
        # adding the value to the total to use for the next day value
        order_past += orders
        # subtracting the date for the next loop
        timenow -= time
        # adding to the list of the order values
        day_value.append(orders)
    return day_value, day


def weekly_sale():
    # List of total sale of each week
    week_value = []
    # List of weeks
    date = []
    # timedelta variable to get the conventional date setup
    time = timedelta(weeks=1)
    # getting the actual date to use
    timenow = datetime.now()
    # variable of order past to subtract
    order_past = 0
    # variable of the week number to use in d1 (avoiding the 0 index problem)
    true_week_number = 0
    #loop in a 12 range
    for x in range(12):
        # Variables subtracting the actual date from the loop number (d1 to avoid the 0 index problem)
        d = datetime.now() - timedelta(weeks=x)
        d1 = datetime.now() - timedelta(weeks=true_week_number)
        # saving the variable in a visualization setup date in the date list
        date.append(d.strftime("%d-%m-%Y"))
        # querying all orders from the past x weeks established by the loop range
        c.execute(f"""
                        SELECT SUM(total) 
                        FROM "main"."order"
                        WHERE "main"."order".order_date > ('{d1}')
                        ;""")
        orders = c.fetchall()
        con.commit()
        # getting just the number from the list of the sql query
        orders = orders[0][0]
        # giving to the 'orders' a neutral number if the variable is empty
        if orders == None:
            orders = 0
        # subtracting the total orders by the previous one just the total of selected week
        orders -= order_past
        # adding the value to the total to use for the next week value
        order_past += orders
        # subtracting the date for the next loop
        timenow -= time
        # adding to the list of the order values
        week_value.append(orders)
        # increasing the variable of week count
        true_week_number += 1
    return week_value, date


def month_sale():
    # List of month
    month = []
    # List of total sale of each month
    month_value = []
    # loop in the last 6 month, jumping each 30 days
    for x in range(0, 180, 30):
        # getting the period for each loop
        d = datetime.now() - timedelta(days=x)
        # adding the date with a visualition setup in the month list
        month.append(d.strftime("%m-%Y"))
    # querying all orders from the past x months established by the loop range
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
    # list of stock added by month
    month_stock = []
    # looping in the last 6 month, jumping 30 days each
    for x in range(0, 180, 30):
        # getting the date period by subtracting the timedelta using the range of the loop by the current date time
        d = datetime.now() - timedelta(days=x)
        # adding the date with a visualition setup in the month list
        month_st.append(d.strftime("%m-%Y"))
    # Querying the value from the stock added by the date period
    c.execute(f"""
                    SELECT SUM(total) 
                    FROM stock
                    GROUP BY strftime('%Y %m',stock_date)
                    ORDER BY stock_date DESC
                    ;""")
    
    month_worth = c.fetchall()
    con.commit()
    # looping in each product gotten by the query, and adding to the month list
    for y in month_worth:
        month_stock.append(int(y[0]))
    return month_stock, month_st


def monthly_sale_provider(user):
    month_value = []
    month = []
    # time delta variable 
    time = timedelta(days=30)
    #current time variable
    timenow = datetime.now()
    # variable to subtract previously value to get the correct period value
    stock_past = 0
    # loop in the past 6 month, 30 days jumping
    for x in range(30, 180, 30):
        # getting the period of the loop
        d = datetime.now() - timedelta(days=x)
        # adding the date in the conventional setup
        month.append(d.strftime("%m-%Y"))
        # checking the access to filter products
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
        # add neutral value to the variable
        if stock == None:
            stock = 0
        # substracting previously stock value
        stock -= stock_past
        # adding the stock past value to adjust next month value
        stock_past += stock
        # regressing the timenow variable to follow the loop 
        timenow -= time
        month_value.append(stock)
    return month_value, month


# Function to get the sale amount by category
def category_sale():
    # List with categories
    category = ['Acessórios', 'CPU', 'Monitor', 'Notebook', 'Telemóvel']
    # Querying all the sold products
    orders = Kart.query.all()
    # 
    sale_products = []
    # variable for each category
    ace = 0
    cpu = 0
    mon = 0
    note = 0
    tel = 0
    #loop in all purchases
    for x in orders:
        # getting the product information
        product_get = Product.query.filter_by(name=str(x.product)).first()
        # finding the product's category
        category_get = product_get.category
        # adding the count to the respective category
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
    #querying the seven best seller products
    c.execute(f"""
                        SELECT product, SUM(amount) 
                        FROM kart
                        GROUP BY product
                        ORDER BY SUM(amount) DESC
                        ;""")
    top = c.fetchall()
    con.commit()
    return top[:7]


# Notification function to alert what product have the amount close to the end
def notification():
    products = Product.query.all()
    product_ending = []
    # looping all products and add to the list all the products with amount 5 or less
    for x in products:
        if x.amount < 6:
            product_ending.append(x)
    return product_ending


def provider_sell(user):
    # Empty list to add each product and the total amount (avaliable in stock and sold)
    list_provider = []
    # Checking access
    if user == 'Admin':
        product = Product.query.all()
    else:
        product = Product.query.filter_by(provider=str(user)).all()
    #Looping in each product queried
    for x in product:
        # getting sold amount
        sold = sold_amount(x)
        # sold amount more amount avaliable in stock
        sold_total = sold[1] + x.amount
        # adding information to the list
        list_provider.append((x.name, sold_total))
    # return ordered list
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

# Function to add fake customers to our database
def add_customers():
    # looping to create 20 new register at once
    for _ in range(20):
        #fake function to create fictional person information
        namefake = fake.first_name()
        users = Users(
            login=namefake,
            name=namefake,
            surname=fake.last_name(),
            address=fake.street_address()
        )
        db.session.add(users)
    db.session.commit()


# Add Ficitonal Stocking history Function    
def add_stock_history():
    products = Product.query.all()
    # variable to pull apart the products with enough quantity
    completed_products = []
    # loop till get all products amount completed
    while len(products) != len(completed_products):
        # pick random product
        pick_product = random.choice(products)
        # looping till find a product not already completed
        while pick_product.name in completed_products:
            pick_product = random.choice(products)
        # total variable
        amount_total = 0
        # product total registered in database 
        sold_qt = sold_amount(pick_product)
        # loop the product till complete it
        while pick_product.name not in completed_products:
            # creating random date
            date = fake.date_time_this_year()
            # not already used amount variable
            max_amount = sold_qt[0] + pick_product.amount
            # finding the avaliable amount after this loop
            available_amount = max_amount - amount_total
            # lowing the random range after reach less than 50 unregistered product amount
            if available_amount > 50:
                amount = random.randint(50, available_amount)
            else:
                amount = available_amount
            # updating the total amount variable    
            amount_total = amount_total + amount
            # calculating total price
            total = amount * pick_product.origin_price
            # registering the operation in the stock history
            stock = Stock(
                product=pick_product.name,
                provider_company=pick_product.provider,
                total=total,
                amount=amount,
                stock_date=date)
            db.session.add(stock)
            # adding the product to the completed product list if it reach the total avaliable in the system
            if amount == available_amount:
                completed_products.append(pick_product.name)
    db.session.commit()


# Add orders function to create fictional order data    
def add_orders():
    # 
    customer_word = 'Customer'
    # Getting all the avaliable customers in the database, excluding the providers
    customers = Users.query.filter_by(company='Customer').all()
    # Gettin all products
    products = Product.query.all()
    # Loop to create x orders at once
    for _ in range(500):
        # creating kart list
        kart_list = []
        # total purchase value
        total = 0
        # choosing random customer
        customer = random.choice(customers)
        # looping in a random range to create the kart product amount
        for _ in range(random.randint(1, 10)):
            # chossing a random product
            pick_product = random.choice(products)
            # registering the product choice in the kart database
            kart = Kart(
                product=pick_product.name,
                amount=random.randint(1, 3),
                price=pick_product.price,
                provider=pick_product.provider
            )
            db.session.add(kart)
            # calculating total value
            total_kart = int(kart.amount) * int(kart.price)
            total += total_kart
            kart_list.append(kart)
        # creating fake purchase date
        date = fake.date_time_this_year()
        # registering the order
        order = Order(
            order_date=date,
            customer_id=customer.id,
            products=kart_list,
            total=total
        )
        db.session.add(order)
    db.session.commit()


# Functions used once to create fictional data
#w = add_stock_history()
#x = add_customers()
#y = add_orders()


if __name__ == '__main__':
    app.run()

