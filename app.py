import os
from flask import Flask, request, render_template, redirect, url_for, flash, session
import datetime
import psycopg2
import bcrypt

app = Flask(__name__)
app.secret_key = "mysecretkey"

# Configuración de conexión para PostgreSQL
conn_str = {
    "host": "dpg-csjdsrpu0jms73b160tg-a.oregon-postgres.render.com",
    "database": "fisi_tweet_xoja",
    "user": "fisi_tweet",
    "password": "pOQvJ4ROVEDplJpTRw3aOUH9exSMDNce"
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
                mydb.rollback()  # Aseguramos que cualquier error haga un rollback
                flash(f"Error al realizar el registro: {e}")
        return redirect(url_for('page_registro_publicacion'))
    else:
        flash("Debe iniciar sesión para agregar una publicación.")
        return redirect(url_for('login_render'))

@app.route('/mensajes/enviar', methods=['GET', 'POST'])
def enviar_mensaje():
    if 'logged_in' in session:
        if request.method == 'GET':
            # Si se hace un GET, obtén todos los usuarios y retorna la página para enviar mensajes
            usuarios = consultarUsuarios()  # Función para obtener usuarios
            return render_template('dashboard.html', usuarios=usuarios)  # Renderiza el mismo dashboard
        elif request.method == 'POST':
            # Lógica para enviar el mensaje
            emisor_id = session['usuario_id']  # ID del usuario emisor
            correo_receptor = request.form.get('correo_receptor')  # Correo del usuario receptor
            contenido = request.form.get('contenido')  # Contenido del mensaje

            try:
                # Busca el ID del receptor basado en el correo
                cursor = mydb.cursor()
                query_receptor = "SELECT idAlumno FROM alumnos WHERE correo = %s"
                cursor.execute(query_receptor, (correo_receptor,))
                receptor = cursor.fetchone()

                if receptor:
                    receptor_id = receptor[0]  # Extrae el ID del receptor

                    # Inserta el mensaje en la base de datos
                    query_mensaje = "INSERT INTO mensajes (idEmisor, idReceptor, contenido) VALUES (%s, %s, %s)"
                    cursor.execute(query_mensaje, (emisor_id, receptor_id, contenido))
                    mydb.commit()
                    cursor.close()

                    flash("Mensaje enviado correctamente!")
                    return redirect(url_for('dashboard'))  # Redirige al dashboard
                else:
                    cursor.close()
                    flash("El correo del receptor no existe.")
                    return redirect(url_for('dashboard'))
            except Exception as e:
                mydb.rollback()
                flash(f"Error al enviar el mensaje: {e}")
                return redirect(url_for('dashboard'))
    else:
        flash("Debes iniciar sesión para enviar mensajes.")
        return redirect(url_for('login_render'))

@app.route('/mensajes/recibidos')
def mensajes_recibidos():
    if 'logged_in' in session:
        receptor_id = session['usuario_id']  # ID del usuario que está viendo sus mensajes
        try:
            cursor = mydb.cursor()
            query_mensajes = '''
                SELECT m.contenido, a.nombre, a.apellido, m.fecha
                FROM mensajes m
                JOIN alumnos a ON m.idEmisor = a.idAlumno
                WHERE m.idReceptor = %s
                ORDER BY m.fecha DESC
            '''
            cursor.execute(query_mensajes, (receptor_id,))
            mensajes = cursor.fetchall()  # Recupera todos los mensajes recibidos
            cursor.close()

            return render_template('mensajes_recibidos.html', mensajes=mensajes)
        except Exception as e:
            flash(f"Error al consultar mensajes: {e}")
            return redirect(url_for('dashboard'))
    else:
        flash("Debes iniciar sesión para ver tus mensajes.")
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

            # Hasheamos la contraseña antes de almacenarla
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Guardamos la contraseña hasheada en la base de datos
            cursor = mydb.cursor()
            query = "INSERT INTO alumnos (nombre, apellido, correo, codigo, contraseña) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (nombre, apellido, correo, codigo, hashed_password.decode('utf-8')))
            mydb.commit()
            cursor.close()

            flash('Usuario agregado de manera correcta: {}'.format(nombre))
        except Exception as e:
            mydb.rollback()  # Hacemos rollback en caso de error
            flash(f"Error al realizar el registro: {e}")
        
    return render_template('registro-usuario.html')

@app.route('/autenticacion/login-face')
def login_render():
    return render_template('loginFace.html')

@app.route('/autenticacion/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo')  # Obtén el correo ingresado
        codigo = request.form.get('codigo')  # Obtén el código ingresado
        password = request.form.get('password')  # Obtén la contraseña ingresada

        if not correo or not codigo or not password:
            flash("Todos los campos son obligatorios.")
            return render_template('loginFace.html')

        try:
            # Consulta para recuperar al usuario en base al correo y código
            cursor = mydb.cursor()
            query = "SELECT * FROM alumnos WHERE correo = %s AND codigo = %s"
            cursor.execute(query, (correo, codigo))
            alumno = cursor.fetchone()  # Recupera la fila completa del alumno
            cursor.close()

            if alumno:
                stored_password = alumno[5]  # Ahora la contraseña está en la columna correcta (índice 5)
                
                # Asegúrate de que stored_password sea una cadena antes de compararla
                if isinstance(stored_password, str):
                    stored_password = stored_password.encode('utf-8')  # Convertimos a bytes

                # Comparamos la contraseña ingresada con el hash almacenado
                if bcrypt.checkpw(password.encode('utf-8'), stored_password):  # Comparación usando bcrypt
                    session['logged_in'] = True
                    session['usuario_id'] = alumno[0]
                    session['nombre'] = alumno[1]
                    flash("Inicio de sesión exitoso!")
                    return redirect(url_for('dashboard'))
                else:
                    flash("Contraseña incorrecta")
            else:
                flash("Usuario no encontrado")
        except Exception as e:
            flash(f"Error al iniciar sesión: {e}")

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

        try:
            # Recuperar información del perfil del usuario, incluyendo la foto
            cursor = mydb.cursor()
            query = "SELECT nombre, apellido, correo, foto_perfil FROM alumnos WHERE idAlumno = %s"
            cursor.execute(query, (idAlumno,))
            usuario = cursor.fetchone()

            # Recuperar mensajes recibidos
            query_mensajes = '''
                SELECT m.contenido, a.nombre, a.apellido, m.fecha
                FROM mensajes m
                JOIN alumnos a ON m.idEmisor = a.idAlumno
                WHERE m.idReceptor = %s
                ORDER BY m.fecha DESC
            '''
            cursor.execute(query_mensajes, (idAlumno,))
            mensajes = cursor.fetchall()

            cursor.close()

            return render_template(
                'dashboard.html',
                publicaciones=publicaciones,
                sesiones=sesiones,
                usuario=usuario,
                mensajes=mensajes
            )
        except Exception as e:
            flash(f"Error al cargar el dashboard: {e}")
            return redirect(url_for('login_render'))
    else:
        flash("Debe iniciar sesión para acceder al dashboard.")
        return redirect(url_for('login_render'))

def consultarTodasPublicaciones():
    try:
        cursor = mydb.cursor()
        query = '''
            SELECT alumnos.nombre, alumnos.correo, publicaciones.contenido, publicaciones.fecha, alumnos.foto_perfil
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

def consultarUsuarios():
    try:
        cursor = mydb.cursor()
        query = "SELECT idAlumno, nombre, apellido, correo FROM alumnos"
        cursor.execute(query)
        usuarios = cursor.fetchall()
        cursor.close()
        return usuarios
    except Exception as e:
        flash(f"Error al consultar usuarios: {e}")
        return []

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
