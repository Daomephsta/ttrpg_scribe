---
layout: session
---
{% from 'creature.j2.html' import stat_block %}
{% from 'encounter.j2.html' import encounter %}
{% from 'npc_link.j2.html' import npc_link %}
# Foo
{{ npc_link('Silifrey Buckman') }}
{{ encounter([(1, script.CHICKEN)]) }}
{{ stat_block(script.CHICKEN) }}