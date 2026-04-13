
import ast
import itertools
import math
import operator
import re
from ast import Name
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from requests_cache import Callable

from ttrpg_scribe.core.dice import SimpleDice, d
from ttrpg_scribe.pf2e_compendium.actor import statistics
from ttrpg_scribe.pf2e_compendium.foundry.enrich.args import Args


def damage_roll(args: Args, context: dict[str, Any]):
    @dataclass
    class DamageInstance:
        dice: list[tuple[list[SimpleDice | int], list[str]]]
        shortLabel: bool

        def __init__(self, dice: SimpleDice | int):
            self.dice = [([dice], [])]
            self.shortLabel = False

        def add_category(self, category: str):
            for _, existing in self.dice:
                existing.append(category)

        def __bin_op(self, op: Callable[[Any, Any], Any], other):
            match other:
                case DamageInstance():
                    by_type: dict[tuple[str, ...], list[SimpleDice | int]] = defaultdict(list)
                    for dice, damage_types in itertools.chain(self.dice, other.dice):
                        by_type[tuple(damage_types)] += dice
                    self.dice = [(dice, list(damage_types))
                                 for damage_types, dice in by_type.items()]
                    return self
                case int() as result if len(self.dice) == 1 and len(self.dice[0][0]) == 1:
                    dice, categories = self.dice[0]
                    dice[0] = op(dice[0], result)
                    self.dice[0] = (dice, categories)
                    return self
                case _:
                    return NotImplemented

        def __add__(self, other):
            return self.__bin_op(operator.add, other)

        def __radd__(self, other):
            return self + other

        def __sub__(self, other):
            return self.__bin_op(operator.sub, other)

        def __mul__(self, other):
            return self.__bin_op(operator.mul, other)

        def __rmul__(self, other):
            return self * other

        def __truediv__(self, other):
            return self.__bin_op(operator.truediv, other)

        def __str__(self) -> str:
            def helper(dice: list[SimpleDice | int], damage_types: list[str]):
                amount = f'<span class="damage-dice">{' + '.join(map(str, dice))}</span>'
                return f'{amount}' if self.shortLabel else f'{amount} {' '.join(damage_types)}'
            return ' + '.join(helper(dice, damage_types) for dice, damage_types in self.dice)

    args.ignore('immutable', 'name', 'options', 'traits')
    damage = args.consume_index(0)
    # Transform dice notation to a form parseable as Python code
    damage = re.sub(r'@(actor|item)', lambda m: f'"@{m[1]}"', damage)
    damage = re.sub(r'(\w+\(.+\)|\(.+\)|\d+)?d(\(.+\)|\d+)',
                    lambda m: f'd({m[1] or 1}, {m[2]})', damage)
    try:
        expr = ast.parse(damage, mode='eval')
    except SyntaxError:
        return statistics.inline_html(damage, 'damage')

    def to_damage(expr: ast.AST) -> DamageInstance:
        def resolve(node: ast.AST) -> Any:
            match node:
                case ast.Expression(body):
                    return resolve(body)
                case ast.BinOp(left, ast.Add(), right):
                    return resolve(left) + resolve(right)
                case ast.BinOp(left, ast.Sub(), right):
                    return resolve(left) - resolve(right)
                case ast.BinOp(left, ast.Mult(), right):
                    return resolve(left) * resolve(right)
                case ast.BinOp(left, ast.Div(), right):
                    return resolve(left) / resolve(right)
                case ast.Subscript(value, ast.Tuple(damage_types)):
                    instance = to_damage(value)
                    for t in damage_types:
                        instance.add_category(resolve(t))
                    return instance
                case ast.Subscript(value, damage_type):
                    instance = to_damage(value)
                    instance.add_category(resolve(damage_type))
                    return instance
                case ast.Call(Name(func), args):
                    resolved_args: list[Any] = [resolve(arg) for arg in args]
                    # Account for edgecase where resolved args end up in a tuple
                    # in a singleton list for some reaosn
                    match resolved_args:
                        case [tuple() as a]:
                            resolved_args = list(a)
                    match func:
                        case 'd':
                            count, size = resolved_args
                            return DamageInstance(count * d(size))
                        case 'min':
                            return min(*resolved_args)
                        case 'max':
                            return max(*resolved_args)
                        case 'floor':
                            return math.floor(*resolved_args)
                        case 'ceil':
                            return math.ceil(*resolved_args)
                        case 'ternary':
                            cond, if_true, if_false = resolved_args
                            return if_true if cond else if_false
                        case 'gte':
                            return operator.ge(*resolved_args)
                        case 'lte':
                            return operator.le(*resolved_args)
                        case unknown:
                            raise SyntaxError(f'Unknown function {unknown}')
                case Name(id):
                    return id
                case ast.Constant(int() as value):
                    return value
                case ast.Constant(str() as value) if value.startswith('@'):
                    return context[value[1:]]
                case ast.Attribute(value, attr):
                    return resolve(value)[attr]
                case ast.Tuple(elements):
                    return tuple(to_damage(e) for e in elements)
                case n:
                    raise SyntaxError(f'Unexpected node {ast.dump(n, indent=2)}')

        match resolve(expr):
            case DamageInstance() as result:
                return result
            case tuple() as results:
                result = results[0]
                for r in results[1:]:
                    result.dice += r.dice
                return result
            case int() as result:
                return DamageInstance(result)
            case x:
                raise ValueError(f"Can't convert {x} to DamageInstance")

    instance = to_damage(expr)
    instance.shortLabel = args.consume_bool('shortLabel')
    return statistics.inline_html(str(instance), 'damage')
