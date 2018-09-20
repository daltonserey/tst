#!/usr/bin/env bash
# TST completion script (to be sourced or eval)
# (C) 2018 Dalton Serey / UFCG

# add completion facilities to TST
if [[ ! -z "$TST_COMPLETION_STATUS" ]]; then
    unset -f _tst_completion
    unset TST_COMPLETION_STATUS
else
    _tst_completion() 
    {
        local commands current config
        commands="version help login checkout commit test update"
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

        # complete update (only one arg)
        if [[ "$command" == "update" ]] && [[ $COMP_CWORD == 2 ]]; then
            [[ -f $config ]] && email=$(grep email $config | cut -f 4 -d '"')
            COMPREPLY=($(compgen -W "--pre-release" -- ${current}))
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
    export TST_COMPLETION_STATUS="ON"
fi
