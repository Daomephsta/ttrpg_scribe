import argparse
from ttrpg_scribe.pf2e_compendium.foundry import packs as foundry_packs

parser = argparse.ArgumentParser('python -m ttrpg_scribe.pf2e_compendium.foundry')
parser.add_argument('subcommand', choices=['dir', 'update'])
args = parser.parse_args()

match args.subcommand:
    case 'update':
        foundry_packs.update()
    case 'dir':
        print(foundry_packs.pf2e_dir().as_posix())
