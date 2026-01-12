import commonjs from '@rollup/plugin-commonjs'
import nodeResolve from '@rollup/plugin-node-resolve'
import typescript from '@rollup/plugin-typescript'

export const base = {
    output: {
        //preserveModules: true,
        preserveModulesRoot: '.',
        format: 'es'
    },
    plugins: [
        commonjs(),
        nodeResolve(),
        typescript(),
    ]
}

/**
 * @param  {...string} entrypoints\
 */
export function preserveInputPaths(...entrypoints) {
    return Object.fromEntries(
        entrypoints.map(e => [e.slice(0, e.length - '.ts'.length), e])
    )
}