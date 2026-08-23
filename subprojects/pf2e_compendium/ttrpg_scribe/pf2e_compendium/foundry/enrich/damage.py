import itertools
import math
import operator
import re
from ast import Name
from collections import defaultdict
from dataclasses import dataclass
from functools import reduce
from os import wait
from typing import Any

from lark import Lark, Token, Transformer, Tree, v_args
from requests_cache import Callable
from ttrpg_scribe.core.dice import SimpleDice, d

from ttrpg_scribe.pf2e_compendium.actor import statistics
from ttrpg_scribe.pf2e_compendium.foundry.enrich.args import Args

parser = Lark.open_from_package(__name__, 'damage.lark', start='expressions')

def damage_roll(args: Args, context: dict[str, Any]):
    args.ignore('immutable', 'name', 'options', 'traits')
    damage = args.consume_index(0)
    try:
        damage = DamageInstance.ensure(RollTransformer(context).transform(parser.parse(damage)))
    except Exception as e:
        e.add_note(f'parse_input={damage}')
        raise e
    damage.shortLabel = args.consume_bool('shortLabel')
    return statistics.inline_html(str(damage), 'damage')

@dataclass
class DamageInstance:
    dice: list[tuple[list[SimpleDice | int], list[str]]]
    shortLabel: bool

    def __init__(self, dice: SimpleDice | int, categories: list[str] | None = None):
        self.dice = [([dice], [] if categories is None else categories)]
        self.shortLabel = False

    @staticmethod
    def ensure(damage) -> DamageInstance:
        if isinstance(damage, int):
            return DamageInstance(damage)
        return damage

    def add_category(self, *category: str):
        for _, existing in self.dice:
            existing.extend(category)

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


class RollTransformer(Transformer):
    def __init__(self, context: dict[str, Any]) -> None:
        super().__init__(visit_tokens=True)
        self.context = context

    def expressions(self, children: list[DamageInstance]):
        return reduce(lambda a, b: a + b, children)

    @v_args(inline=True)
    def expression(self, head, *tail):
        return reduce(lambda acc, op: op(acc), tail, initial=head)

    @v_args(inline=True)
    def add(self, right):
        return lambda acc: acc + right

    @v_args(inline=True)
    def sub(self, right):
        return lambda acc: acc - right

    @v_args(inline=True)
    def term(self, head, *tail):
        return reduce(lambda acc, op: op(acc), tail, initial=head)

    @v_args(inline=True)
    def mul(self, right):
        return lambda acc: acc * right

    @v_args(inline=True)
    def div(self, right):
        return lambda acc: acc / right

    @v_args(inline=True)
    def function_term(self, name, *args):
        match name:
            case 'min':
                return min(*args)
            case 'max':
                return max(*args)
            case 'floor':
                return math.floor(*args)
            case 'ceil':
                return math.ceil(*args)
            case 'ternary':
                cond, if_true, if_false = args
                return if_true if cond else if_false
            case 'gte':
                return operator.ge(*args)
            case 'lte':
                return operator.le(*args)
            case unknown:
                raise SyntaxError(f'Unknown function {unknown}')


    def dice_term(self, children):
        match children[:2]:
            case int() as count, int() as size:
                damage = DamageInstance(count * d(size))
            case int() as size, *_:
                damage = DamageInstance(1 * d(size))
            case _:
                raise ValueError(f'Unexpected children {children}')
        return self._modifiers_flavour(damage, children)

    def data_reference(self, path: list[str]):
        return reduce(lambda a, b: a[b], path, initial=self.context)

    @v_args(inline=True)
    def grouping(self, damage, flavour):
        damage = DamageInstance.ensure(damage)
        damage.add_category(*flavour)
        return damage

    def pool(self, children):
        damage = reduce(lambda a, b: a + b, itertools.takewhile(lambda c: isinstance(c, DamageInstance), children))
        return self._modifiers_flavour(damage, children)

    @v_args(inline=True)
    def flavoured_number(self, number, flavour):
        return DamageInstance(number, flavour)

    def flavour(self, children):
        return [str(t) for t in children]

    IDENTIFIER = str
    MODIFIERS = str

    def SIGNED_NUMBER(self, child):
        return float(child) if '.' in child else int(child)

    def _modifiers_flavour(self, damage: DamageInstance, children):
        match children:
            case *_, str() as modifiers, list() as flavour:
                damage.add_category(*flavour)
                raise NotImplementedError('Dice modifiers')
            case *_, str() as modifiers:
                raise NotImplementedError('Dice modifiers')
            case *_, list() as flavour:
                damage.add_category(*flavour)
        return damage
