from app import app
from flask import (render_template, request, redirect, url_for, session,
	flash, Blueprint, jsonify
	)

from app.models import User, ShippingInfo, Kart,ProductVariations

import gc

from flask_login import (current_user, login_user, logout_user, login_required
	)
from app.users.forms import (ShippingForm,RequestResetForm,ResetPasswordForm,
	CartForm)
from app import db, mail
from flask_mail import Message

users = Blueprint('users', __name__)

def ShippingPrice():
	'''
	calculate the price of shipping if items is greater than 5 shipping is 2500
	else 1200
	'''
	item_num = Kart.query.filter_by(id = Kart.id).count()
	shipping_price = 0
	#item_lists = Kart.query.filter_by(id=Kart.id)
	if item_num >= 1:
		shipping_price = 1200
	elif item_num >= 5:
		shipping_price = 2500
	else:
		pass
	return shipping_price

'''
cart variables
'''
#items_subtotal=0

def subtotals():
	items_subtotal = 0
	get_products = Kart.query.filter_by(subtotal = Kart.subtotal).all()
	for price in get_products:
		items_subtotal+=int(price.subtotal)
	return items_subtotal

@users.route('/cart/',methods = ["GET","POST"])
def cart():	
	count = Kart.query.filter_by(product_id =Kart.product_id).count()
	form = CartForm()
	# fetch cart data 
	cartlist = Kart.query.filter_by(user_id=Kart.user_id)
	shipping = ShippingInfo.query.all()
	variants = ProductVariations.query.filter_by(product_id = ProductVariations.product_id)
	price = ShippingPrice()
	items_subtotals = subtotals() 
	#for annoymous users
	if current_user.is_anonymous:
		flash('please login or register to be able to add a shipping address')			
		return render_template('users/cart.html', count= count, cartlist= cartlist,
	title = "Cart", form = form, price=price, variants = variants,items_subtotals=items_subtotals)
	
	#for authenticated users
	if current_user.is_authenticated:
		if current_user.shipping==[]:
			flash("please add a shipping address in your profile")
			return render_template('users/cart.html', count= count, cartlist= cartlist,
		title = "Cart", form = form,price=price, variants= variants)

	return render_template('users/cart.html', count= count, cartlist= cartlist,
	title = "Cart", form = form, price=price, variants=variants,items_subtotals=items_subtotals)

@users.route('/cart/update/<int:id>',methods = ["POST"])
def quantity_update(id):
	cart_item = Kart.query.get_or_404(id)
	quantity = request.form["quantity"]
	cart_item.quantity = quantity
	item_total = cart_item.product.product_price * int(quantity)
	cart_item.subtotal = item_total
	items_subtotal = subtotals()
	db.session.commit()		
	return jsonify({"result":"success", "item_total":item_total, "subtotal":items_subtotal})

@users.route('/cart/remove/<int:id>',methods = ["GET","POST"])
def remove_item(id):
	cart_item = Kart.query.get_or_404(id)
	db.session.delete(cart_item)
	db.session.commit()
	return redirect(url_for('users.cart'))


@users.route('/profile/')
def profile():
	count = Kart.query.filter_by(product_id =Kart.product_id).count()

	form = ShippingForm()
	shipping = ShippingInfo.query.all()
	if form.validate_on_submit():
		info = ShippingInfo(address1=form.address1.data,address2=form.address2.data,
		postcode=form.postcode.data,city=form.city.data,
		state=form.state.data,country=request.country.data)
		db.session.add(info)
		db.session.commit()
		flash('shipping information was submitted successfully')
		return redirect(url_for('users.profile'))
	return render_template('users/profile.html', title = "Account page",form=form,
	shipping = shipping, count=count)


def send_reset_email(user):
	token = user.get_reset_token()
	msg = Message('Password Reset Request', sender='noreply@demo.com',
	recipients=[user.email])
	msg.body = f'''To reset your password, visit the following link:
{ url_for('users.reset_token', token = token, _external =True) }
If you did not make this request simply ignore this request and no changes will be made.
'''
	mail.send(msg)


@users.route('/profile/reset_password/',methods = ["GET","POST"])
def reset_request():
	if current_user.is_authenticated:
		return redirect(url_for('home.homepage'))
	form = RequestResetForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		send_reset_email(user)
		flash('An email has been sent with instructions to reset you password','info')
		return redirect(url_for('auth.login'))
	return render_template('users/reset_request.html',title = 'Reset password',
	form = form)




@users.route('/profile/reset_password/<token>/',methods = ["GET","POST"])
def reset_token(token):
	if current_user.is_authenticated:
		return redirect(url_for('home.homepage'))
	user = User.verify_reset_token(token)
	if user is None:
		flash('That is an invalid or expired token', 'warning')
		return redirect(url_for('users.reset_request'))
	form = ResetPasswordForm()
	if form.validate_on_submit():
		user.password_hash = user.set_password(form.password.data)
		db.session.commit()
		flash('Your password has been successfully updated', 'success')
		return redirect(url_for('auth.login'))
	return render_template('users/change-password.html',title = 'Reset password',
	form = form)
