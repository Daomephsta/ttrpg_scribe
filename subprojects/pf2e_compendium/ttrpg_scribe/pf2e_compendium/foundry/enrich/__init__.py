import re
from typing import Any, Callable

from ttrpg_scribe.core.html import Tag
from ttrpg_scribe.pf2e_compendium.actor import statistics
from ttrpg_scribe.pf2e_compendium.foundry import i18n, mongo_client
from ttrpg_scribe.pf2e_compendium.foundry.enrich.args import Args
from ttrpg_scribe.pf2e_compendium.foundry.enrich.damage import damage_roll


def enrich(text: str, context: dict[str, Any] = {}) -> str:
    def is_effect(s: str):
        return any(s.startswith(prefix) for prefix in ['Spell Effect: ', 'Effect: ', 'Aura: '])

    def enricher(replacer: Callable[[str, str], str | Tag]) -> Callable[[re.Match[str]], str]:
        def wrapper(result: re.Match[str]) -> str:
            name, raw_args, display = result.groups()
            replacement = replacer(name, raw_args)
            if display:
                if is_effect(display):
                    return ''
                match replacement:
                    case str():
                        return display
                    case Tag():
                        replacement.children = [
                            Tag('span', children=replacement.children, style='display: none;'),
                            display
                        ]
                        return str(replacement)
            else:
                replacement = str(replacement)
                if is_effect(replacement):
                    return ''
                return replacement
        return wrapper

    def at_enrichers(name: str, raw_args: str) -> str | Tag:
        match name:
            case 'Localize':
                return enrich(i18n.translate(raw_args))
            case 'UUID':
                return raw_args[raw_args.rindex('.') + 1:]
            case 'Template':
                with Args(raw_args, arg_sep='|', key_value_sep=':',
                          error_context='@Template') as args:
                    args.ignore('damaging', 'name', 'options', 'traits')
                    shape = args.consume_str('type') or args.consume_index(0)
                    distance = args.consume_str('distance')
                    if shape == 'line' and (width := args.consume_str('width')) is not None:
                        return f'{distance}-foot ({width}-foot wide) {shape}'
                    return f'{distance}-foot {shape}'
            case 'Check':
                with Args(raw_args, arg_sep='|', key_value_sep=':',
                          error_context='@Check') as args:
                    args.ignore('against', 'defense', 'immutable', 'inflicts', 'name',
                                'overrideTraits', 'rollerRole', 'showDC', 'options', 'traits')
                    check_type = args.consume_str('type') or args.consume_index(0)
                    basic = args.consume_bool('basic')
                    dc = args.consume_str('dc')
                    if check_type == 'flat':  # Flat checks aren't level-based statistics
                        # Special case check type name for flat checks
                        return f'DC {dc} Flat Check'
                    match basic, dc:
                        case True, str():
                            dc = statistics.inline_html(dc, 'dc')
                            return f'DC {dc} basic {check_type.title()}'
                        case False, None:
                            return check_type.title()
                        case False, str():
                            dc = statistics.inline_html(dc, 'dc')
                            return f'DC {dc} {check_type.title()}'
                        case True, None:
                            return f'basic {check_type.title()}'
            case 'Damage':
                with Args(raw_args, arg_sep='|', key_value_sep=':',
                          error_context='@Damage') as args:
                    return damage_roll(args, context)
            case 'Embed':
                with Args(raw_args, arg_sep=' ', key_value_sep='=',
                          error_context=f'@{name}') as args:
                    uuid = args.consume_index(0)
                    uuid = uuid[uuid.rindex('.') + 1:]
                    inline = args.consume_bool('inline')
                    if not inline:
                        raise NotImplementedError('Only inline @Embed is implemented')
                    doc = mongo_client.get_document('all', uuid, id_type='uuid')
                    desc = enrich(doc['system']['description']['value'])
                    return f'<div class="details">{desc}</div>'
            case _:
                raise ValueError('Unknown enricher')

    def inline_enrichers(name: str, raw_args: str) -> str | Tag:
        raw_args, _, tag = raw_args.partition('#')
        raw_args = raw_args.strip()
        with Args(raw_args, arg_sep=' ', key_value_sep='=',
                  error_context=f'[[/{name}]]') as args:
            match name:
                case 'r' | 'pr' | 'gmr' | 'br' | 'sr':
                    args.ignore('options', 'traits')
                    amount = ' '.join(args.consume_positional())
                    return f'{amount} {tag}' if tag else amount
                case 'act':
                    args.ignore('options', 'traits', 'variant')
                    action = args.consume_index(0).replace('-', ' ').title()
                    dc = args.consume_str('dc')
                    statistic = args.consume_str('statistic') or args.consume_str('skill')
                    match dc, statistic:
                        case None, None:
                            return action
                        case None, statistic:
                            return f'{action} ({statistic})'
                        case dc, None:
                            dc = statistics.inline_html(dc, 'dc')
                            return f'{action} (DC {dc})'
                        case dc, statistic:
                            dc = statistics.inline_html(dc, 'dc')
                            return f'{action} (DC {dc} {statistic})'
                case _:
                    raise ValueError('Unknown enricher')

    if '<hr />\n' in text:
        text = text.replace('<hr />\n', '<div class="details">')
        text += '</div>'
    for pattern in [r'@(Damage)\[((?:[^[\]]*|\[[^[\]]*\])*)\](?:{([^}]+)})?',
                    r'@(\w+)\[([^\]]+)\](?:{([^}]+)})?']:
        text = re.sub(pattern, enricher(at_enrichers), text)
    text = re.sub(r'\[\[\/(?P<name>\w+) (?P<args>[^]]+)\]\](?:\{(?P<display>[^}]+?)\})?',
                  enricher(inline_enrichers), text)
    return text


if __name__ == '__main__':
    import logging
    import sys
    _LOGGER = logging.getLogger(__name__)
    _LOGGER.info(f'{enrich(sys.argv[1])}\n')
