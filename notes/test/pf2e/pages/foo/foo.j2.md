---
layout: article
---
{% from 'creature.j2.html' import creature %}
{% from 'encounter.j2.html' import encounter %}
{% from 'npc_link.j2.html' import npc_link %}
# Foo
{{ npc_link('Silifrey Buckman') }}
{{ encounter([(10, script.CHICKEN)]) }}
{{ creature(script.CHICKEN, collapsible=True) }}