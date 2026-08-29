import itertools
import math
import operator
from collections import defaultdict
from dataclasses import dataclass
from functools import reduce
from typing import Any, NamedTuple, Self, override

from lark import Lark, Transformer, v_args
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
    def ensure(damage) -> 'DamageInstance':
        if isinstance(damage, int):
            return DamageInstance(damage)
        return damage

    def flavour(self, *category: str) -> Self:
        for _, existing in self.dice:
            existing.extend(category)
        return self

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

    @override
    def __str__(self) -> str:
        def helper(dice: list[SimpleDice | int], damage_types: list[str]):
            amount = f'<span class="damage-dice">{' + '.join(map(str, dice))}</span>'
            return f'{amount}' if self.shortLabel else f'{amount} {' '.join(damage_types)}'
        return ' + '.join(helper(dice, damage_types) for dice, damage_types in self.dice)


class RollTransformer(Transformer):
    def __init__(self, context: dict[str, Any]) -> None:
        super().__init__(visit_tokens=True)
        self.context = context

    class Tag[T](NamedTuple):
        name: str
        value: T

    @classmethod
    def args_by_tags(cls, children: list[Any], tags: list[str]):
        tagged_args = {t.name: t.value for t in children if isinstance(t, cls.Tag)}
        return [tagged_args.get(t) for t in tags]

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

    @v_args(inline=True)
    def dice_term(self, count: int, size: int, *other):
        return self._modifiers_flavour(DamageInstance(count * d(size)), other)

    @v_args(inline=True)
    def die_term(self, size: int, *other):
        return self._modifiers_flavour(DamageInstance(d(size)), other)

    def data_reference(self, path: list[str]):
        return reduce(lambda a, b: a[b], path, initial=self.context)

    @v_args(inline=True)
    def flavoured_expression(self, damage, flavour):
        return DamageInstance.ensure(damage).flavour(*flavour.value)

    def pool(self, children):
        damage = reduce(lambda a, b: a + b, itertools.takewhile(lambda c: isinstance(c, DamageInstance), children))
        return self._modifiers_flavour(damage, children)

    @v_args(inline=True)
    def flavoured_number(self, number, flavour):
        return DamageInstance(number, flavour.value)

    def flavour(self, children) -> 'RollTransformer.Tag[list[str]]':
        return self.Tag('flavour', [str(t) for t in children])

    IDENTIFIER = str
    def MODIFIERS(self, modifiers):
        return self.Tag('modifiers', modifiers)

    def SIGNED_NUMBER(self, child):
        return float(child) if '.' in child else int(child)

    def _modifiers_flavour(self, damage: DamageInstance, children):
        modifiers, flavour = self.args_by_tags(children, ['modifiers', 'flavour'])
        if modifiers is not None:
            raise NotImplementedError('Dice modifiers')
        if flavour is not None:
            damage.flavour(*flavour)
        return damage
