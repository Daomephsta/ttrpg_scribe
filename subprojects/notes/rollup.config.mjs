import { base, preserveInputPaths } from '../../rollup.base.mjs'

export default {
    input: preserveInputPaths(
        'ttrpg_scribe/notes/static/toc.ts',
    ),
	...base
}