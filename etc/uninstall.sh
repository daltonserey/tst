# mv old .tst directory
rm -rf ~/.tst

# comment out tst PATH settings in rc files
FILES=(~/.bashrc ~/.profile ~/.bash_profile)
for file in ${FILES[@]}; do
    [[ -f "$file" ]] && sed -i~ "/configures PATH and PYTHONPATH for TST/d" $file
    [[ -f "$file" ]] && sed -i~ "/tst.paths.inc/d" $file
    [[ -f "$file" ]] && sed -i~ "/configures completion for TST/d" $file
    [[ -f "$file" ]] && sed -i~ "/tst.completion.inc/d" $file
done
