import os
from flask import Flask, request, render_template, redirect, url_for, flash, session
import datetime
import psycopg2
import bcrypt

app = Flask(__name__)
app.secret_key = "mysecretkey"

# Configuración de conexión para PostgreSQL
conn_str = {
    "host": "dpg-crnlv5l6l47c73ai705g-a.oregon-postgres.render.com",
    "database": "fisi_tweet",
    "user": "root",
    "password": "ROCR5iWHfufiDIHTQPNohyXiWFlooPhX"
}

# Conexión a la base de datos PostgreSQL
try:
    mydb = psycopg2.connect(**conn_str)
    print("Conexión exitosa a la base de datos PostgreSQL")
except Exception as e:
    print(f"No se pudo conectar a la base de datos PostgreSQL: {e}")

@app.route('/')
def Index():
    publicaciones = consultarTodasPublicaciones()
    return render_template('index.html', publicaciones=publicaciones)

@app.route('/publicaciones/registro-publicacion')
def page_registro_publicacion():
    if 'logged_in' in session:
        return render_template('registro-publicacion.html')
    else:
        flash("Debe iniciar sesión para agregar una publicación.")
        return redirect(url_for('login_render'))

@app.route('/publicaciones/agregar-publicacion', methods=['POST'])
def agregar_publicacion():
    if 'logged_in' in session:
        if request.method == 'POST':
            try:
                fecha = str(datetime.datetime.now())
                idAlumno = session['usuario_id']
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
        return redirect(url_for('page_registro_publicacion'))
    else:
        flash("Debe iniciar sesión para agregar una publicación.")
        return redirect(url_for('login_render'))

@app.route('/autenticacion/registro-usuario')
def registro_usuario():
    return render_template('registro-usuario.html')

@app.route('/autenticacion/agregar-usuario', methods=['POST'])
def agregar_usuario():
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            correo = request.form['correo']
            codigo = request.form['codigo']
            password = request.form['password']

            # Hashing de la contraseña
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Almacenamos el hash como texto, decodificando de bytes a una cadena de texto
            cursor = mydb.cursor()
            query = "INSERT INTO alumnos (nombre, apellido, correo, codigo, contraseña) VALUES (%s, %s, %s, %s, %s)"
            values = (nombre, apellido, correo, codigo, hashed_password.decode('utf-8'))  # decode to store as text
            cursor.execute(query, values)
            mydb.commit()
            cursor.close()

            flash('Usuario agregado de manera correcta: {}'.format(nombre))
        
        except Exception as e:
            mydb.rollback()
            flash(f"Error al realizar el registro: {e}")
        
    return render_template('registro-usuario.html')

@app.route('/autenticacion/login-face')
def login_render():
    return render_template('loginFace.html')

@app.route('/autenticacion/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        codigo = request.form['codigo']
        password = request.form['password']  # Esto viene del formulario HTML

        cursor = mydb.cursor()
        query = "SELECT * FROM alumnos WHERE correo = %s AND codigo = %s"
        values = (correo, codigo)
        cursor.execute(query, values)
        alumno = cursor.fetchone()
        cursor.close()

        if alumno:
            hashed_password = alumno[4]  # Asegúrate de que 'contraseña' esté en la columna 5
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                fecha = str(datetime.datetime.now())

                try:
                    cursor = mydb.cursor()
                    idAlumno = alumno[0]

                    query = "INSERT INTO logs (idAlumno, fecha) VALUES (%s, %s)"
                    values = (idAlumno, fecha)
                    cursor.execute(query, values)
                    cursor.close()

                    session['logged_in'] = True
                    session['usuario_id'] = alumno[0]
                    session['nombre'] = alumno[1]
                    flash("Inicio de sesión exitoso!")
                    return redirect(url_for('dashboard'))
                except Exception as e:
                    flash(f"Error al registrar Log: {e}")
            else:
                flash("Contraseña incorrecta")
        else:
            flash("Error de autenticación")
            
    return render_template('loginFace.html')

@app.route('/autenticacion/logout', methods=['POST', 'GET'])
def logout():
    session.pop('logged_in', None)
    session.pop('usuario_id', None)
    session.pop('nombre', None)
    flash("Sesión cerrada correctamente.")
    return redirect(url_for('Index'))

@app.route('/autenticacion/dashboard')
def dashboard():
    if 'logged_in' in session:
        idAlumno = session['usuario_id']
        publicaciones = consultarPublicaciones(idAlumno=idAlumno)
        sesiones = consultarSesiones(idAlumno=idAlumno)

        # Recuperar información del perfil del usuario
        cursor = mydb.cursor()
        query = "SELECT nombre, apellido, correo FROM alumnos WHERE idAlumno = %s"
        cursor.execute(query, (idAlumno,))
        usuario = cursor.fetchone()
        cursor.close()

        return render_template('dashboard.html', publicaciones=publicaciones, sesiones=sesiones, usuario=usuario)
    else:
        flash("Debe iniciar sesión para acceder al dashboard.")
        return redirect(url_for('login_render'))

def consultarTodasPublicaciones():
    try:
        cursor = mydb.cursor()
        query = '''
            SELECT alumnos.nombre, alumnos.correo, publicaciones.contenido, publicaciones.fecha
            FROM alumnos
            JOIN publicaciones ON alumnos.idAlumno = publicaciones.idAlumno
            ORDER BY publicaciones.fecha DESC
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
