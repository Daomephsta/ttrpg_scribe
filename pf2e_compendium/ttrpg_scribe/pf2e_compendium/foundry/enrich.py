import re

from ttrpg_scribe.pf2e_compendium.foundry import i18n


def _damage_roll(positional_args: list[str], keyed_args: dict[str, str]) -> str:
    buf = []
    assert len(positional_args) == 1, f'Unexpected positional args {positional_args}'
    unknown_keys = keyed_args.keys() - {'traits', 'name'}
    assert len(unknown_keys) == 0, f'Unknown keys {unknown_keys} in keyed args {keyed_args}'
    for part in re.split(r',(?![A-z])', positional_args[0]):
        amountEnd = part.rfind('[')
        amount = part[:amountEnd].strip('()')
        damage_types = part[amountEnd:].strip('[]').split(',')
        if '[splash]' in amount:
            amount = amount.removesuffix('[splash]')
            damage_types.append('splash')
        buf.append(f'{amount} {" ".join(damage_types)}')
    return ' plus '.join(buf)


def enrich(text: str) -> str:
    def at_enrichers(result: re.Match) -> str:
        name, raw_args, display = result.groups()
        name: str
        raw_args: str
        if display:
            return display

        def parse_args(args: str) -> tuple[list[str], dict[str, str]]:
            positional = []
            keyed = {}
            for arg in args.split('|'):
                match arg.split(':', maxsplit=1):
                    case [key, value]:
                        keyed[key] = value
                    case [positional_arg]:
                        positional.append(positional_arg)
            return positional, keyed

        match name:
            case 'Localize':
                return enrich(i18n.translate(raw_args))
            case 'UUID':
                return raw_args[raw_args.rindex('.') + 1:]
            case 'Template':
                match parse_args(raw_args):
                    case ([shape], {'distance': distance}) |\
                         ([], {'type': shape, 'distance': distance}):
                        return f'{distance}-foot {shape}'
                    case unknown:
                        raise ValueError(f'Unknown @Template enricher args {raw_args} {unknown}')
            case 'Check':
                def only_ignored_keys(keyed_args: dict[str, str]):
                    ignored = {'against', 'defense', 'name', 'overrideTraits', 'traits'}
                    return len(set(keyed_args.keys()) - ignored) == 0
                match parse_args(raw_args):
                    case ([check_type, 'basic'], {'dc': dc}) |\
                         ([], {'basic': True, 'dc': dc, 'type': check_type}):
                        return f'DC {dc} basic {check_type.title()}'
                    case [check_type], {**keyed_args} if only_ignored_keys(keyed_args):
                        return check_type.title()
                    case ([check_type], {'dc': dc}) |\
                         ([], {'dc': dc, 'type': check_type}):
                        return f'DC {dc} {check_type.title()}'
                    case unknown:
                        raise ValueError(f'Unknown @Check enricher args {raw_args} {unknown}')
            case 'Damage':
                return _damage_roll(*parse_args(raw_args))
        raise ValueError(f'Unknown enricher {name} with args {raw_args}')

    def inline_enrichers(result: re.Match) -> str:
        amount, tag, display = result.groups()
        if display:
            return display
        if tag:
            return f'{amount} {tag}'
        return amount

    if '<hr />\n' in text:
        text = text.replace('<hr />\n', '<div class="details">')
        text += '</div>'
    text = text.replace('\n', '</br>')
    for pattern in [r'@(Damage)\[((?:[^[\]]*|\[[^[\]]*\])*)\](?:{([^}]+)})?',
                    r'@(\w+)\[([^\]]+)\](?:{([^}]+)})?']:
        text = re.sub(pattern, at_enrichers, text)
    text = re.sub(r'\[\[\/b?r ([0-9]+d[0-9]+)(?:\[\w+\])?(?: #([\w ]+))?\]\](?:\{([\w ]+?)\})?',
                  inline_enrichers, text)
    return text
