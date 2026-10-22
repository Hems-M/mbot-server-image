# MBot terminal theme: University of Michigan maize and blue, the same palette as the
# ROBuntu tools (maize #FFCB05, Michigan blue #00274C; green only for success).
# Sourced by mbot-help and mbot. Installed to /opt/mbot/lib/mbot-theme.sh.
# Colours only on a real terminal; NO_COLOR=1 or a pipe gives plain text.
# shellcheck shell=bash

if [[ -t 1 && "${TERM:-dumb}" != "dumb" && -z "${NO_COLOR:-}" ]]; then
    MAIZE=$'\e[38;2;255;203;5m'
    BLUE_BG=$'\e[48;2;0;39;76m'
    BODY=$'\e[38;2;248;249;250m'
    SOFT=$'\e[38;2;190;199;211m'
    GREEN=$'\e[38;5;84m'
    BOLD=$'\e[1m'
    RESET=$'\e[0m'
else
    MAIZE="" BLUE_BG="" BODY="" SOFT="" GREEN="" BOLD="" RESET=""
fi

UI_WIDTH="$(tput cols 2>/dev/null || echo 80)"
[[ "$UI_WIDTH" =~ ^[0-9]+$ ]] || UI_WIDTH=80
((UI_WIDTH > 96)) && UI_WIDTH=96
((UI_WIDTH < 60)) && UI_WIDTH=60

# A full-width Michigan-blue row with maize text.
blue_row() {
    if [[ -n "$BLUE_BG" ]]; then
        printf '%s%*s\r%s%s%s\n' "$BLUE_BG" "$UI_WIDTH" '' "$BLUE_BG$1" "$2" "$RESET"
    else
        printf '%s\n' "$2"
    fi
}

mbot_banner() {
    blue_row "$MAIZE" ''
    blue_row "$MAIZE$BOLD" "  MBOT  |  UNIVERSITY OF MICHIGAN ROBOTICS"
    blue_row "$MAIZE" "  $1"
    blue_row "$MAIZE" ''
}

# Section heading: maize bar, NAME, short description.
section() {
    printf '\n%s▌%s %s%-10s%s %s%s%s\n' "$MAIZE" "$RESET" "$MAIZE$BOLD" "$1" "$RESET" "$SOFT" "$2" "$RESET"
}

# One command and what it does. Long commands get the description on the next line.
cmd() {
    local command="$1" text="$2" col="${3:-40}"
    if ((${#command} <= col - 2)); then
        printf '    %s%-*s%s %s%s%s\n' "$BODY$BOLD" "$col" "$command" "$RESET" "$SOFT" "$text" "$RESET"
    else
        printf '    %s%s%s\n' "$BODY$BOLD" "$command" "$RESET"
        printf '    %*s %s%s%s\n' "$col" '' "$SOFT" "$text" "$RESET"
    fi
}

note() {
    printf '    %s%s%s\n' "$SOFT" "$1" "$RESET"
}

ok_line() {
    printf '  %s✔%s %s\n' "$GREEN" "$RESET" "$1"
}
