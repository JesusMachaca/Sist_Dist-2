import os
from flask import Flask, request, render_template, redirect, url_for, flash, session
from flask_session import Session
import datetime
import psycopg2
from psycopg2 import sql

app = Flask(__name__)

# SETTINGS
app.secret_key = "mysecretkey"

# Configuración de la sesión
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Configuración de la conexión para PostgreSQL
conn_str = {
    "host": "dpg-cqarlkuehbks73de8dlg-a.oregon-postgres.render.com",
    "database": "bdfisitweet",
    "user": "grupo_app",
    "password": "4fPiWKsmtrNfCeHEEo2jBVIP7jvLGAn3"
}

# Conectar a la base de datos PostgreSQL
try:
    mydb = psycopg2.connect(**conn_str)
    print("Conexión exitosa a la base de datos PostgreSQL")
except Exception as e:
    print(f"No se pudo conectar a la base de datos PostgreSQL: {e}")

@app.route('/')
def Index():
    publicaciones = consultarTodasPublicaciones()
    return render_template('index.html', publicaciones=publicaciones)

@app.route('/registro-publicacion')
def page_registro_publicacion():
    return render_template('registro-publicacion.html')

@app.route('/agregar-publicacion', methods=['POST'])
def agregar_publicacion():
    if 'alumno' in session:
        try:
            fecha = str(datetime.datetime.now())
            idAlumno = session['alumno'][0]
            contenido = request.form['contenido']

            cursor = mydb.cursor()
            query = "INSERT INTO publicaciones (idAlumno, contenido, fecha) VALUES (%s, %s, %s)"
            values = (idAlumno, contenido, fecha)
            cursor.execute(query, values)
            mydb.commit()
            cursor.close()

            flash("Se ha registrado de manera correcta!")
        except Exception as e:
            flash(f"Error al realizar el registro: {e}")
            return render_template('registro-publicacion.html')
    else:
        flash("Debes iniciar sesión para agregar una publicación")

    return render_template('registro-publicacion.html')

@app.route('/registro-usuario')
def registro_usuario():
    return render_template('registro-usuario.html')

@app.route('/agregar-usuario', methods=['POST'])
def agregar_usuario():
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            correo = request.form['correo']
            codigo = request.form['codigo']

            cursor = mydb.cursor()
            query = "INSERT INTO alumnos (nombre, apellido, correo, codigo) VALUES (%s, %s, %s, %s)"
            values = (nombre, apellido, correo, codigo)
            cursor.execute(query, values)
            mydb.commit()
            cursor.close()

            flash('Usuario agregado de manera correcta: {}'.format(nombre))
        except Exception as e:
            flash("Error al realizar el registro: {}".format(e))
            return render_template('registro-usuario.html')

    return render_template('registro-usuario.html')

@app.route('/login-face')
def login_render():
    return render_template('loginFace.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        codigo = request.form['codigo']
        cursor = mydb.cursor()
        query = "SELECT * FROM alumnos WHERE correo = %s AND codigo = %s"
        values = (correo, codigo)
        cursor.execute(query, values)
        alumno = cursor.fetchone()
        cursor.close()

        if alumno:
            fecha = str(datetime.datetime.now())
            
            try:
                cursor = mydb.cursor()
                idAlumno = alumno[0]

                query = "INSERT INTO logs (idAlumno, fecha) VALUES (%s, %s)"
                values = (idAlumno, fecha)
                cursor.execute(query, values)
                mydb.commit()
                cursor.close()

                session['logged_in'] = True
                session['alumno'] = alumno
                return redirect(url_for('dashboard'))
            except Exception as e:
                flash(f"Error al registrar Log: {e}")
        else:
            flash("Error de autenticación")

    return render_template('loginFace.html')

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.pop('logged_in', None)
    session.pop('alumno', None)
    return redirect(url_for('Index'))

@app.route('/dashboard')
def dashboard():
    if 'alumno' in session:
        idAlumno = session['alumno'][0]
        publicaciones = consultarPublicaciones(idAlumno=idAlumno)
        sesiones = consultarSesiones(idAlumno=idAlumno)
        return render_template('dashboard.html', alumno=session['alumno'], publicaciones=publicaciones, sesiones=sesiones)
    else:
        flash("Debes iniciar sesión para ver el dashboard")
        return redirect(url_for('login_render'))

def consultarTodasPublicaciones():
    try:
        cursor = mydb.cursor()
        query = '''
            SELECT alumnos.nombre, alumnos.correo, publicaciones.contenido, publicaciones.fecha
            FROM alumnos
            JOIN publicaciones ON alumnos.idAlumno = publicaciones.idAlumno
        '''
        cursor.execute(query)
        resultados = cursor.fetchall()
        cursor.close()
        return resultados
    except Exception as e:
        flash(f"Error al consultar publicaciones: {e}")
        return None

def consultarPublicaciones(idAlumno):
    try:
        cursor = mydb.cursor()
        query = '''
            SELECT contenido, fecha
            FROM publicaciones WHERE idAlumno = %s
        '''
        values = (idAlumno,)
        cursor.execute(query, values)
        resultados = cursor.fetchall()
        cursor.close()
        return resultados
    except Exception as e:
        flash(f"Error al consultar publicaciones: {e}")
        return None

def consultarSesiones(idAlumno):
    try:
        cursor = mydb.cursor()
        query = '''
            SELECT idLog, fecha
            FROM logs WHERE idAlumno = %s
        '''
        values = (idAlumno,)
        cursor.execute(query, values)
        resultados = cursor.fetchall()
        cursor.close()
        return resultados
    except Exception as e:
        flash(f"Error al consultar sesiones: {e}")
        return None

def getAlumnos():
    try:
        cursor = mydb.cursor()
        cursor.execute("SELECT idAlumno, nombre, apellido, correo, codigo, imagen, imagenEncoding FROM alumnos")
        alumnos = cursor.fetchall()
        cursor.close()
        return alumnos
    except Exception as e:
        flash(f"Error al consultar alumnos: {e}")
        return None

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
