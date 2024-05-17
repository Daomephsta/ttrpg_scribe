---
layout: session
extra_stylesheets: ['/encounter/compendium/static/stat_block.css']
---
{% from 'creature.j2.html' import stat_block %}
{% from 'encounter.j2.html' import encounter %}
{% from 'npc_link.j2.html' import npc_link %}
# Foo
{{ npc_link('Silifrey Buckman') }}
{{ encounter([(10, script.CHICKEN)]) }}
{{ stat_block(script.CHICKEN, collapsible=True) }}