import runpy
import sys

if __name__ == '__main__':
    script_file = sys.argv[1]
    args = dict(arg.split('=') for arg in sys.argv[2:])
    script_members = runpy.run_path(script_file,
        run_name='__ttrpg_script_script__')
    if 'main' not in script_members:
        print('Missing main(args: dict[str, str])')
        sys.exit(-1)
    script_members['main'](args)
