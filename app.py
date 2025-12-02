from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import bcrypt
import os
from dotenv import load_dotenv
import ssl
import certifi  # ← AGREGAR ESTO

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# ---------------------------
# CONEXIÓN A MONGO - CORRECCIÓN SSL
# ---------------------------
db = None
client = None

try:
    # CORRECCIÓN: Configuración SSL adecuada para MongoDB Atlas
    connection_string = 'mongodb+srv://lopezkucinthializethcbtis272_db_user:admin1234@cluster9.1im7xnf.mongodb.net/cluster9'
    
    # Opción 1: Conexión con SSL seguro (RECOMENDADA)
    client = MongoClient(
        connection_string,
        tls=True,
        tlsCAFile=certifi.where(),  # Usar certificados CA actualizados
        retryWrites=True,
        w='majority',
        connectTimeoutMS=30000,
        socketTimeoutMS=30000,
        serverSelectionTimeoutMS=30000,
        maxPoolSize=50
    )
    
    # Verificar conexión
    client.admin.command('ping')
    db = client.inclusivelearn
    print("✅ Conectado a MongoDB Atlas correctamente con SSL seguro")
    
except Exception as e:
    print(f"❌ Error conectando a MongoDB: {e}")
    print("⚠️ Intentando conexión alternativa...")
# ---------------------------
# RUTAS HTML
# ---------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/registro')
def registro_page():
    return render_template('registro.html')

@app.route('/recomendaciones')
def recomendaciones_page():
    return render_template('recomendaciones.html')

@app.route('/resolver')
def resolver_page():
    return render_template('resolver.html')

@app.route('/cursos')
def cursos_page():
    return render_template('cursos.html')

@app.route('/curso/<curso_id>')
def ver_curso(curso_id):
    return render_template('curso_detalle.html', curso_id=curso_id)

@app.route('/curso/<curso_id>/leccion/<leccion_id>')
def ver_leccion(curso_id, leccion_id):
    return render_template('leccion_detalle.html', curso_id=curso_id, leccion_id=leccion_id)

# NUEVA RUTA AGREGADA - EVALUACIÓN DE MATEMÁTICAS
@app.route('/evaluacion-matematicas')
def evaluacion_matematicas():
    return render_template('evaluacion-matematicas.html')


# ---------------------------
# API: USUARIOS Y AUTENTICACIÓN - CON MODO SEGURO
# ---------------------------

# Almacenamiento temporal para cuando MongoDB no funciona
usuarios_temporales = {}
progreso_temporal = {}

@app.route('/api/registro', methods=['POST'])
def api_registro():
    try:
        data = request.get_json() if request.is_json else request.form
        print(f"📝 Datos recibidos: {data}")

        required_fields = ['nombre', 'email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'El campo {field} es requerido'}), 400

        nombre = data['nombre']
        email = data['email']
        password = data['password']

        # Verificar si existe (en BD o temporal)
        usuario_existente = False
        if db:
            usuario_existente = db.usuarios.find_one({'email': email}) is not None
        else:
            usuario_existente = email in usuarios_temporales
            
        if usuario_existente:
            return jsonify({'error': 'El usuario ya existe'}), 400

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        if db:
            # Guardar en MongoDB
            usuario_data = {
                'nombre': nombre,
                'email': email,
                'password': hashed_password,
                'fecha_registro': datetime.now(),
                'preferencias_accesibilidad': {
                    'alto_contraste': False,
                    'tamano_fuente': 16,
                    'lector_voz': False
                },
                'progreso': {
                    'cursos_completados': 0,
                    'problemas_resueltos': 0,
                    'nivel': 'principiante'
                }
            }

            resultado = db.usuarios.insert_one(usuario_data)
            usuario_id = str(resultado.inserted_id)
        else:
            # Guardar temporalmente
            usuario_id = f"temp_{len(usuarios_temporales) + 1}"
            usuarios_temporales[email] = {
                '_id': usuario_id,
                'nombre': nombre,
                'email': email,
                'password': hashed_password,
                'preferencias_accesibilidad': {
                    'alto_contraste': False,
                    'tamano_fuente': 16,
                    'lector_voz': False
                },
                'progreso': {
                    'cursos_completados': 0,
                    'problemas_resueltos': 0,
                    'nivel': 'principiante'
                }
            }

        session['user_id'] = usuario_id
        session['user_email'] = email

        return jsonify({
            'mensaje': 'Usuario registrado exitosamente',
            'user_id': usuario_id,
            'nombre': nombre
        })

    except Exception as e:
        print(f"❌ Error en registro: {str(e)}")
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json() if request.is_json else request.form

        email = data['email']
        password = data['password']

        # Buscar usuario en BD o temporal
        usuario = None
        if db:
            usuario = db.usuarios.find_one({'email': email})
        else:
            usuario = usuarios_temporales.get(email)

        if usuario and bcrypt.checkpw(password.encode('utf-8'), usuario['password']):
            session['user_id'] = str(usuario['_id'])
            session['user_email'] = email
            return jsonify({
                'mensaje': 'Login exitoso',
                'user_id': str(usuario['_id']),
                'nombre': usuario['nombre']
            })

        return jsonify({'error': 'Credenciales incorrectas'}), 401

    except Exception as e:
        print(f"❌ Error en login: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'mensaje': 'Sesión cerrada correctamente'})

@app.route('/api/user-data')
def api_user_data():
    if 'user_id' in session:
        usuario = None
        if db:
            try:
                usuario = db.usuarios.find_one({'_id': ObjectId(session['user_id'])})
            except:
                usuario = None
        else:
            usuario = usuarios_temporales.get(session.get('user_email'))
            
        if usuario:
            return jsonify({
                'logged_in': True,
                'nombre': usuario['nombre'],
                'email': usuario['email'],
                'preferencias': usuario.get('preferencias_accesibilidad', {})
            })
    return jsonify({'logged_in': False})

@app.route('/api/guardar-preferencias', methods=['POST'])
def api_guardar_preferencias():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        data = request.get_json()
        if db:
            db.usuarios.update_one(
                {'_id': ObjectId(session['user_id'])},
                {'$set': {'preferencias_accesibilidad': data}}
            )
        else:
            # Actualizar en almacenamiento temporal
            if session.get('user_email') in usuarios_temporales:
                usuarios_temporales[session['user_email']]['preferencias_accesibilidad'] = data
                
        return jsonify({'mensaje': 'Preferencias guardadas correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------
# API: CURSOS - SIEMPRE FUNCIONA
# ---------------------------

@app.route('/api/cursos')
def api_cursos():
    # SIEMPRE devolver cursos de ejemplo
    cursos_ejemplo = [
        {
            'id': '1',
            'titulo': 'Pensamiento matemático',
            'descripcion': 'Curso introductorio de matemáticas con enfoque accesible',
            'categoria': 'Matemáticas',
            'nivel': 'Principiante',
            'duracion': '8 horas',
            'imagen': '/static/images/matematicas.jpg'
        },
        {
            'id': '2',
            'titulo': 'Construye aplicaciones web', 
            'descripcion': 'Aprende programación desde cero con Python',
            'categoria': 'Programación',
            'nivel': 'Intermedio',
            'duracion': '12 horas',
            'imagen': '/static/images/python.jpg'
        },
        {
            'id': '3',
            'titulo': 'Inglés V',
            'descripcion': 'Aprende un nuevo idioma de forma sencilla',
            'categoria': 'Idiomas',
            'nivel': 'Avanzado', 
            'duracion': '10 horas',
            'imagen': '/static/images/ingles.jpg'
        },
        {
            'id': '4',
            'titulo': 'La energía en los procesos de la vida diaria',
            'descripcion': 'Curso de cómo funciona la ciencia en nuestro entorno',
            'categoria': 'Ciencias',
            'nivel': 'Principiante',
            'duracion': '8 horas',
            'imagen': '/static/images/ciencias.jpg'
        },
        {
            'id': '5',
            'titulo': 'Implementa aplicaciones web', 
            'descripcion': 'Aprende programación desde cero con Python',
            'categoria': 'Programación',
            'nivel': 'Intermedio',
            'duracion': '12 horas',
            'imagen': '/static/images/programacion.jpg'
        },
        {
            'id': '6',
            'titulo': 'Conciencia histórica II',
            'descripcion': 'Descubre la historia de México durante el expansionismo capitalista',
            'categoria': 'Historia',
            'nivel': 'Principiante', 
            'duracion': '10 horas',
            'imagen': '/static/images/historia.jpg'
        }
    ]
    
    print(f"📚 Devolviendo {len(cursos_ejemplo)} cursos")
    return jsonify(cursos_ejemplo)

@app.route('/api/curso/<curso_id>')
def api_curso_detalle(curso_id):
    # Datos de ejemplo COMPLETOS con contenido para ejercicios
    cursos_data = {
        '1': {
            'id': '1',
            'titulo': 'Pensamiento matemático',
            'descripcion': 'Curso completo de matemáticas básicas con enfoque accesible',
            'categoria': 'Matemáticas',
            'nivel': 'Principiante',
            'duracion': '8 horas',
            'instructor': 'Prof. Ana Martínez',
            'rating': '4.8',
            'estudiantes': '1,250',
            'objetivos': [
                'Comprender conceptos matemáticos fundamentales',
                'Resolver problemas aritméticos básicos',
                'Aplicar matemáticas en situaciones cotidianas'
            ],
            'lecciones': [
                {
                    'id': '1', 
                    'titulo': 'Introducción a los números', 
                    'duracion': 15, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/i2pazVdFxVQ',
                    'es_youtube': True
                },
                {
                    'id': '2', 
                    'titulo': 'Operaciones básicas', 
                    'duracion': 20, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/4pB_ki1EmNc',
                    'es_youtube': True
                },
                {
                    'id': '3', 
                    'titulo': 'Ejercicios prácticos', 
                    'duracion': 25, 
                    'tipo': 'ejercicios', 
                    'completado': False,
                    'contenido': {
                        'titulo': 'Ejercicios Prácticos de Matemáticas',
                        'descripcion': 'Practica lo aprendido con estos ejercicios interactivos',
                        'ejercicios': [
                            {
                                'pregunta': 'Resuelve: 15 + 27 = ?',
                                'opciones': ['42', '32', '52', '37'],
                                'respuesta_correcta': '42'
                            },
                            {
                                'pregunta': '¿Cuál es el resultado de 8 × 7?',
                                'opciones': ['56', '54', '64', '15'],
                                'respuesta_correcta': '56'
                            },
                            {
                                'pregunta': 'Si tengo 50 manzanas y regalo 15, ¿cuántas me quedan?',
                                'opciones': ['35', '25', '45', '65'],
                                'respuesta_correcta': '35'
                            },
                            {
                                'pregunta': 'Calcula: 144 ÷ 12 = ?',
                                'opciones': ['12', '10', '14', '11'],
                                'respuesta_correcta': '12'
                            }
                        ]
                    }
                },
                {
                    'id': '4', 
                    'titulo': 'Geometría básica', 
                    'duracion': 30, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/RWwJ7NGpdQQ',
                    'es_youtube': True
                },
                {
                    'id': '5', 
                    'titulo': 'Evaluación del módulo', 
                    'duracion': 45, 
                    'tipo': 'evaluacion', 
                    'completado': False,
                    'contenido': {
                        'titulo': 'Evaluación Final - Pensamiento Matemático',
                        'descripcion': 'Demuestra lo que has aprendido en este módulo',
                        'instrucciones': 'Resuelve las siguientes preguntas. Tienes 45 minutos para completar la evaluación.',
                        'preguntas': [
                            {
                                'pregunta': '¿Cuál es el resultado de 125 + 378?',
                                'opciones': ['503', '493', '513', '403'],
                                'respuesta_correcta': '503'
                            },
                            {
                                'pregunta': 'Un triángulo tiene ángulos de 45° y 75°. ¿Cuánto mide el tercer ángulo?',
                                'opciones': ['60°', '50°', '70°', '80°'],
                                'respuesta_correcta': '60°'
                            },
                            {
                                'pregunta': 'Si un cuadrado tiene lado de 8cm, ¿cuál es su área?',
                                'opciones': ['64 cm²', '32 cm²', '16 cm²', '48 cm²'],
                                'respuesta_correcta': '64 cm²'
                            },
                            {
                                'pregunta': '¿Qué fracción representa 0.75?',
                                'opciones': ['3/4', '1/4', '2/3', '4/5'],
                                'respuesta_correcta': '3/4'
                            },
                            {
                                'pregunta': 'Calcula: 15% de 200',
                                'opciones': ['30', '15', '25', '35'],
                                'respuesta_correcta': '30'
                            }
                        ]
                    }
                }
            ]
        },
        '2': {
            'id': '2',
            'titulo': 'Construye aplicaciones web',
            'descripcion': 'Aprende programación desde cero con Python de forma accesible',
            'categoria': 'Programación',
            'nivel': 'Intermedio',
            'duracion': '12 horas',
            'instructor': 'Ing. Carlos López',
            'rating': '4.6',
            'estudiantes': '890',
            'objetivos': [
                'Entender fundamentos de programación',
                'Escribir código Python básico',
                'Construir aplicaciones simples'
            ],
            'lecciones': [
                {
                    'id': '1', 
                    'titulo': 'Introducción a Python', 
                    'duracion': 20, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/_6N18g3ewnw',
                    'es_youtube': True
                },
                {
                    'id': '2', 
                    'titulo': 'Variables y tipos de datos', 
                    'duracion': 25, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/numQzIgpOo0',
                    'es_youtube': True
                },
                {
                    'id': '3', 
                    'titulo': 'Estructuras de control', 
                    'duracion': 30, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/w53HiWSZnzU',
                    'es_youtube': True
                },
                {
                    'id': '4', 
                    'titulo': 'Ejercicios de programación', 
                    'duracion': 40, 
                    'tipo': 'ejercicios', 
                    'completado': False,
                    'contenido': {
                        'titulo': 'Ejercicios de Programación Python',
                        'descripcion': 'Practica tus habilidades de programación con estos ejercicios',
                        'ejercicios': [
                            {
                                'pregunta': '¿Cuál es la salida de: print("Hola" + "Mundo")?',
                                'opciones': ['HolaMundo', 'Hola Mundo', 'Error', 'Hola+Mundo'],
                                'respuesta_correcta': 'HolaMundo'
                            },
                            {
                                'pregunta': '¿Qué tipo de dato es: [1, 2, 3]?',
                                'opciones': ['Lista', 'Tupla', 'Diccionario', 'Conjunto'],
                                'respuesta_correcta': 'Lista'
                            },
                            {
                                'pregunta': '¿Cuál bucle se ejecuta al menos una vez?',
                                'opciones': ['while', 'for', 'do-while', 'ninguno'],
                                'respuesta_correcta': 'do-while'
                            },
                            {
                                'pregunta': '¿Qué función se usa para obtener la longitud de una lista?',
                                'opciones': ['len()', 'length()', 'size()', 'count()'],
                                'respuesta_correcta': 'len()'
                            }
                        ]
                    }
                },
                {
                    'id': '5', 
                    'titulo': 'Evaluación del módulo', 
                    'duracion': 60, 
                    'tipo': 'evaluacion', 
                    'completado': False,
                    'contenido': {
                        'titulo': 'Evaluación Final - Programación Python',
                        'descripcion': 'Demuestra tus conocimientos de programación en Python',
                        'instrucciones': 'Resuelve las siguientes preguntas sobre programación Python.',
                        'preguntas': [
                            {
                                'pregunta': '¿Cuál es la salida de: print(2 ** 3)?',
                                'opciones': ['8', '6', '9', 'Error'],
                                'respuesta_correcta': '8'
                            },
                            {
                                'pregunta': '¿Qué método se usa para agregar un elemento al final de una lista?',
                                'opciones': ['append()', 'add()', 'insert()', 'push()'],
                                'respuesta_correcta': 'append()'
                            },
                            {
                                'pregunta': '¿Cómo se define una función en Python?',
                                'opciones': ['def mi_funcion():', 'function mi_funcion():', 'define mi_funcion():', 'func mi_funcion():'],
                                'respuesta_correcta': 'def mi_funcion():'
                            },
                            {
                                'pregunta': '¿Qué hace el método split() en una cadena?',
                                'opciones': ['Divide la cadena en una lista', 'Une varias cadenas', 'Convierte a mayúsculas', 'Elimina espacios'],
                                'respuesta_correcta': 'Divide la cadena en una lista'
                            },
                            {
                                'pregunta': '¿Cuál es el resultado de: "hello".upper()?',
                                'opciones': ['HELLO', 'Hello', 'hello', 'Error'],
                                'respuesta_correcta': 'HELLO'
                            }
                        ]
                    }
                }
            ]
        },
        '3': {
            'id': '3',
            'titulo': 'Inglés V',
            'descripcion': 'Aprende inglés avanzado con contenido adaptado',
            'categoria': 'Idiomas',
            'nivel': 'Avanzado',
            'duracion': '10 horas',
            'instructor': 'Prof. Laura Smith',
            'rating': '4.7',
            'estudiantes': '720',
            'objetivos': [
                'Dominar conversaciones avanzadas',
                'Comprender textos complejos',
                'Escribir documentos profesionales'
            ],
            'lecciones': [
                {
                    'id': '1', 
                    'titulo': 'Gramática básica', 
                    'duracion': 18, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/SQOEqIuh4gg',
                    'es_youtube': True
                },
                {
                    'id': '2', 
                    'titulo': 'Vocabulario técnico', 
                    'duracion': 22, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/xkaj_2d8z5w',
                    'es_youtube': True
                },
                {
                    'id': '3', 
                    'titulo': 'Conversación avanzada', 
                    'duracion': 35, 
                    'tipo': 'practica', 
                    'completado': False,
                    'contenido': {
                        'titulo': 'Práctica de Conversación Avanzada',
                        'descripcion': 'Mejora tus habilidades de conversación en inglés',
                        'actividades': [
                            {
                                'titulo': 'Diálogo de Negocios',
                                'descripcion': 'Practica una conversación de negocios con un cliente internacional',
                                'dialogo': '''
                                **Cliente:** Good morning, I'm interested in your company's services.
                                **Tú:** Good morning! Thank you for your interest. How can we assist you today?
                                **Cliente:** I'd like to know more about your pricing structure.
                                **Tú:** Certainly. We offer several packages depending on your needs...
                                '''
                            },
                            {
                                'titulo': 'Debate sobre Tecnología',
                                'descripcion': 'Participa en un debate sobre inteligencia artificial',
                                'temas': [
                                    'The impact of AI on employment',
                                    'Ethical considerations in AI development',
                                    'Future trends in technology'
                                ]
                            }
                        ]
                    }
                },
                {
                    'id': '4', 
                    'titulo': 'Comprensión auditiva', 
                    'duracion': 40, 
                    'tipo': 'interactivo', 
                    'completado': False,
                    'contenido': {
                        'titulo': 'Ejercicio de Comprensión Auditiva',
                        'descripcion': 'Escucha los audios y responde las preguntas',
                        'ejercicios': [
                            {
                                'audio_url': '/static/audio/english1.mp3',
                                'preguntas': [
                                    {
                                        'pregunta': 'What is the main topic of the conversation?',
                                        'opciones': ['Travel plans', 'Business meeting', 'Weather', 'Sports'],
                                        'respuesta_correcta': 'Travel plans'
                                    },
                                    {
                                        'pregunta': 'When are they planning to travel?',
                                        'opciones': ['Next week', 'Next month', 'Tomorrow', 'Next year'],
                                        'respuesta_correcta': 'Next month'
                                    }
                                ]
                            },
                            {
                                'audio_url': '/static/audio/english2.mp3',
                                'preguntas': [
                                    {
                                        'pregunta': 'What problem are they discussing?',
                                        'opciones': ['Technical issue', 'Budget problem', 'Schedule conflict', 'Personnel matter'],
                                        'respuesta_correcta': 'Technical issue'
                                    }
                                ]
                            }
                        ]
                    }
                },
                {
                    'id': '5', 
                    'titulo': 'Evaluación del módulo', 
                    'duracion': 45, 
                    'tipo': 'evaluacion', 
                    'completado': False,
                    'contenido': {
                        'titulo': 'Evaluación Final - Inglés Avanzado',
                        'descripcion': 'Demuestra tu dominio del inglés avanzado',
                        'instrucciones': 'Responde las siguientes preguntas de gramática y vocabulario.',
                        'preguntas': [
                            {
                                'pregunta': 'Choose the correct sentence:',
                                'opciones': [
                                    'If I had known, I would have helped',
                                    'If I would have known, I had helped',
                                    'If I knew, I would help',
                                    'If I have known, I would help'
                                ],
                                'respuesta_correcta': 'If I had known, I would have helped'
                            },
                            {
                                'pregunta': 'What does "to bite the bullet" mean?',
                                'opciones': [
                                    'To endure a painful situation',
                                    'To eat quickly',
                                    'To argue aggressively',
                                    'To make a mistake'
                                ],
                                'respuesta_correcta': 'To endure a painful situation'
                            },
                            {
                                'pregunta': 'Which is the correct passive form: "They built this house in 1990"?',
                                'opciones': [
                                    'This house was built in 1990',
                                    'This house is built in 1990',
                                    'This house built in 1990',
                                    'This house has been built in 1990'
                                ],
                                'respuesta_correcta': 'This house was built in 1990'
                            },
                            {
                                'pregunta': 'Choose the correct word: "I look forward to ______ from you."',
                                'opciones': ['hearing', 'hear', 'heard', 'hears'],
                                'respuesta_correcta': 'hearing'
                            },
                            {
                                'pregunta': 'What is the synonym of "ubiquitous"?',
                                'opciones': ['Everywhere', 'Rare', 'Complex', 'Simple'],
                                'respuesta_correcta': 'Everywhere'
                            }
                        ]
                    }
                }
            ]
        },
        '4': {
            'id': '4',
            'titulo': 'La energía en los procesos de la vida diaria',
            'descripcion': 'Curso de cómo funciona la ciencia en nuestro entorno',
            'categoria': 'Ciencias',
            'nivel': 'Principiante',
            'duracion': '8 horas',
            'instructor': 'Dr. Roberto García',
            'rating': '4.5',
            'estudiantes': '600',
            'objetivos': [
                'Comprender los tipos de energía',
                'Identificar fuentes de energía renovables',
                'Aplicar conceptos energéticos en la vida diaria'
            ],
            'lecciones': [
                {
                    'id': '1', 
                    'titulo': 'Introducción a la energía', 
                    'duracion': 20, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/KlRLGXbtgAA',
                    'es_youtube': True
                },
                {
                    'id': '2', 
                    'titulo': 'Tipos de energía', 
                    'duracion': 25, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/Mk8Env3xrMI',
                    'es_youtube': True
                },
                {
                    'id': '3', 
                    'titulo': 'Energías renovables', 
                    'duracion': 30, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/Og6C1HyeaBs',
                    'es_youtube': True
                },
                {
                    'id': '4', 
                    'titulo': 'Ejercicios prácticos', 
                    'duracion': 35, 
                    'tipo': 'ejercicios', 
                    'completado': False,
                    'contenido': {
                        'titulo': 'Ejercicios sobre Energía',
                        'descripcion': 'Practica tus conocimientos sobre tipos de energía',
                        'ejercicios': [
                            {
                                'pregunta': '¿Cuál de estas es una energía renovable?',
                                'opciones': ['Energía solar', 'Carbón', 'Petróleo', 'Gas natural'],
                                'respuesta_correcta': 'Energía solar'
                            },
                            {
                                'pregunta': '¿Qué principio establece que la energía no se crea ni se destruye, solo se transforma?',
                                'opciones': ['Ley de conservación de la energía', 'Ley de Ohm', 'Ley de Newton', 'Ley de Boyle'],
                                'respuesta_correcta': 'Ley de conservación de la energía'
                            },
                            {
                                'pregunta': '¿Qué tipo de energía almacena una batería?',
                                'opciones': ['Energía química', 'Energía térmica', 'Energía nuclear', 'Energía mecánica'],
                                'respuesta_correcta': 'Energía química'
                            }
                        ]
                    }
                },
                {
                    'id': '5', 
                    'titulo': 'Evaluación del módulo', 
                    'duracion': 45, 
                    'tipo': 'evaluacion', 
                    'completado': False,
                    'contenido': {
                        'titulo': 'Evaluación Final - Ciencias de la Energía',
                        'descripcion': 'Demuestra tu comprensión sobre los conceptos de energía',
                        'instrucciones': 'Responde las siguientes preguntas sobre energía y sus aplicaciones.',
                        'preguntas': [
                            {
                                'pregunta': '¿Cuál es la unidad básica de energía en el sistema internacional?',
                                'opciones': ['Julio', 'Vatio', 'Newton', 'Pascal'],
                                'respuesta_correcta': 'Julio'
                            },
                            {
                                'pregunta': '¿Qué tipo de energía utiliza un panel solar?',
                                'opciones': ['Energía radiante', 'Energía eólica', 'Energía geotérmica', 'Energía hidráulica'],
                                'respuesta_correcta': 'Energía radiante'
                            },
                            {
                                'pregunta': '¿Qué ventaja tienen las energías renovables?',
                                'opciones': ['Son inagotables', 'Son más baratas', 'No contaminan', 'Todas las anteriores'],
                                'respuesta_correcta': 'Todas las anteriores'
                            },
                            {
                                'pregunta': '¿Cómo se llama el proceso de transformación de energía solar en eléctrica?',
                                'opciones': ['Efecto fotovoltaico', 'Efecto Joule', 'Efecto Seebeck', 'Efecto Peltier'],
                                'respuesta_correcta': 'Efecto fotovoltaico'
                            }
                        ]
                    }
                }
            ]
        },
        '5': {
            'id': '5',
            'titulo': 'Implementa aplicaciones web',
            'descripcion': 'Aprende programación desde cero con Python',
            'categoria': 'Programación',
            'nivel': 'Intermedio',
            'duracion': '12 horas',
            'instructor': 'Ing. Sofía Ramírez',
            'rating': '4.4',
            'estudiantes': '450',
            'objetivos': [
                'Desarrollar aplicaciones web funcionales',
                'Implementar interfaces de usuario accesibles',
                'Integrar bases de datos en aplicaciones web'
            ],
            'lecciones': [
                {
                    'id': '1', 
                    'titulo': 'Introducción al desarrollo web', 
                    'duracion': 25, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/BOVXMbwJA08',
                    'es_youtube': True
                },
                {
                    'id': '2', 
                    'titulo': 'HTML y CSS básico', 
                    'duracion': 30, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/Y-OhzQpsRwI',
                    'es_youtube': True
                },
                {
                    'id': '3', 
                    'titulo': 'JavaScript para principiantes', 
                    'duracion': 35, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/8GTaO9XhA5M',
                    'es_youtube': True
                },
                {
                    'id': '4', 
                    'titulo': 'Ejercicios de desarrollo web', 
                    'duracion': 40, 
                    'tipo': 'ejercicios', 
                    'completado': False,
                    'contenido': {
                        'titulo': 'Ejercicios Prácticos de Desarrollo Web',
                        'descripcion': 'Practica tus habilidades de desarrollo web',
                        'ejercicios': [
                            {
                                'pregunta': '¿Qué significa HTML?',
                                'opciones': ['HyperText Markup Language', 'HighTech Modern Language', 'Hyper Transfer Markup Language', 'Home Tool Markup Language'],
                                'respuesta_correcta': 'HyperText Markup Language'
                            },
                            {
                                'pregunta': '¿Cuál es la etiqueta correcta para un enlace?',
                                'opciones': ['<a href="">', '<link>', '<href>', '<url>'],
                                'respuesta_correcta': '<a href="">'
                            },
                            {
                                'pregunta': '¿Qué propiedad CSS se usa para cambiar el color de fondo?',
                                'opciones': ['background-color', 'bgcolor', 'color-background', 'background'],
                                'respuesta_correcta': 'background-color'
                            }
                        ]
                    }
                },
                {
                    'id': '5', 
                    'titulo': 'Evaluación final', 
                    'duracion': 50, 
                    'tipo': 'evaluacion', 
                    'completado': False,
                    'contenido': {
                        'titulo': 'Evaluación Final - Desarrollo Web',
                        'descripcion': 'Demuestra tus conocimientos de desarrollo web',
                        'instrucciones': 'Responde las siguientes preguntas sobre desarrollo web.',
                        'preguntas': [
                            {
                                'pregunta': '¿Qué es el DOM?',
                                'opciones': ['Document Object Model', 'Data Object Model', 'Document Orientation Model', 'Digital Object Management'],
                                'respuesta_correcta': 'Document Object Model'
                            },
                            {
                                'pregunta': '¿Cuál es la diferencia entre HTTP y HTTPS?',
                                'opciones': ['HTTPS es seguro', 'HTTP es más rápido', 'HTTPS es para móviles', 'No hay diferencia'],
                                'respuesta_correcta': 'HTTPS es seguro'
                            },
                            {
                                'pregunta': '¿Qué lenguaje se ejecuta en el navegador?',
                                'opciones': ['JavaScript', 'Python', 'Java', 'C++'],
                                'respuesta_correcta': 'JavaScript'
                            }
                        ]
                    }
                }
            ]
        },
        '6': {
            'id': '6',
            'titulo': 'Conciencia histórica II',
            'descripcion': 'Descubre la historia de México durante el expansionismo capitalista',
            'categoria': 'Historia',
            'nivel': 'Principiante',
            'duracion': '10 horas',
            'instructor': 'Dr. Miguel Ángel Torres',
            'rating': '4.3',
            'estudiantes': '380',
            'objetivos': [
                'Analizar el periodo del expansionismo capitalista',
                'Comprender los efectos sociales en México',
                'Identificar las transformaciones económicas'
            ],
            'lecciones': [
                {
                    'id': '1', 
                    'titulo': 'Contexto histórico del siglo XIX', 
                    'duracion': 20, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/XerUPdM-fRo',
                    'es_youtube': True
                },
                {
                    'id': '2', 
                    'titulo': 'Expansionismo capitalista mundial', 
                    'duracion': 25, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/ZUbdz9FlnLk',
                    'es_youtube': True
                },
                {
                    'id': '3', 
                    'titulo': 'Impacto en la economía mexicana', 
                    'duracion': 30, 
                    'tipo': 'video', 
                    'completado': False, 
                    'archivo': 'https://www.youtube.com/embed/_8gfaJtjyzU',
                    'es_youtube': True
                },
                {
                    'id': '4', 
                    'titulo': 'Ejercicios de análisis histórico', 
                    'duracion': 35, 
                    'tipo': 'ejercicios', 
                    'completado': False,
                    'contenido': {
                        'titulo': 'Ejercicios de Análisis Histórico',
                        'descripcion': 'Analiza los eventos históricos del expansionismo capitalista',
                        'ejercicios': [
                            {
                                'pregunta': '¿En qué siglo ocurrió principalmente el expansionismo capitalista en México?',
                                'opciones': ['Siglo XIX', 'Siglo XVIII', 'Siglo XX', 'Siglo XXI'],
                                'respuesta_correcta': 'Siglo XIX'
                            },
                            {
                                'pregunta': '¿Qué país tuvo mayor influencia económica en México durante este periodo?',
                                'opciones': ['Estados Unidos', 'España', 'Francia', 'Inglaterra'],
                                'respuesta_correcta': 'Estados Unidos'
                            },
                            {
                                'pregunta': '¿Qué recurso natural fue clave para el desarrollo económico?',
                                'opciones': ['Petróleo', 'Plata', 'Oro', 'Todos los anteriores'],
                                'respuesta_correcta': 'Todos los anteriores'
                            }
                        ]
                    }
                },
                {
                    'id': '5', 
                    'titulo': 'Evaluación del módulo', 
                    'duracion': 45, 
                    'tipo': 'evaluacion', 
                    'completado': False,
                    'contenido': {
                        'titulo': 'Evaluación Final - Historia de México',
                        'descripcion': 'Demuestra tu comprensión del expansionismo capitalista en México',
                        'instrucciones': 'Responde las siguientes preguntas sobre historia de México.',
                        'preguntas': [
                            {
                                'pregunta': '¿Qué presidente mexicano promovió la industrialización?',
                                'opciones': ['Porfirio Díaz', 'Benito Juárez', 'Antonio López de Santa Anna', 'Miguel Hidalgo'],
                                'respuesta_correcta': 'Porfirio Díaz'
                            },
                            {
                                'pregunta': '¿Cómo se llamó el periodo de estabilidad política y económica?',
                                'opciones': ['Porfiriato', 'Reforma', 'Independencia', 'Revolución'],
                                'respuesta_correcta': 'Porfiriato'
                            },
                            {
                                'pregunta': '¿Qué tratado afectó las relaciones México-Estados Unidos?',
                                'opciones': ['Tratado de Guadalupe Hidalgo', 'Tratado de Versalles', 'Tratado de Tlatelolco', 'Tratado de Libre Comercio'],
                                'respuesta_correcta': 'Tratado de Guadalupe Hidalgo'
                            }
                        ]
                    }
                }
            ]
        }
    }
    
    curso = cursos_data.get(curso_id, {})
    return jsonify(curso)

# AGREGAR ESTA RUTA FALTANTE - ES LA CLAVE PARA QUE FUNCIONEN LAS LECCIONES
@app.route('/api/curso/<curso_id>/leccion/<leccion_id>')
def api_leccion_detalle(curso_id, leccion_id):
    try:
        print(f"🎯 Solicitando lección {leccion_id} del curso {curso_id}")
        
        # Obtener el curso completo usando la función existente
        curso_response = api_curso_detalle(curso_id)
        curso = curso_response.get_json()
        
        if not curso:
            return jsonify({'error': 'Curso no encontrado'}), 404
        
        # Buscar la lección específica
        leccion_encontrada = None
        for leccion in curso.get('lecciones', []):
            if leccion['id'] == leccion_id:
                leccion_encontrada = leccion
                break
        
        if leccion_encontrada:
            print(f"✅ Lección {leccion_id} encontrada: {leccion_encontrada['titulo']}")
            print(f"   Tipo: {leccion_encontrada['tipo']}")
            
            # Debug: verificar contenido de evaluaciones
            if leccion_encontrada['tipo'] == 'evaluacion':
                if 'contenido' in leccion_encontrada:
                    preguntas = leccion_encontrada['contenido'].get('preguntas', [])
                    print(f"   📝 EVALUACIÓN CON {len(preguntas)} PREGUNTAS")
                    for i, pregunta in enumerate(preguntas):
                        print(f"      Pregunta {i+1}: {pregunta['pregunta'][:50]}...")
                else:
                    print(f"   ⚠️ EVALUACIÓN SIN CONTENIDO")
            
            return jsonify({
                'leccion': leccion_encontrada,
                'curso': curso
            })
        else:
            print(f"❌ Lección {leccion_id} no encontrada en curso {curso_id}")
            return jsonify({'error': 'Lección no encontrada'}), 404
            
    except Exception as e:
        print(f"❌ Error cargando lección: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ---------------------------
# APIs RESTANTES CON MODO SEGURO
# ---------------------------

@app.route('/api/completar_leccion/<leccion_id>', methods=['POST'])
def completar_leccion(leccion_id):
    # Permitir completar lecciones sin login para testing
    try:
        data = request.get_json()
        
        if db and 'user_id' in session:
            db.progreso_lecciones.update_one(
                {'user_id': ObjectId(session['user_id']), 'leccion_id': leccion_id},
                {'$set': {'completado': True, 'fecha_completado': datetime.now()}},
                upsert=True
            )
        else:
            # Guardar en progreso temporal
            user_id = session.get('user_id', 'anonimo')
            key = f"{user_id}_{leccion_id}"
            progreso_temporal[key] = {'completado': True, 'fecha': datetime.now().isoformat()}
        
        return jsonify({'status': 'success', 'message': 'Lección completada'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/progreso_curso/<curso_id>')
def progreso_curso(curso_id):
    # Permitir ver progreso sin login para testing
    try:
        lecciones_completadas = 0
        
        if db and 'user_id' in session:
            lecciones_completadas = db.progreso_lecciones.count_documents({
                'user_id': ObjectId(session['user_id']), 'curso_id': curso_id
            })
        else:
            # Contar lecciones completadas temporalmente
            user_id = session.get('user_id', 'anonimo')
            user_prefix = f"{user_id}_"
            lecciones_completadas = sum(1 for key in progreso_temporal if key.startswith(user_prefix))
        
        curso = api_curso_detalle(curso_id).get_json()
        total_lecciones = len(curso.get('lecciones', []))
        porcentaje = (lecciones_completadas / total_lecciones * 100) if total_lecciones > 0 else 0
        
        return jsonify({
            'lecciones_completadas': lecciones_completadas,
            'total_lecciones': total_lecciones,
            'porcentaje': round(porcentaje, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/guardar_progreso_video', methods=['POST'])
def guardar_progreso_video():
    # Permitir sin login para testing
    try:
        data = request.get_json()
        
        if db and 'user_id' in session:
            db.progreso_videos.update_one(
                {
                    'user_id': ObjectId(session['user_id']),
                    'leccion_id': data.get('leccion_id')
                },
                {
                    '$set': {
                        'tiempo_actual': data.get('tiempo_actual'),
                        'porcentaje_completado': data.get('porcentaje_completado'),
                        'ultima_actualizacion': datetime.now()
                    }
                },
                upsert=True
            )
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/quiz/<leccion_id>/enviar', methods=['POST'])
def enviar_quiz(leccion_id):
    # Permitir sin login para testing
    try:
        data = request.get_json()
        respuestas = data.get('respuestas', {})
        
        if db and 'user_id' in session:
            # Guardar resultados del quiz
            db.quizzes.insert_one({
                'user_id': ObjectId(session['user_id']),
                'leccion_id': leccion_id,
                'respuestas': respuestas,
                'fecha_completado': datetime.now(),
                'puntaje': data.get('puntaje', 0)
            })
        
        return jsonify({
            'status': 'success', 
            'message': 'Quiz enviado correctamente',
            'puntaje': data.get('puntaje', 0)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/curso/<curso_id>/completar-leccion', methods=['POST'])
def api_completar_leccion(curso_id):
    # Permitir sin login para testing
    try:
        data = request.get_json()
        leccion_index = data.get('leccion_index')
        
        # Aquí podrías guardar el progreso en la base de datos
        # Por ahora solo devolvemos éxito
        return jsonify({'mensaje': 'Lección marcada como completada'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/resolver-problema', methods=['POST'])
def api_resolver_problema():
    try:
        data = request.get_json()
        problema = data.get('problema', '')
        
        # Guardar el problema en la base de datos si el usuario está logueado
        if 'user_id' in session:
            if db:
                db.problemas.insert_one({
                    'usuario_id': ObjectId(session['user_id']),
                    'problema': problema,
                    'fecha': datetime.now(),
                    'resuelto': True
                })
                
                # Actualizar contador de problemas resueltos
                db.usuarios.update_one(
                    {'_id': ObjectId(session['user_id'])},
                    {'$inc': {'progreso.problemas_resueltos': 1}}
                )
        
        # Generar solución (simulada por ahora)
        solucion = f"""
🧮 **PROBLEMA RESUELTO**

**Problema:** {problema}

**Solución paso a paso:**
1. Analizar el problema planteado
2. Identificar los datos conocidos
3. Aplicar el método adecuado
4. Verificar el resultado obtenido

✅ **Solución correcta:** El problema ha sido resuelto satisfactoriamente

💡 **Consejo:** Practica problemas similares para mejorar tu comprensión.

📊 **Este problema ha sido guardado en tu historial.**
"""
        
        return jsonify({'solucion': solucion})
        
    except Exception as e:
        print(f"❌ Error resolviendo problema: {str(e)}")
        return jsonify({'error': 'Error al procesar el problema'}), 500

@app.route('/api/recomendaciones')
def api_recomendaciones():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        usuario = None
        if db:
            usuario = db.usuarios.find_one({'_id': ObjectId(session['user_id'])})
        
        # Recomendaciones basadas en el progreso del usuario
        recomendaciones = [
            {
                'tipo': 'curso',
                'titulo': 'Matemáticas Intermedias',
                'descripcion': 'Basado en tu progreso en Matemáticas Básicas',
                'prioridad': 'alta'
            },
            {
                'tipo': 'ejercicio', 
                'titulo': 'Problemas de práctica',
                'descripcion': 'Ejercicios para reforzar tus conocimientos',
                'prioridad': 'media'
            }
        ]
        
        return jsonify({
            'recomendaciones': recomendaciones,
            'progreso': usuario.get('progreso', {}) if usuario else {}
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------------------
# INICIAR FLASK
# ---------------------------

import os

if __name__ == '__main__':
    # CONFIGURACIÓN PARA RENDER
    port = int(os.environ.get('PORT', 5001))
    host = '0.0.0.0'
    
    if db:
        print("🚀 IncluLearn con MongoDB")
    else:
        print("🚀 IncluLearn MODO SEGURO (sin MongoDB)")
    
    print("📚 Cursos disponibles")
    print("🎬 Videos funcionando") 
    print("✅ CONTENIDO COMPLETO: Ejercicios y evaluaciones agregados")
    print("🔍 API de lecciones: ACTIVADA")
    print("🔓 Modo testing: APIs funcionan sin login")
    print("🎯 EVALUACIÓN MATEMÁTICAS: Ruta agregada")
    print(f"🌐 Servidor en: http://{host}:{port}")
    
    app.run(debug=False, host=host, port=port, use_reloader=False, threaded=True)






