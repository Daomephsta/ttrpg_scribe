---
extra_stylesheets: 
    - {{ url_for('bestiary.static', filename='stat_block.css') }}
---
{% from 'creature.j2.html' import stat_block %}
# Foo

{{ stat_block(script.CHICKEN) }}