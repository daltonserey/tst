# add completion facilities to TST
_tst_completion() 
{
    local commands current config
    commands="version help login checkout commit test"
    config=~/.tst/config.json
    COMPREPLY=()
    current="${COMP_WORDS[COMP_CWORD]}"

    # complete command itself
    if [[ $COMP_CWORD == 1 ]]; then
        COMPREPLY=( $(compgen -W "$commands" -- ${current}) )
        return 0
    fi

    # identify command
    command="${COMP_WORDS[1]}"

    # complete login (only one arg)
    if [[ "$command" == "login" ]] && [[ $COMP_CWORD == 2 ]]; then
        [[ -f $config ]] && email=$(grep email $config | cut -f 4 -d '"')
        COMPREPLY=($(compgen -W "${email}" -- ${current}))
        return 0
    fi

    # complete commit or test
    if [[ "$command" == "commit" ]] || [[ "$command" == "test" ]]; then
        if [[ -z "$TST_COMPLETION_FILTER" ]]; then
            COMPREPLY=($( compgen -f "${current}"))
        else
            COMPREPLY=($( compgen -f "${current}" | grep -Ev "$TST_COMPLETION_FILTER"))
        fi
        return 0
    fi
}
complete -F _tst_completion tst
