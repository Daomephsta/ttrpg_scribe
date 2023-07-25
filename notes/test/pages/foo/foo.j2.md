---
layout: session
---
{% from 'creature.j2.html' import stat_block %}
{% from 'encounter.j2.html' import encounter %}
# Foo
{{ encounter([(1, script.CHICKEN)]) }}
{{ stat_block(script.CHICKEN) }}