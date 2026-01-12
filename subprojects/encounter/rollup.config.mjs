import { base, preserveInputPaths } from '../../rollup.base.mjs'

export default {
    input: preserveInputPaths(
        'ttrpg_scribe/encounter/flask/static/configure_party.ts',
        'ttrpg_scribe/encounter/flask/static/encounter_engine.ts',
        'ttrpg_scribe/encounter/flask/plugin/static/launch_encounter.ts',
    ),
    ...base
}