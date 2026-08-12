---
layout: article
---
{% from 'creature.j2.html' import creature %}
{% from 'encounter.j2.html' import encounter %}
{% from 'npc_link.j2.html' import npc_link %}
# Foo
{{ npc_link('Silifrey Buckman') }}
{{ encounter([
    (3, 'pathfinder-monster-core/eagle'),
    (1, 'pathfinder-monster-core/eagle', {'name': 'Super Chicken', 'adjustment': 'elite', 'initiative': 'arcana'}),
    (2, script.CHICKEN)])
}}
{{ creature(script.CHICKEN, collapsible=True) }}