import os
import time

import minizinc
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from werkzeug.utils import secure_filename
from pathlib import Path

# --- La configuración no cambia ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt'}
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'una-clave-secreta-muy-segura'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_txt_to_data_dict(filepath):
    """
    Lee un archivo .txt y lo parsea a un diccionario de Python
    que la biblioteca minizinc-python pueda usar.
    """
    data = {}
    try:
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f if line.strip()] # Ignorar líneas vacías

        data['n'] = int(lines[0])
        data['m'] = int(lines[1])

        # Convertir listas de strings a listas de números
        data['p'] = [int(x) for x in lines[2].split(',')]
        data['ext'] = [float(x) for x in lines[3].split(',')]
        data['ce'] = [float(x) for x in lines[4].split(',')]

        # Procesar la matriz 'c'
        c_matrix = []
        c_lines = lines[5:5+data['m']]
        for line in c_lines:
            c_matrix.append([float(x) for x in line.split(',')])
        data['c'] = c_matrix

        data['ct'] = float(lines[5+data['m']])
        data['maxM'] = int(lines[5+data['m']+1])

        return data

    except (IOError, IndexError, ValueError) as e:
        flash(f'Error parseando el archivo TXT: {e}. Por favor, revisa el formato.', 'error')
        return None

# --- Rutas de la App ---
@app.route('/')
def index():
    data = session.get('data', None)
    original_filename = session.get('original_filename', None)
    txt_content = session.get('txt_content', None)

    dzn_preview = ""
    if data:
        c_str = "c = [| " + "\n   | ".join([", ".join(map(str, row)) for row in data['c']]) + " |];\n\n"
        dzn_preview = f"n = {data['n']};\nm = {data['m']};\n\np = {data['p']};\next = {data['ext']};\nce = {data['ce']};\n\n{c_str}ct = {data['ct']};\nmaxM = {data['maxM']};"
    return render_template('index.html', txt_content=txt_content, dzn_content=dzn_preview, filename=original_filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Encapsula la logica necesaria para subir el archivo"""
    if 'file' not in request.files:
        flash('No se encontró el campo del archivo.', 'error')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó ningún archivo.', 'error')
        return redirect(url_for('index'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Parsear el archivo y guardar el diccionario de datos en la sesión
        data = parse_txt_to_data_dict(filepath)
        if data:
            session['data'] = data
            session['original_filename'] = filename
            with open(filepath, 'r') as f:
                session['txt_content'] = f.read()
            flash('Archivo cargado y parseado con éxito!', 'success')

        return redirect(url_for('index'))
    else:
        flash('Formato de archivo no permitido. Sube un .txt', 'error')
        return redirect(url_for('index'))


@app.route('/run_model', methods=['POST'])
def run_model():
    """Ejecuta el modelo MiniZinc con los datos de la sesión."""
    data = session.get('data', None)
    if not data:
        flash("No hay datos cargados para ejecutar el modelo.", "error")
        return redirect(url_for('index'))

    try:
        initial_extremism = sum(pi * exti for pi, exti in zip(data['p'], data['ext']))
    except (TypeError, KeyError):
        # Medida de seguridad por si los datos están mal formados
        initial_extremism = 0
        flash("No se pudo calcular el extremismo inicial debido a datos inválidos.", "warning")

    try:
        
        # Carga el binario de MiniZinc desde la ruta especificada si existe
        if 'MINIZINC_BIN_PATH' in os.environ: 
            MINIZINC_BIN = Path(os.environ['MINIZINC_BIN_PATH'])
            driver = minizinc.Driver(MINIZINC_BIN)
            minizinc.default_driver = driver
            
        # 1. Cargar el modelo .mzn
        model = minizinc.Model("./Proyecto.mzn")

        # 2. Seleccionar el solver (Gecode viene por defecto con MiniZinc)
        solver = minizinc.Solver.lookup("coin-bc")

        # 3. Crear una instancia del modelo con nuestros datos
        instance = minizinc.Instance(solver, model)

        # 4. Asignar los datos del diccionario a la instancia
        for key, value in data.items():
            instance[key] = value

        # 5. Ejecutar el solver
        result = instance.solve(timeout=datetime.timedelta(seconds=500))

        if result.status == minizinc.Status.OPTIMAL_SOLUTION or result.status == minizinc.Status.SATISFIED:
            # 6. Extraer los resultados y guardarlos para la página de resultados
            # Usamos result.solution para acceder a las variables por su nombre
            solve_time_delta = result.statistics.get('solveTime', datetime.timedelta(0))
            execution_time = solve_time_delta.total_seconds()

            final_results = {
                "initial_extremism": f"{initial_extremism:.4f}",
                "extremismo_final": f"{result.objective:.4f} (MINIMIZADO)",
                "costo_total": f"{result['total_cost']:.4f}",
                "movimientos_totales": result['total_moves'],
                "matriz_x": result['x'],
                "p_final": result['p_final'],
                "ct_max": data['ct'],
                "maxM_max": data['maxM'],
                "initial_p": data['p'],
                "execution_time": f"{execution_time:.4f} segundos",
                "status": str(result.status)
            }
            print("to aca")
            session['results'] = final_results
            return redirect(url_for('show_results'))
        else:
            flash(f"El modelo no encontró una solución óptima. Estado: {result.status}", "error")
            return redirect(url_for('index'))

    except minizinc.error.MiniZincError as e:
        flash(f"Ocurrió un error con MiniZinc: {e}", "error")
        print(f"Error de MiniZinc: {e}")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Un error inesperado ocurrió: {e}", "error")
        print(f"Error inesperado: {e}")
        return redirect(url_for('index'))


# La ruta /download_dzn genera el dzn desde los datos de sesión y permite la descarga del archivo
@app.route('/download_dzn')
def download_dzn():
    data = session.get('data', None)
    if not data:
        flash('No hay datos para generar el DZN.', 'error')
        return redirect(url_for('index'))

    c_str = "c = [| " + "\n   | ".join([", ".join(map(str, row)) for row in data['c']]) + " |];\n\n"
    dzn_content = f"n = {data['n']};\nm = {data['m']};\n\np = {data['p']};\next = {data['ext']};\nce = {data['ce']};\n\n{c_str}ct = {data['ct']};\nmaxM = {data['maxM']};"
    original_filename = session.get('original_filename', 'datos')
    dzn_filename = os.path.splitext(original_filename)[0] + '.dzn'
    return Response(dzn_content, mimetype="text/plain", headers={"Content-disposition": f"attachment; filename={dzn_filename}"})

@app.route('/results')
def show_results():
    results = session.get('results', None)
    if not results:
        flash("No hay resultados para mostrar. Por favor, ejecuta el modelo primero.", "info")
        return redirect(url_for('index'))
    return render_template('results.html', results=results)


@app.route('/clear')
def clear_session():
    session.clear()
    flash('Sesión limpiada. Puedes empezar de nuevo.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True, port=8080)