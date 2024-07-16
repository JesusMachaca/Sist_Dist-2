import os
from flask import Flask, request, render_template, redirect, url_for, flash, session
import datetime
import psycopg2
from psycopg2 import sql

app = Flask(__name__)

# SETTINGS
app.secret_key = "mysecretkey"

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
def index():
    publicaciones = consultar_todas_publicaciones()
    return render_template('index.html', publicaciones=publicaciones)

@app.route('/registro-publicacion')
def page_registro_publicacion():
    if 'usuario' in session:
        return render_template('registro-publicacion.html')
    else:
        flash("Debe iniciar sesión para acceder.")
        return redirect(url_for('login_render'))

@app.route('/agregar-publicacion', methods=['POST'])
def agregar_publicacion():
    if 'usuario' in session:
        if request.method == 'POST':
            try:
                fecha = str(datetime.datetime.now())
                id_alumno = session['usuario']['id']
                contenido = request.form['contenido']

                cursor = mydb.cursor()
                query = "INSERT INTO publicaciones (idAlumno, contenido, fecha) VALUES (%s, %s, %s)"
                values = (id_alumno, contenido, fecha)
                cursor.execute(query, values)
                mydb.commit()
                cursor.close()

                flash("Se ha registrado de manera correcta!")
            except Exception as e:
                flash(f"Error al realizar el registro: {e}")
        return redirect(url_for('page_registro_publicacion'))
    else:
        flash("Debe iniciar sesión para publicar.")
        return redirect(url_for('login_render'))

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
            session['usuario'] = {
                'id': alumno[0],
                'nombre': alumno[1],
                'apellido': alumno[2],
                'correo': alumno[3],
                'codigo': alumno[4]
            }
            flash("Inicio de sesión exitoso!")
            return redirect(url_for('dashboard'))
        else:
            flash("Error de autenticación")

    return render_template('loginFace.html')


@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash("Sesión cerrada exitosamente.")
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'usuario' in session:
        id_alumno = session['usuario']['id']
        publicaciones = consultar_publicaciones(id_alumno=id_alumno)
        sesiones = consultar_sesiones(id_alumno=id_alumno)
        return render_template('dashboard.html', alumno=session['usuario'], publicaciones=publicaciones, sesiones=sesiones)
    else:
        flash("Debe iniciar sesión para acceder al dashboard.")
        return redirect(url_for('login_render'))

def consultar_todas_publicaciones():
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

def consultar_publicaciones(id_alumno):
    try:
        cursor = mydb.cursor()
        query = '''
            SELECT contenido, fecha
            FROM publicaciones WHERE idAlumno = %s
        '''
        values = (id_alumno,)
        cursor.execute(query, values)
        resultados = cursor.fetchall()
        cursor.close()
        return resultados
    except Exception as e:
        flash(f"Error al consultar publicaciones: {e}")
        return None

def consultar_sesiones(id_alumno):
    try:
        cursor = mydb.cursor()
        query = '''
            SELECT idLog, fecha
            FROM logs WHERE idAlumno = %s
        '''
        values = (id_alumno,)
        cursor.execute(query, values)
        resultados = cursor.fetchall()
        cursor.close()
        return resultados
    except Exception as e:
        flash(f"Error al consultar sesiones: {e}")
        return None

def get_alumnos():
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
