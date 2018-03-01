from flask import (
    Flask,
    render_template,
    request, 
    redirect,
    flash,
    url_for)
from flask import session as session
import psycopg2
import random
import string
import os
from sqlalchemy import create_engine
from urllib2 import HTTPError
from sqlalchemy.orm import sessionmaker
from config import Config, Auth
from forms import LoginForm, SignUpForm
from flask_login import LoginManager, current_user
from flask_login import current_user, login_user, logout_user, login_required
from requests_oauthlib import OAuth2Session
from werkzeug.urls import url_parse
from database_setup import Restaurant, Base, MenuItem, User
import json
import psycopg2
DBURL = "postgresql://catalog:catalogpassword@localhost:5432/restaurantmenu"
engine = create_engine(DBURL)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
db_session = DBSession()
app = Flask(__name__)
app.secret_key = 'secret_key'
login = LoginManager(app)
login.login_view = 'login'
login.session_protection = "strong"
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


@app.route('/oauth2callback')
def callback():
    # Redirect user to home page if already logged in.
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('restaurants'))
    if 'error' in request.args:
        if request.args.get('error') == 'access_denied':
            flash('You denied access.')
            return
        flash('Error encountered')
        return
    if 'code' not in request.args and 'state' not in request.args:
        return redirect(url_for('login'))
    else:
        # Execution reaches here when user has
        # successfully authenticated our app.
        print 'my still session', session
        google = get_google_auth(state=session['oauth_state'])
        try:
            token = google.fetch_token(
                Auth.TOKEN_URI,
                client_secret=Auth.CLIENT_SECRET,
                authorization_response=request.url)
        except HTTPError:
            return 'HTTPError occurred.'
        google = get_google_auth(token=token)
        resp = google.get(Auth.USER_INFO)
        if resp.status_code == 200:
            user_data = resp.json()
            email = user_data['email']
            print 'my email', email
            user = db_session.query(User).filter_by(email=email).first()
            # print 'my google user', user.fetchall()
            if user is None:
                user = User()
                user.email = email
            user.username = user_data['name']
            print(token)
            user.tokens = json.dumps(token)
            user.avatar = user_data['picture']
            db_session.add(user)
            db_session.commit()
            login_user(user)
            return redirect(url_for('all_restaurants'))
        return 'Could not fetch your information.'


def get_google_auth(state=None, token=None):
    if token:
        return OAuth2Session(Auth.CLIENT_ID, token=token)
    if state:
        return OAuth2Session(
            Auth.CLIENT_ID,
            state=state,
            redirect_uri=Auth.REDIRECT_URI)
    oauth = OAuth2Session(
        Auth.CLIENT_ID,
        redirect_uri=Auth.REDIRECT_URI,
        scope=Auth.SCOPE)
    return oauth


@login.user_loader
def load_user(id):
    return db_session.query(User).get(int(id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('all_restaurants'))
    google = get_google_auth()
    auth_url, state = google.authorization_url(
        Auth.AUTH_URI, access_type='offline')
    session['oauth_state'] = state
    print 'my session', session
    return render_template('login.html', auth_url=auth_url)


@app.route('/logout')
def logout():
    # route for logging out
    logout_user()
    return redirect(url_for('all_restaurants'))


@app.route('/')
@app.route('/restaurants')
def all_restaurants():
    # route to view all restaurant, also the home page
    conn = psycopg2.connect(DBURL)
    c = conn.cursor()
    c.execute('SELECT * FROM Restaurant')
    restaurants = c.fetchall()
    c.close()
    conn.close()
    return render_template('restaurants.html', restaurants=restaurants)


@app.route('/restaurant/<int:restaurant_id>/json')
def restaurant_json(restaurant_id):
    # json endpoint for each restaurant
    restaurant = db_session.query(Restaurant).filter_by(
        id=restaurant_id).first()
    if not restaurant:
        return 'restuarant id {} does not exist'.format(restaurant_id)
    print 'restuarants', restaurant
    json_data = restaurant.serialize
    return json.dumps(json_data)


@app.route('/restaurant/new', methods=['GET', 'POST'])
@login_required
def new_restaurants():
    # route to add a new restaurant
    if request.method == 'POST':
        add_new_restaurant(request.form['newrestaurant'])
        flash('new restaurant added!')
        return redirect('/restaurants')
    return render_template('newRestaurant.html')


@app.route('/restaurant/<int:restaurant_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_restaurant(restaurant_id):
    # route to edit a restaurant data
    if request.method == 'POST':
        message = editrestaurant(restaurant_id, request.form['editrestaurant'])
        if message:
            return redirect(url_for('new_restaurants'))
        else:
            flash('restaurant has been edited!')
            return redirect('/restaurants')
    return render_template('editRestaurant.html', path=request.path)


@app.route('/restaurant/<int:restaurant_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_restaurant(restaurant_id):
    # route to delete a restuarant
    if request.method == 'POST':
        if request.form['submit'] == 'Yes':
            message = deleterestaurant(restaurant_id)
            if not message:
                flash('restaurant has been deleted!')
        return redirect('/restaurants')
    return render_template('deleteRestaurant.html')


@app.route('/restaurant/<int:restaurant_id>')
@app.route('/restaurant/<int:restaurant_id>/menu')
def show_menu(restaurant_id):
    # route to view all menus
    conn = psycopg2.connect(DBURL)
    c = conn.cursor()
    c.execute('SELECT * FROM menu_item where restaurant_id = {}'.format(
        restaurant_id))
    menu_items = c.fetchall()
    print menu_items
    c.close()
    conn.close()
    return render_template(
        'menu.html', items=menu_items, restaurant_id=restaurant_id)


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>')
def view_menu(restaurant_id, menu_id):
    # route to view a menu
    menu = db_session.query(MenuItem).filter_by(id=menu_id).first()
    menu = menu.serialize
    return render_template('view_menu.html', menu=menu,
                           menu_id=menu_id, restaurant_id=restaurant_id)


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/json')
def view_menu_json(restaurant_id, menu_id):
    # json endpoint for each menu
    menu = db_session.query(MenuItem).filter_by(id=menu_id).first()
    menu = menu.serialize
    if not menu:
        return 'restaurant id {} or menu id {} does not exist'.format(
            restaurant_id, menu_id)
    return json.dumps(menu)


@app.route('/restaurant/<int:restaurant_id>/menu/new', methods=['GET', 'POST'])
@login_required
def new_menu(restaurant_id):
    # route to add a restaurant
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        course = request.form['course']
        message = add_new_menu(
            restaurant_id, [name, price, course, description])
        if message:
            return redirect(url_for('new_restaurants'))
        flash('menu item has been added!')
        return redirect(url_for('show_menu', restaurant_id=restaurant_id))
    return render_template('newMenu.html', restaurant_id=restaurant_id)


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit',
           methods=['GET', 'POST'])
@login_required
def edit_menu(restaurant_id, menu_id):
    # route to edit a menu
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        course = request.form['course']
        message = editmenu(
            restaurant_id, menu_id, [name, price, course, description])
        if message:
            return redirect(url_for('new_restaurants'))
        else:
            flash('menu item has been added!')
            return redirect(url_for('show_menu', restaurant_id=restaurant_id))
    return render_template('editMenu.html', data={
        'restaurant_id': restaurant_id,
        'menu_id': menu_id})


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete',
           methods=['GET', 'POST'])
@login_required
def delete_menu(restaurant_id, menu_id):
    # route to delete a menu
    if request.method == 'POST':
        if request.form['submit'] == 'Yes':
            message = deletemenu(restaurant_id, menu_id)
            if not message:
                flash('Menu Item deleted!')
        return redirect(url_for('show_menu', restaurant_id=restaurant_id))
    return render_template('deleteMenu.html', path=request.path)


def add_new_restaurant(restaurant_name):
    # helper function to add a restaurant
    new_restaurant = Restaurant(
        name=restaurant_name, user_id=current_user.get_id())
    db_session.add(new_restaurant)
    db_session.commit()


def editrestaurant(restaurant_id, new_name):
    # helper function to edit a restaurant
    restaurant = db_session.query(Restaurant).filter_by(
        id=restaurant_id).first()
    if restaurant.user_id != current_user.get_id():
        flash('You are not authorized to edit this restaurant')
        return 'not authorized'
    restaurant.name = new_name
    db_session.add(restaurant)
    db_session.commit()
    return None


def deleterestaurant(restaurant_id):
    # helper function to delete a restaurant
    restaurant = db_session.query(Restaurant).filter_by(
        id=restaurant_id).first()
    if restaurant.user_id != current_user.get_id():
        flash('You are not authorized to delete this restaurant')
        return 'not authorized'
    db_session.delete(restaurant)
    db_session.commit()


def add_new_menu(restaurant_id, menu_name):
    # helper function to add a menu
    restaurant = db_session.query(Restaurant).filter_by(
        id=restaurant_id).first()
    user_id = restaurant.user_id
    if current_user.get_id() != user_id:
        flash('you are not authorized to create a menu for this restaurant')
        return 'not authorized'
    new_menu = MenuItem(name=menu_name[0], price=menu_name[1],
                        course=menu_name[2], description=menu_name[3],
                        restaurant_id=restaurant_id, user_id=user_id)
    print 'new_menu', new_menu.user_id
    db_session.add(new_menu)
    db_session.commit()


def editmenu(restaurant_id, menu_id, new_menu):
    # helper function to edit a menu
    restaurant = db_session.query(Restaurant).filter_by(
        id=restaurant_id).first()
    # menu creator id
    user_id = restaurant.user_id
    if current_user.get_id() != user_id:
        flash('You are not authorized to edit this menu')
        return 'Not authorized'
    menuitem = db_session.query(MenuItem).filter_by(
        id=menu_id).first()
    print 'MENU ITEM', menuitem
    menuitem.name = new_menu[0]
    menuitem.price = new_menu[1]
    menuitem.course = new_menu[2]
    menuitem.description = new_menu[3]
    db_session.add(menuitem)
    db_session.commit()


def deletemenu(restaurant_id, menu_id):
    # helper function to delete a menu
    restaurant = db_session.query(Restaurant).filter_by(
        id=restaurant_id).first()
    # menu creator id
    user_id = restaurant.user_id
    if current_user.get_id() != user_id:
        flash('You are not authorized to delete this menu')
        return 'Not authorized'
    menuitem = db_session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id, id=menu_id).one()
    db_session.delete(menuitem)
    db_session.commit()

if __name__ == "__main__":
    # app.secret_key = 'super_secret_key'
    app.debug = True
    app.config.from_object(Config)
    app.run(host='127.0.0.1', port=5000)
