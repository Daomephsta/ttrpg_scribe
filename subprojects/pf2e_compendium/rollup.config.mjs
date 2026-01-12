import { base, preserveInputPaths } from '../../rollup.base.mjs'

export default {
    input: preserveInputPaths(
        './ttrpg_scribe/pf2e_compendium/flask/static/search.ts',
        './ttrpg_scribe/pf2e_compendium/flask/static/analyse_creature.ts',
        './ttrpg_scribe/pf2e_compendium/oracle/static/oracle/encounter.ts',
    ),
    ...base
}