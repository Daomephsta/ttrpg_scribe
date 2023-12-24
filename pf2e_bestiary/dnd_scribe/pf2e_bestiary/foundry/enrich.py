import re
from dnd_scribe.pf2e_bestiary.foundry import i18n


def _damage_roll(s: str) -> str:
    buf = []
    for part in re.split(r',(?![A-z])', s):
        amountEnd = part.rindex('[')
        amount = part[:amountEnd].strip('()')
        damage_types = part[amountEnd:].strip('[]').split(',')
        if '[splash]' in amount:
            amount = amount.removesuffix('[splash]')
            damage_types.append('splash')
        buf.append(f'{amount} {" ".join(damage_types)}')
    return ' plus '.join(buf)


def enrich(text: str) -> str:
    def at_enrichers(result: re.Match) -> str:
        name, args, display = result.groups()
        if display:
            return display
        if '|' in args:
            args = dict(arg.split(':') for arg in args.split('|'))
        match name, args:
            case 'Localize', str() as args:
                return enrich(i18n.translate(args))
            case 'UUID', str() as args:
                return args[args.rindex('.') + 1:]
            case 'Template', dict() as args:
                return f'{args["distance"]}-foot {args["type"]}'
            case 'Check', dict() as args:
                if 'basic' in args:
                    return f'DC {args["dc"]} basic {args["type"].title()}'
                return f'DC {args["dc"]} {args["type"].title()}'
            case 'Damage', str() as args:
                return _damage_roll(args)
        print(f'Unknown enricher {name} with args {args}')
        return result[0]

    def inline_enrichers(result: re.Match) -> str:
        amount, tag, display = result.groups()
        if display:
            return display
        if tag:
            return f'{amount} {tag}'
        return amount

    text = text.replace('<hr />\n', '<hr class="intrasection"/>')
    text = text.replace('\n', '</br>')
    for pattern in [r'@(Damage)\[((?:[^[\]]*|\[[^[\]]*\])*)\](?:{([^}]+)})?',
                    r'@(\w+)\[([^\]]+)\](?:{([^}]+)})?']:
        text = re.sub(pattern, at_enrichers, text)
    text = re.sub(r'\[\[\/b?r ([0-9]+d[0-9]+)(?:\[\w+\])?(?: #([\w ]+))?\]\](?:\{([\w ]+?)\})?',
                  inline_enrichers, text)
    return text
