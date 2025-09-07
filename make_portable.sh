root=$(pwd)
dest="$root/dist/portable"

# Clean
pdm cache remove ttrpg_scribe_buildscript*
mkdir -p $dest
rm -r $dest
rm -f $root/dist/ttrpg_scribe_portable-*.zip

# Build artifacts
for project in . core dnd_bestiary encounter notes npc pf2e_compendium;
do echo "Building $project";
    cd $project;
    rm -rf .pdm-plugins
    pdm install --plugins;
    pdm build --no-clean -d $dest;
    cd $root
done

# Assemble
base=$(basename -s .whl $dest/ttrpg_scribe-*.whl)
version=${base/ttrpg_scribe-/}
portable_zip="$root/dist/ttrpg_scribe_portable-$version.zip"
echo "Assembling $portable_zip"
cd $dest
zip -q $portable_zip *.whl
cd $root
