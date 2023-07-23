---
extra_stylesheets: 
    - {{ url_for('bestiary.static', filename='stat_block.css') }}
---
{% from 'creature.j2.html' import stat_block %}
{% from 'encounter.j2.html' import encounter %}
# Foo

{{ encounter([(1, script.CHICKEN)]) }}