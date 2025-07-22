% MODELO MINIZINC PARA EL PROBLEMA DE MINIMIZAR EL EXTREMISMO (MinExt)

% ---------------------------------------------------------------------------- %
% PARÁMETROS DE ENTRADA
% Estos valores se leerán de un archivo de datos (.dzn).

int: n;                            % Número total de personas
int: m;                            % Número de opiniones posibles
set of int: OPINIONES = 1..m;      % Conjunto de índices para las opiniones

array[OPINIONES] of int: p;        % p[i]: número de personas con opinión inicial i
array[OPINIONES] of float: ext;    % ext[i]: valor de extremismo de la opinión i
array[OPINIONES] of float: ce;     % ce[i]: costo extra por mover a una opinión i inicialmente vacía
array[OPINIONES, OPINIONES] of float: c; % c[i,j]: costo de mover una persona de la opinión i a la j

float: ct;                         % Costo total máximo permitido
int: maxM;                          % Número máximo de movimientos permitidos

% ---------------------------------------------------------------------------- %
% VARIABLES DE DECISIÓN
% El solver encontrará los valores óptimos para estas variables.

% x[i,j]: número de personas que se mueven de la opinión i a la opinión j.
% El valor x[i,i] representa el número de personas que se quedan en la opinión i.
array[OPINIONES, OPINIONES] of var 0..n: x;

% ---------------------------------------------------------------------------- %
% VARIABLES AUXILIARES

% p_final[j]: número total de personas que tendrán la opinión j en la distribución final.
array[OPINIONES] of var 0..n: p_final;

% Variables auxiliares para acceso desde Python
var float: total_cost;
var int: total_moves;

% ---------------------------------------------------------------------------- %
% RESTRICCIONES
% Reglas que toda solución factible debe cumplir.

% Restricción 1: Conservación de las personas.
% El número total de personas que salen de una opinión i (ya sea para moverse a
% otra opinión o para quedarse) debe ser igual al número de personas que
% originalmente tenían esa opinión.
constraint forall(i in OPINIONES) (
  sum(j in OPINIONES) (x[i,j]) = p[i]
);

% Restricción 2: Cálculo de la población final.
% La población final de una opinión j es la suma de todas las personas que se
% movieron hacia ella desde cualquier opinión i.
constraint forall(j in OPINIONES) (
  p_final[j] = sum(i in OPINIONES) (x[i,j])
);

% Restricción 3: Definir variable de costo total
constraint total_cost = sum(i, j in OPINIONES where i != j) (
  % Costo base del movimiento
  c[i,j] * (1.0 + p[i] / n) * x[i,j] +
  % Costo extra si la opinión de destino 'j' estaba inicialmente vacía
  (if p[j] = 0 then ce[j] * x[i,j] else 0.0 endif)
);

% Restricción 4: Límite máximo de costo total.
constraint total_cost <= ct;

% Restricción 5: Definir variable de movimientos totales
constraint total_moves = sum(i, j in OPINIONES) (abs(i-j) * x[i,j]);

% Restricción 6: Límite máximo de movimientos.
constraint total_moves <= maxM;

% ---------------------------------------------------------------------------- %
% FUNCIÓN OBJETIVO
% El valor que queremos minimizar.

% Objetivo: Minimizar el extremismo total de la población final.
% Se calcula como la suma ponderada del número de personas en cada opinión
% final por el valor de extremismo de esa opinión.
solve minimize sum(j in OPINIONES) (p_final[j] * ext[j]);

% ---------------------------------------------------------------------------- %
% SALIDA

output [
  "--- Solución Óptima Encontrada ---\n",
  "Matriz de movimientos (x[i,j]):\n" ++ show2d(x) ++ "\n",
  "Distribución final de la población (p_final):\n" ++ show(p_final) ++ "\n",
  "Costo total de la solución: ", show(total_cost), "\n",
  "Movimientos totales: ", show(total_moves), "\n",
  "Extremismo total final: ", show(sum(j in OPINIONES) (p_final[j] * ext[j])), "\n"
];