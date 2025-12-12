{% test non_negative(model, column_name) %}

-- Este test debería devolver filas si encuentra valores negativos o nulos en la columna especificada.
select
    {{ column_name }}
from {{ model }}
where {{ column_name }} < 0 or {{ column_name }} is null

{% endtest %}
