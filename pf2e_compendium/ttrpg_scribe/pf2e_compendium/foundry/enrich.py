import itertools
import re
from collections.abc import Set
from typing import overload

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


def consume_options(args: Args):
    KNOWN = {
        'area-damage', 'area-effect', 'bedside-manner', 'crosstalk', 'damaging-effect',
        'disable-bloodmoon', 'fall-damage', 'forced-movement', 'mid-air-collision',
        'mind-if-i-borrow-that', 'natures-patient-healing', 'nobles-ally', 'siege-weapon',
        'spotlight-ready', 'sweeping-spell', 'youre-next'
    }

    def is_known(option: str):
        return option in KNOWN or option.startswith(('action:', 'inflicts:', 'item:'))
    options = args.consume_set('options')
    unknown = {option for option in options if not is_known(option)}
    assert len(unknown) == 0, f'Unknown options {unknown}'
    return options


def consume_traits(args: Args):
    # TODO: Look into these more
    NOT_REALLY_TRAITS = {
        'area-damage', 'cold-iron', 'compulsion', 'controlling', 'custom', 'damaging-effect',
        'interact', 'keyboard', 'manipulate', 'poison:xulgath-bile', 'skill', 'slashing', 'spell',
        'trip-tangle'
    }
    KNOWN = {
        'abjuration', 'acid', 'air', 'alchemical', 'amphibious', 'arcana', 'arcane', 'attack',
        'auditory', 'aura', 'beast', 'chaotic', 'charm', 'cold', 'complex', 'concentrate',
        'conjuration', 'contact', 'curse', 'darkness', 'death', 'disarm', 'disease', 'divination',
        'divine', 'earth', 'electricity', 'emotion', 'enchantment', 'environmental', 'evocation',
        'exploration', 'fear', 'fey', 'fire', 'force', 'fungus', 'good', 'grippli', 'haunt',
        'hazard', 'holy', 'humanoid', 'illusion', 'incapacitation', 'inhaled', 'injury', 'kaiju',
        'light', 'linguistic', 'magical', 'manipulate', 'mechanical', 'mental', 'misfortune',
        'move', 'necromancy', 'nonlethal', 'occult', 'olfactory', 'poison', 'polymorph',
        'possession', 'primal', 'rare', 'secret', 'shadow', 'sleep', 'sonic', 'swarm',
        'teleportation', 'transmutation', 'trap', 'trip', 'uncommon', 'unholy', 'unique',
        'virulent', 'visual', 'vitality', 'void', 'water'
    } | NOT_REALLY_TRAITS

    def is_known(trait: str):
        return trait in KNOWN or trait.startswith(('action:', 'item:'))
    traits = args.consume_set('traits')
    unknown = {trait for trait in traits if not is_known(trait)}
    assert len(unknown) == 0, f'Unknown traits {unknown}'
    return traits


_STATISTIC_ID = itertools.count(1)


def _statistic_span(text: str, htmlClass: str):
    attrs = {
        'class': f'statistic-{htmlClass}',
        'id': f'statistic-{htmlClass}-{next(_STATISTIC_ID)}'
    }
    attrs_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
    return f'<span {attrs_str}>{text}</span>'


def _damage_roll(args: Args) -> str:
    def strip_delimiters(s: str, prefix: str, suffix: str):
        if s.startswith(prefix) and s.endswith(suffix):
            return s[len(prefix):-len(suffix)]
        return s

    buf = []
    args.ignore('immutable', 'name')
    consume_options(args)
    consume_traits(args)
    damage = args.consume_index(0)
    for part in re.split(r',(?![A-z])', damage):
        amountEnd = part.rfind('[')
        amount = strip_delimiters(part[:amountEnd], '(', ')')
        damage_types = strip_delimiters(part[amountEnd:], '[', ']').split(',')
        if 'healing' in damage_types:  # healing "damage type" shouldn't be included in output
            damage_types.remove('healing')
        if '[splash]' in amount:
            amount = amount.removesuffix('[splash]')
            damage_types.append('splash')
        if args.consume_bool('shortLabel') or damage_types == []:
            buf.append(_statistic_span(amount, 'damage-dice'))
        else:
            buf.append(f'{_statistic_span(amount, 'damage-dice')} {" ".join(damage_types)}')
    return _statistic_span(' plus '.join(buf), 'damage')


def enrich(text: str) -> str:
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
                    args.ignore('damaging')
                    consume_options(args)
                    consume_traits(args)
                    shape = args.consume_str('type') or args.consume_index(0)
                    distance = args.consume_str('distance')
                    if shape == 'line' and (width := args.consume_str('width')) is not None:
                        return f'{distance}-foot ({width}-foot wide) {shape}'
                    return f'{distance}-foot {shape}'
            case 'Check':
                with parse_args(raw_args, context='@Check') as args:
                    args.ignore('against', 'defense', 'immutable', 'name', 'overrideTraits',
                                'rollerRole', 'showDC')
                    consume_options(args)
                    consume_traits(args)
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
                    return _damage_roll(args)
            case unknown:
                raise ValueError(f'Unknown enricher @{unknown}[{raw_args}]')

    def inline_enrichers(result: re.Match) -> str:
        def parse_inline_args(args: str, *, context: str) -> tuple[Args, str]:
            args, _, tag = args.partition('#')
            return Args(args.strip(), arg_sep=' ', key_value_sep='=', error_context=context), tag
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
                    consume_options(args)
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
    text = re.sub(r'\[\[\/(?P<name>\w+) (?P<args>[^]]+)\]\](?:\{(?P<display>[\w ]+?)\})?',
                  inline_enrichers, text)
    return text


if __name__ == '__main__':
    import logging
    import sys
    _LOGGER = logging.getLogger(__name__)
    _LOGGER.info(f'{enrich(sys.argv[1])}\n')
