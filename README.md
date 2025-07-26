# Pasos para la ejecución

1. Crear y activar el entorno virtual de Python

- **En Linux/macOS:**

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

- **En Windows:**

   ```powershell
   python3 -m venv venv
   venv\Scripts\activate
   ```

2. Instalar los requerimientos

   ```bash
   pip install -r requirements.txt
   ```
3. Ejecutar el programa
   ```bash
   python run.py
   ```

4. Binario de Minizic

   Si al ejecutar en consola 
   ```bash
   minizinc
   ```
   no se obtiene respuesta del comando encontrado, se debe especificar en el archivo **.env** la variable **MINIZINC_BIN_PATH** que apunte al ejecutable de minizinc. 

   
**Nota:** Es necesario contar con Minizinc en su sistema para una correcta ejecución del programa