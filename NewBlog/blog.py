from ast import keyword
from re import U
from sqlite3 import Cursor
from wsgiref.util import request_uri
from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField, PasswordField, validators
from passlib.hash import md5_crypt
from passlib.hash import sha256_crypt 
from passlib.hash import sha512_crypt 
from functools import wraps



#--------------------------------------------------------------------
# Kullanici giris decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedIn' in session:
            return f(*args, **kwargs)
        else:
            flash('Izin Gerekmektedir', 'danger')
            return redirect(url_for('login'))
    return decorated_function


#--------------------------------------------------------------------
#Register Form
class RegisterForm(Form):
    name = StringField('Name Surname', validators= [validators.Length(min = 4, max = 20)])
    username = StringField('Kullanici Adi', validators= [validators.Length(min = 5, max = 20)])
    email = StringField('Email', validators= [validators.Email(message= 'Email adresi gecersizdir')])
    password = PasswordField('Parola', validators= [
        validators.DataRequired(message = 'Lutfen bir parola giriniz'),
        validators.Length(min = 6, message= "Parola en az 6 karakterden olusmalidir"),
        validators.EqualTo(fieldname = 'confirm', message= 'Parola uyusmuyor')
    ])
    confirm = PasswordField('Parola Dogrula')



#--------------------------------------------------------------------
#Login Form
class LoginForm(Form):
    username = StringField('Kullanici Adi')
    password = PasswordField('Parola')


app = Flask(__name__)
app.secret_key = 'MyBlog'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'myblog'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


@app.route('/')
def index():
    return render_template('index.html')



#------------------------------------------------------------------------------------------------
#register
@app.route('/register', methods =['GET', "POST"])
def register():
    form = RegisterForm(request.form)


    if request.method == 'POST' and form.validate():

        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        cursor = mysql.connection.cursor()
        query = 'Insert into users (name, email, username, password) values(%s,%s,%s,%s)'
        cursor.execute(query, (name, email, username, password))

        mysql.connection.commit()
        cursor.close()
        flash('Basariyla kayit oldunuz', 'success')

        return redirect(url_for('login'))


    else: 
        return render_template('register.html', form = form)



#----------------------------------------------------------------------------------------------------------------------------
#Login
@app.route('/login', methods = ['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST':
        username = form.username.data
        enteredPassword = form.password.data

        cursor = mysql.connection.cursor()
        query = 'Select * from users where username = %s'
        result = cursor.execute(query, (username,))
        if result > 0:
            data = cursor.fetchone()
            realPassword = data['password']
            if sha256_crypt.verify(enteredPassword,realPassword): 
                flash('Hos geldiniz', 'success')

                session['loggedIn'] = True
                session['username'] = username

                return redirect(url_for('index'))
                
            else:
                flash('Yanlis parola', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Kullanici kayitli degil', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html', form = form)



#----------------------------------------------------------------------------------------------------------------------------
#Logout
@app.route('/logout')

def logout():
    session.clear()
    return redirect(url_for('index'))



#----------------------------------------------------------------------------------------------------------------------------
#Dashboard
@app.route('/dashboard')
@login_required

def dashboard():
    cursor = mysql.connection.cursor()
    query = 'Select * from articles where author = %s'
    result = cursor.execute(query, (session['username'], ))

    if result > 0:
        articles = cursor.fetchall()
        return render_template('dashboard.html', articles = articles)
    else:

        return render_template('dashboard.html') 



#----------------------------------------------------------------------------------------------------------------------------
#Makale Sayfasi
@app.route('/articles')
def articles():
    cursor = mysql.connection.cursor()
    query = 'Select * from articles'

    result = cursor.execute(query)

    if result > 0:
        articles = cursor.fetchall()

        return render_template('articles.html', articles = articles)

    else:
        return render_template('articles.html')

#----------------------------------------------------------------------------------------------------------------------------
#Makale ekleme
@app.route('/addArticle', methods = ['GET', "POST"])
def addArticle():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()

        query = 'Insert into articles(title, author, content) values(%s, %s, %s)'

        cursor.execute(query, (title, session['username'], content))

        mysql.connection.commit()
        cursor.close()

        flash('Makale basariyla eklendi', 'success')
        return redirect(url_for('dashboard'))
    else:
        return render_template('addArticle.html', form = form)



#----------------------------------------------------------------------------------------------------------------------------
#Makale formu
class ArticleForm(Form):
    title = StringField('Makale Basligi', validators=[validators.length(min = 5, max = 100)])
    content = TextAreaField('Content', validators=[validators.length(min = 10)])



#----------------------------------------------------------------------------------------------------------------------------
#Makale okuma formu
@app.route('/article/<string:id>')

def article(id):
    cursor = mysql.connection.cursor()
    query = 'Select * from articles where id = %s'

    result = cursor.execute(query, (id, ))

    if result > 0:
        article = cursor.fetchone()
        return render_template('article.html', article = article)

    else:
        return render_template('article.html')



#----------------------------------------------------------------------------------------------------------------------------
#Makale Silme formu
@app.route('/delete/<string:id>')
@login_required
def delete(id):
    cursor = mysql.connection.cursor()

    query = 'Select * from articles where author = %s and id = %s'

    result = cursor.execute(query, (session['username'], id))

    if result > 0:
        query2 = 'Delete from articles where id = %s'
        cursor.execute(query2, (id, ))
        mysql.connection.commit()
        flash('Silme islemi tamamlandi', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Makale veya Yetkiniz bulunmuyor', 'danger')
        return redirect(url_for('index'))



#----------------------------------------------------------------------------------------------------------------------------
#Makale Guncelleme
@app.route('/edit/<string:id>', methods = ['GET', 'POST'])
@login_required
def update(id):
    if request.method == 'GET':
        cursor = mysql.connection.cursor()

        query = 'Select * from articles where id = %s and author = %s'
        result = cursor.execute(query, (id, session['username']))

        if result == 0:
            flash('Makale veya Yetkiniz bulunmuyor', 'danger')   
            return redirect(url_for('index'))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article['title']
            form.content.data = article['content']
            return render_template('update.html', form = form)

    else:
        
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        cursor = mysql.connection.cursor()
        query2 = 'Update articles Set title = %s , content = %s where id = %s'
        cursor.execute(query2, (newTitle, newContent, id))
        mysql.connection.commit()
        flash('Makale basariyla guncellendi', 'success')
        return redirect(url_for('dashboard'))
#----------------------------------------------------------------------------------------------------------------------------


#Makale arama

@app.route('/search', methods = ['GET','POST'])

def search():
    if request.method == 'GET':
        return redirect(url_for('index'))
    else:
        keyword = request.form.get('keyword')
        cursor = mysql.connection.cursor()
        query = 'Select * from articles where title like "%'+ keyword + '%"'
        result = cursor.execute(query)

        if result == 0:
            flash('Aranan makale bulunamadi', 'danger')
            return redirect(url_for('articles'))

        else:
            articles = cursor.fetchall()
            return render_template('articles.html', articles = articles)
            


if __name__ == '__main__':
    app.run(debug = True)

