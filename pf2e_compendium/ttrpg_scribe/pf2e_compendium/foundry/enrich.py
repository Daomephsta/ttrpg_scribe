import ast
import itertools
import math
import operator
import re
from ast import Name
from collections import defaultdict
from collections.abc import Set
from dataclasses import dataclass
from typing import Any, Callable, overload

from ttrpg_scribe.core.dice import SimpleDice, d

from ttrpg_scribe.pf2e_compendium.foundry import i18n


class Args:
    keyed: dict[str, str] = {}
    __match_args__ = ('positional', 'keyed')

    def __init__(self, raw: str, *, arg_sep: str, key_value_sep: str, error_context: str) -> None:
        self.raw = raw
        self.error_context = error_context
        self.keyed = {}
        for arg in raw.split(arg_sep):
            match arg.split(key_value_sep, maxsplit=1):
                case [key, value]:
                    self.keyed[key] = value
                case [arg]:
                    self.keyed[arg] = arg
        self.position_keys = {p: k for p, k in enumerate(self.keyed)}

    def consume_bool(self, key: str, default=False) -> bool:
        value = self.keyed.pop(key, default)
        return value == 'true' or self.__is_positional(key, value)

    def consume_str(self, key: str, default=None) -> str | None:
        return self.keyed.pop(key, default)

    def ignore(self, *keys: str):
        for key in keys:
            self.consume_str(key)

    __sentinel = object()

    @overload
    def consume_index(self, index: int) -> str:
        ...

    @overload
    def consume_index(self, index: int, default: str | None | object = __sentinel) -> str | None:
        ...

    def consume_index(self, index: int, default: str | None | object = __sentinel) -> str | None:
        if default == Args.__sentinel:
            return self.keyed.pop(self.position_keys[index])
        elif key := self.position_keys.get(index):
            assert isinstance(default, str) or default is None
            return self.keyed.pop(key, default)
        return None

    def consume_positional(self):
        for key in self.position_keys.values():
            yield self.keyed.pop(key)

    def consume_set(self, key: str, default: Set[str] = frozenset()) -> Set[str]:
        if value := self.consume_str(key):
            return {e.strip() for e in value.split(',')}
        return default

    def assert_consumed(self):
        keyed = []
        positional = []
        for k, v in self.keyed.items():
            if self.__is_positional(k, v):
                positional.append(k)
            else:
                keyed.append(k)
        assert len(keyed) == 0, f'Unconsumed keys {keyed}'
        assert len(positional) == 0, f'Unconsumed arguments {positional}'

    def __is_positional(self, key, value):
        return key == value

    def __enter__(self):
        return self

    def __exit__(self, e_type: type[Exception] | None, e_value: Exception | None, traceback):
        def notes(e: Exception):
            e.add_note(f'context={self.error_context}')
            e.add_note(f'args={self.raw}')
        if e_value is None:
            try:
                self.assert_consumed()
            except Exception as e:
                notes(e)
                raise
        else:
            notes(e_value)
        return False

    def __str__(self):
        args = ', '.join(k if self.__is_positional(k, v) else f'{k}={v}'
                         for k, v in self.keyed.items())
        return f'Args({args})'


_STATISTIC_ID = itertools.count(1)


def _statistic_span(text: str, htmlClass: str):
    attrs = {
        'class': f'statistic-{htmlClass}',
        'id': f'statistic-{htmlClass}-{next(_STATISTIC_ID)}'
    }
    attrs_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
    return f'<span {attrs_str}>{text}</span>'


def _damage_roll(args: Args, context: dict[str, Any]) -> str:
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
                amount = _statistic_span(' + '.join(map(str, dice)), 'damage-dice')
                return f'{amount}' if self.shortLabel else f'{amount} {' '.join(damage_types)}'
            return ' + '.join(helper(dice, damage_types) for dice, damage_types in self.dice)

    args.ignore('immutable', 'name', 'options', 'traits')
    damage = args.consume_index(0)
    # Transform dice notation to a form parseable as Python code
    damage = re.sub(r'@(actor|item)', lambda m: f'"@{m[1]}"', damage)
    damage = re.sub(r'(\(.+\)|\d+)?d(\(.+\)|\d+)',
                    lambda m: f'd({m[1] or 1}, {m[2]})', damage)
    try:
        expr = ast.parse(damage, mode='eval')
    except SyntaxError:
        return _statistic_span(damage, 'damage')

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
                    resolved_args = (resolve(arg) for arg in args)
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
    return _statistic_span(str(instance), 'damage')


def enrich(text: str, context: dict[str, Any] = {}) -> str:
    def at_enrichers(result: re.Match) -> str:
        def parse_args(args: str, *, context: str) -> Args:
            return Args(args, arg_sep='|', key_value_sep=':', error_context=context)
        name, raw_args, display = result.groups()
        name: str
        raw_args: str
        if display:
            return display

        match name:
            case 'Localize':
                return enrich(i18n.translate(raw_args))
            case 'UUID':
                return raw_args[raw_args.rindex('.') + 1:]
            case 'Template':
                with parse_args(raw_args, context='@Template') as args:
                    args.ignore('damaging', 'options', 'traits')
                    shape = args.consume_str('type') or args.consume_index(0)
                    distance = args.consume_str('distance')
                    if shape == 'line' and (width := args.consume_str('width')) is not None:
                        return f'{distance}-foot ({width}-foot wide) {shape}'
                    return f'{distance}-foot {shape}'
            case 'Check':
                with parse_args(raw_args, context='@Check') as args:
                    args.ignore('against', 'defense', 'immutable', 'name', 'overrideTraits',
                                'rollerRole', 'showDC', 'options', 'traits')
                    check_type = args.consume_str('type') or args.consume_index(0)
                    basic = args.consume_bool('basic')
                    dc = args.consume_str('dc')
                    match basic, dc:
                        case True, str():
                            return f'DC {dc} basic {check_type.title()}'
                        case False, None:
                            return check_type.title()
                        case False, str():
                            if check_type != 'flat':  # Flat checks aren't level-based statistics
                                dc = _statistic_span(dc, 'dc')
                            else:
                                # Special case check type name for flat checks
                                return f'DC {dc} Flat Check'
                            return f'DC {dc} {check_type.title()}'
                        case True, None:
                            return f'basic {check_type.title()}'
            case 'Damage':
                with parse_args(raw_args, context='@Damage') as args:
                    return _damage_roll(args, context)
            case unknown:
                raise ValueError(f'Unknown enricher @{unknown}[{raw_args}]')

    def inline_enrichers(result: re.Match) -> str:
        name, raw_args, display = result.groups()
        name: str
        raw_args: str
        display: str
        if display:
            return display

        raw_args, _, tag = raw_args.partition('#')
        raw_args = raw_args.strip()
        with Args(raw_args, arg_sep=' ', key_value_sep='=', error_context=f'[[/{name}]]') as args:
            match name:
                case 'r' | 'pr' | 'gmr' | 'br' | 'sr':
                    amount = ' '.join(args.consume_positional())
                    return f'{amount} {tag}' if tag else amount
                case 'act':
                    args.ignore('options')
                    action = args.consume_index(0).replace('-', ' ').title()
                    dc = args.consume_str('dc')
                    statistic = args.consume_str('statistic') or args.consume_str('skill')
                    match dc, statistic:
                        case None, None:
                            return action
                        case None, statistic:
                            return f'{action} ({statistic})'
                        case dc, None:
                            dc = _statistic_span(dc, 'dc')
                            return f'{action} (DC {dc})'
                        case dc, statistic:
                            dc = _statistic_span(dc, 'dc')
                            return f'{action} (DC {dc} {statistic})'
                case _ as name:
                    raise ValueError(f'Unknown enricher {result[0]} ({name=}, {args=})')

    if '<hr />\n' in text:
        text = text.replace('<hr />\n', '<div class="details">')
        text += '</div>'
    text = text.replace('\n', '</br>')
    for pattern in [r'@(Damage)\[((?:[^[\]]*|\[[^[\]]*\])*)\](?:{([^}]+)})?',
                    r'@(\w+)\[([^\]]+)\](?:{([^}]+)})?']:
        text = re.sub(pattern, at_enrichers, text)
    text = re.sub(r'\[\[\/(?P<name>\w+) (?P<args>[^]]+)\]\](?:\{(?P<display>[^}]+?)\})?',
                  inline_enrichers, text)
    return text


if __name__ == '__main__':
    import logging
    import sys
    _LOGGER = logging.getLogger(__name__)
    _LOGGER.info(f'{enrich(sys.argv[1])}\n')
