import { base, preserveInputPaths } from '../../rollup.base.mjs'

export default {
    input: preserveInputPaths(
        'ttrpg_scribe/core/flask/static/popup.ts',
    ),
	...base
}