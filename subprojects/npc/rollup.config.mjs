import { base, preserveInputPaths } from '../../rollup.base.mjs'

export default {
    input: preserveInputPaths(
        './ttrpg_scribe/npc/flask_app/static/npc_generator.ts',
    ),
    ...base
}