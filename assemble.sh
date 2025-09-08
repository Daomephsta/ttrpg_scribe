#!/usr/bin/env bash
root=$(pwd)
dest="$root/dist/assemble"

# Clean
pdm cache remove ttrpg_scribe_buildscript*
mkdir -p $dest
rm -r $dest
rm -f $root/dist/ttrpg_scribe-*.zip

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
assembled_zip="$root/dist/ttrpg_scribe-$version.zip"
echo "Assembling $assembled_zip"
cd $dest
zip -q $assembled_zip *.whl
cd $root
