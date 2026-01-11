import typescript from '@rollup/plugin-typescript';

export const base = {
    output: {
        preserveModules: true,
        preserveModulesRoot: '.',
        format: 'es'
    },
    plugins: [
        typescript()
    ]
}