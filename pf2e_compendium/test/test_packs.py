from ttrpg_scribe.pf2e_compendium.foundry import packs


def test_read_document(test_document):
    packs.read(test_document)
