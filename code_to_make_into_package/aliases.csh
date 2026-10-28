##########################################################################################
function op_fix_2nd_display()
{
    echo "Fixing 2nd display by purging and reinstalling NVIDIA drivers..."
    echo ""
    echo "Current driver status:"
    nvidia-smi 2>&1 | head -5
    echo ""

    echo "Step 1: Purging all NVIDIA packages..."
    sudo apt purge nvidia-* libnvidia-* -y
    if [[ $? -ne 0 ]]; then
        echo "ERROR: Failed to purge NVIDIA packages" >&2
        return 1
    fi

    echo ""
    echo "Step 2: Removing unused dependencies..."
    sudo apt autoremove -y

    echo ""
    echo "Step 3: Updating package lists..."
    sudo apt update

    echo ""
    echo "Step 4: Installing recommended NVIDIA driver..."
    sudo ubuntu-drivers install nvidia-driver-580-open

    if [[ $? -eq 0 ]]; then
        echo ""
        echo "Driver installed successfully!"
        echo "Rebooting in 5 seconds..."
        sleep 5
        sudo reboot
    else
        echo ""
        echo "Driver installation failed. Try manually:"
        echo "  ubuntu-drivers devices  # to see available drivers"
        echo "  sudo ubuntu-drivers install <driver-name>"
        return 1
    fi
}
##########################################################################################


##########################################################################################
function _op_get_optimal_threads_test()
{
    if [[ -f .pytest_optimal_threads ]]; then
        local cached_threads=$(cat .pytest_optimal_threads)
        if [[ -n "$cached_threads" ]]; then
            echo "$cached_threads"
            return 0
        fi
    fi

    echo "0"
}

function _op_get_optimal_threads_coverage()
{
    if [[ -f .pytest_optimal_threads_coverage ]]; then
        local cached_threads=$(cat .pytest_optimal_threads_coverage)
        if [[ -n "$cached_threads" ]]; then
            echo "$cached_threads"
            return 0
        fi
    fi

    echo "0"
}

function op_test_tune_threads()
{
    echo "=========================================="
    echo "Tuning optimal thread count for pytest..."
    echo "System has $(nproc) CPU cores"
    echo "=========================================="

    local cpu_cores=$(nproc)

    local thread_counts=(1 2 4 8)

    if [[ $cpu_cores -ge 8 ]]; then
        thread_counts+=(12)
    fi
    if [[ $cpu_cores -ge 16 ]]; then
        thread_counts+=(16)
    fi
    if [[ $cpu_cores -ge 24 ]]; then
        thread_counts+=(20 24)
    fi
    if [[ $cpu_cores -ge 32 ]]; then
        thread_counts+=(28 32)
    fi

    echo "Testing thread counts: ${thread_counts[@]}"
    echo ""

    echo "--- Testing REGULAR pytest ---"
    local best_time_test=999999
    local best_threads_test=1
    local performance_degradation_threshold="1.05"

    for threads in "${thread_counts[@]}"; do
        echo -n "Testing with $threads threads... "

        local total_time=0
        local runs=3

        for ((i=1; i<=runs; i++)); do
            local start_time=$(date +%s.%N)
            uv run pytest -q -n $threads > /dev/null 2>&1
            local end_time=$(date +%s.%N)
            local elapsed=$(echo "$end_time - $start_time" | bc)
            total_time=$(echo "$total_time + $elapsed" | bc)
        done

        local avg_time=$(echo "scale=2; $total_time / $runs" | bc)
        echo "Average time: ${avg_time}s"

        if (( $(echo "$avg_time < $best_time_test" | bc -l) )); then
            best_time_test=$avg_time
            best_threads_test=$threads
        else
            local threshold_time=$(echo "scale=2; $best_time_test * $performance_degradation_threshold" | bc)
            if (( $(echo "$avg_time > $threshold_time" | bc -l) )); then
                echo "  Performance degradation detected. Stopping regular test tuning."
                break
            fi
        fi
    done

    echo ""
    echo "--- Testing pytest with COVERAGE ---"
    local best_time_cov=999999
    local best_threads_cov=1

    for threads in "${thread_counts[@]}"; do
        echo -n "Testing with $threads threads... "

        local total_time=0
        local runs=2

        for ((i=1; i<=runs; i++)); do
            local start_time=$(date +%s.%N)
            uv run pytest -q --cov --cov-report= -n $threads > /dev/null 2>&1
            local end_time=$(date +%s.%N)
            local elapsed=$(echo "$end_time - $start_time" | bc)
            total_time=$(echo "$total_time + $elapsed" | bc)
        done

        local avg_time=$(echo "scale=2; $total_time / $runs" | bc)
        echo "Average time: ${avg_time}s"

        if (( $(echo "$avg_time < $best_time_cov" | bc -l) )); then
            best_time_cov=$avg_time
            best_threads_cov=$threads
        else
            local threshold_time=$(echo "scale=2; $best_time_cov * $performance_degradation_threshold" | bc)
            if (( $(echo "$avg_time > $threshold_time" | bc -l) )); then
                echo "  Performance degradation detected. Stopping coverage test tuning."
                break
            fi
        fi
    done

    echo ""
    echo "=========================================="
    echo "RESULTS:"
    echo "Regular pytest: $best_threads_test threads (${best_time_test}s)"
    echo "Coverage pytest: $best_threads_cov threads (${best_time_cov}s)"
    echo "=========================================="

    # Cache the results (use 0 for serial execution with -n 1)
    if [[ $best_threads_test -eq 1 ]]; then
        echo "0" > .pytest_optimal_threads
    else
        echo "$best_threads_test" > .pytest_optimal_threads
    fi

    if [[ $best_threads_cov -eq 1 ]]; then
        echo "0" > .pytest_optimal_threads_coverage
    else
        echo "$best_threads_cov" > .pytest_optimal_threads_coverage
    fi

    echo "Results cached in .pytest_optimal_threads and .pytest_optimal_threads_coverage"

    return 0
}

function _op_is_linux()
{
    [[ "$(uname -s)" == "Linux" ]]
}

function _op_get_pytest_flags()
{
    local num_threads=$(_op_get_optimal_threads_test)
    local include_linux_tests=${1:-false}
    local user_args="${@:2}"

    local pytest_flags=""

    # Add quiet flag or user args
    if [[ -z "$user_args" ]]; then
        pytest_flags="-q --color=yes"
    else
        pytest_flags="$user_args"
    fi

    # Add threading if not already specified
    if [[ "$pytest_flags" != *"-n"* ]] && [[ "$num_threads" != "0" ]]; then
        pytest_flags="$pytest_flags -n $num_threads"
    fi

    # Add Linux test ignore flag if needed
    if [[ "$include_linux_tests" == "false" ]]; then
        pytest_flags="$pytest_flags --ignore=src/op/ui/_test__visualization_events_linux.py"
    fi

    echo "$pytest_flags"
}

function _op_run_format_check_test()
{
    local pytest_flags="$1"
    _op_check_test_naming || return $?
    uvx ruff format 2>&1 | grep -v "files left unchanged"
    uvx ruff check || return $? #  uvx ruff check --fix 2>&1 | grep -v "All checks passed!"
    uv run python src/op/pydantic/main_check.py || return $?
    stdbuf -o0 -e0 uv run python -u -m pytest ${pytest_flags}
}

function _op_test_linux_only()
{
    local pytest_flags="${1:--q}"
    _op_run_format_check_test "$pytest_flags src/op/ui/_test__visualization_events_linux.py"
}

function _op_extract_pytest_summary()
{
    local output="$1"
    echo "$output" | grep -E "^[0-9]+ passed in [0-9]+\.[0-9]+s" | opl -1
}

function _op_test_no_clear()
{
    local include_linux=$(_op_is_linux && echo "true" || echo "false")
    local pytest_flags=$(_op_get_pytest_flags "$include_linux" "${@}")

    # Check if quiet mode (for summary)
    local is_quiet=false
    if [[ "$pytest_flags" == *"-q"* ]] && [[ "$pytest_flags" != *"-vv"* ]]; then
        is_quiet=true
    fi

    if [[ "$is_quiet" == "true" ]]; then
        # Create temp files for capturing summaries
        local main_temp=$(mktemp)
        local linux_temp=$(mktemp)
        local progress_pid_file=$(mktemp)

        # Function to show progress dots (wrap in subshell to suppress job messages)
        {
            {
                while true; do
                    echo -ne "\033[32m.\033[0m"
                    sleep 0.05
                done
            } &
            echo $! > "$progress_pid_file"
        } 2>/dev/null
        local progress_pid=$(cat "$progress_pid_file")

        # Run main tests silently (no output)
        _op_run_format_check_test "$pytest_flags" > "$main_temp" 2>&1
        local main_exit_code=$?

        # Kill progress indicator
        kill $progress_pid 2>/dev/null
        wait $progress_pid 2>/dev/null
        echo ""  # New line after dots

        # Extract main test summary (strip ANSI codes first)
        local main_summary=$(sed 's/\x1b\[[0-9;]*m//g' "$main_temp" | grep -oE "[0-9]+ passed in [0-9]+\.[0-9]+s" | head -1)
        local main_count=$(echo "$main_summary" | grep -oE "^[0-9]+")
        local main_time=$(echo "$main_summary" | grep -oE "[0-9]+\.[0-9]+s" | grep -oE "[0-9]+\.[0-9]+")

        # Check if tests failed (no summary or non-zero exit)
        if [[ $main_exit_code -ne 0 ]] || [[ -z "$main_summary" ]]; then
            # Print error message in red
            echo -e "\033[1;31m✗ Tests failed\033[0m"
            # Cleanup temp files
            rm -f "$main_temp" "$linux_temp" "$progress_pid_file"
            return $main_exit_code
        fi

        if [[ "$include_linux" == "true" ]] && [[ $main_exit_code -eq 0 ]]; then
            # Start progress indicator for Linux tests
            {
                {
                    while true; do
                        echo -ne "\033[32m.\033[0m"
                        sleep 0.05
                    done
                } &
                echo $! > "$progress_pid_file"
            } 2>/dev/null
            local linux_progress_pid=$(cat "$progress_pid_file")

            # Run Linux tests silently
            _op_test_linux_only "$pytest_flags" > "$linux_temp" 2>&1

            # Kill progress indicator
            kill $linux_progress_pid 2>/dev/null
            wait $linux_progress_pid 2>/dev/null
            echo ""  # New line after dots

            # Extract Linux test summary (strip ANSI codes first)
            local linux_summary=$(sed 's/\x1b\[[0-9;]*m//g' "$linux_temp" | grep -oE "[0-9]+ passed in [0-9]+\.[0-9]+s" | head -1)
            local linux_count=$(echo "$linux_summary" | grep -oE "^[0-9]+")
            local linux_time=$(echo "$linux_summary" | grep -oE "[0-9]+\.[0-9]+s" | grep -oE "[0-9]+\.[0-9]+")

            # Calculate totals
            local total_count=$((main_count + linux_count))
            local total_time=$(echo "$main_time + $linux_time" | bc)

            # Print bold green total
            echo -e "\033[1;92m$total_count passed in ${total_time}s\033[0m"
        else
            # Print bold green summary
            echo -e "\033[1;92m$main_summary\033[0m"
        fi

        # Cleanup temp files
        rm -f "$main_temp" "$linux_temp" "$progress_pid_file"

        return $main_exit_code
    else
        # Verbose mode - just run normally
        _op_run_format_check_test "$pytest_flags"
        local main_exit_code=$?

        if [[ "$include_linux" == "true" ]] && [[ $main_exit_code -eq 0 ]]; then
            echo ""
            _op_test_linux_only "$pytest_flags"
        fi

        return $main_exit_code
    fi
}

function op_test()
{
    # Check if we're already in a retry (avoid infinite loop)
    if [[ "$OP_TEST_RETRY" == "1" ]]; then
        clear
        _op_test_no_clear ${@}
        return $?
    fi

    clear
    _op_test_no_clear ${@}
    local exit_code=$?

    # If tests failed and we have no custom args, run verbose mode
    if [[ $exit_code -ne 0 ]] && [[ $# -eq 0 ]]; then
        echo ""
        echo -e "\033[1;31m⚠ Tests failed! Running in verbose mode...\033[0m"
        echo ""
        sleep 1

        # Set flag to prevent infinite loop
        export OP_TEST_RETRY=1
        clear
        op_test_verbose
        local verbose_exit=$?
        unset OP_TEST_RETRY
        return $verbose_exit
    fi

    return $exit_code
}

function op_test_verbose()
{
    if [[ ($# -ne 0) ]]; then
        echo "No parameters should be given" >&2
        return 2
    fi

    local num_threads=$(_op_get_optimal_threads_test)
    if [[ "$num_threads" == "0" ]]; then
        op_test -vv
    else
        op_test -vv -n $num_threads
    fi
}

function op_test_coverage()
{
    if [[ ($# -ne 0) ]]; then
        echo "No parameters should be given" >&2
        return 2
    fi

    local num_threads=$(_op_get_optimal_threads_coverage)
    local pytest_flags=$(_op_get_pytest_flags "false" --cov --cov-report=term-missing)

    if [[ "$num_threads" != "0" ]]; then
        pytest_flags="$pytest_flags -n $num_threads"
    fi

    local coverage_output
    coverage_output=$(_op_run_format_check_test "$pytest_flags" 2>&1)

    local coverage_percentage=$(echo "$coverage_output" | grep "^TOTAL" | awk '{print $4}')

    if [[ "$coverage_percentage" == "100%" ]]; then
        echo -e "\033[1;32m100%\033[0m"
    else
        echo "Coverage: $coverage_percentage"
        echo ""
        echo "============================="
        echo "Files with missing coverage:"
        echo "============================="

        # Extract and display only lines that don't have 100% coverage
        # Look for the coverage table which starts after the test results
        local in_coverage_table=0
        echo "$coverage_output" | while IFS= read -r line; do
            # Check if we've reached the coverage table header
            if [[ "$line" =~ ^Name[[:space:]]+Stmts[[:space:]]+Miss[[:space:]]+Cover ]]; then
                in_coverage_table=1
                continue
            fi

            if [[ "$line" =~ ^---+$ ]]; then
                continue
            fi

            if [[ "$line" =~ ^TOTAL ]]; then
                break
            fi

            # If we're in the coverage table, check for non-100% coverage
            if [[ $in_coverage_table -eq 1 ]] && [[ -n "$line" ]]; then
                # Extract coverage percentage (4th column)
                local file_coverage=$(echo "$line" | awk '{print $4}')
                if [[ "$file_coverage" != "100%" ]] && [[ -n "$file_coverage" ]]; then
                    echo "$line"
                fi
            fi
        done

    fi
}

function _op_test_coverage_verbose()
{
    if [[ ($# -ne 0) ]]; then
        echo "No parameters should be given" >&2
        return 2
    fi

    local num_threads=$(_op_get_optimal_threads_coverage)
    local pytest_flags=$(_op_get_pytest_flags "false" --cov --cov-report=term-missing)

    if [[ "$num_threads" != "0" ]]; then
        pytest_flags="$pytest_flags -n $num_threads"
    fi

    _op_run_format_check_test "$pytest_flags"
}

function _op_test_serial()
{
    clear
    if [[ ($# -eq 0) ]]; then
        pytest_flags=-q
    else
        pytest_flags=${@}
    fi

    _op_check_test_naming; uvx ruff format; uvx ruff check --fix; uv run pytest ${pytest_flags}
}

function _op_test_show_threads()
{
    local num_threads_test=$(_op_get_optimal_threads_test)
    local num_threads_cov=$(_op_get_optimal_threads_coverage)

    echo "Current configuration:"
    if [[ "$num_threads_test" == "0" ]]; then
        echo "  Regular tests: Serial execution"
    else
        echo "  Regular tests: $num_threads_test threads"
    fi

    if [[ "$num_threads_cov" == "0" ]]; then
        echo "  Coverage tests: Serial execution"
    else
        echo "  Coverage tests: $num_threads_cov threads"
    fi

    echo "System CPU cores: $(nproc)"

    if [[ -f .pytest_optimal_threads ]]; then
        echo "Test config source: .pytest_optimal_threads (cached)"
    else
        echo "Test config source: auto-detected"
    fi

    if [[ -f .pytest_optimal_threads_coverage ]]; then
        echo "Coverage config source: .pytest_optimal_threads_coverage (cached)"
    else
        echo "Coverage config source: auto-detected"
    fi

    echo ""
    echo "To reset: rm .pytest_optimal_threads .pytest_optimal_threads_coverage"
    echo "To tune: _op_test_tune_threads"
}

function _op_test_parallel()
{
    local threads=${1:-$(nproc)}
    echo "Running tests with $threads parallel threads..."
    shift
    clear
    _op_check_test_naming; uvx ruff format; uvx ruff check --fix; uv run pytest -q -n $threads ${@}
}
##########################################################################################


##########################################################################################
function op_run()
{
    if [[ ($# -ne 1) ]]; then
        echo "Exactly one parameter should be given" >&2
        echo "Usage: ${FUNCNAME[0]} python_file.py" >&2
        return 2
    fi

    clear
    uv run ${1}
}

function op_run_map_editor()
{
    if [[ ($# -ne 0) ]]; then
        echo "No parameters should be given" >&2
        return 2
    fi

    op_run src/op/main_map_editor.py
}

function op_run_visualize_simulation()
{
    if [[ ($# -ne 0) ]]; then
        echo "No parameters should be given" >&2
        return 2
    fi

    op_run src/op/main_visualize_simulation.py
}
##########################################################################################


##########################################################################################
function op_profile()
{
    if [[ ($# -ne 1) ]]; then
        echo "Exactly one parameter should be given" >&2
        echo "Usage: ${FUNCNAME[0]} python_file.py" >&2
        return 2
    fi

    uv run python -m cProfile -s cumtime ${1}
}
##########################################################################################


##########################################################################################
function op_doc_graphs_create()
{
    uv run python src/op/docs_create/main_mermaid.py
}
##########################################################################################


##########################################################################################
function op_extension_list_create()
{
    code --list-extensions 2>&1 | tee .vscode/extensions_list.txt > /dev/null && echo "Created .vscode/extensions_list.txt with $(wc -l < .vscode/extensions_list.txt) extensions"
}

function op_extension_list_update()
{
    code --list-extensions | xargs -n 1 code --uninstall-extension
    cat .vscode/extensions_list.txt | xargs -n 1 code --install-extension
}
##########################################################################################

##########################################################################################
function _op_install_ssort()
{
    uv tool install ssort
    uv tool update-shell
}

function op_ssort()
{
    local excluded_files=(
        "src/op/geometry/polar_in_respect_to_center.py"
        "src/op/world/world.py"
    )

    echo "========================================================="
    echo "ssort's excluded files:"
    echo "========================================================="
    local grep_pattern=""
    for file in "${excluded_files[@]}"; do
        if [[ -z "$grep_pattern" ]]; then
            grep_pattern="-e \"$file\""
        else
            grep_pattern="$grep_pattern -e \"$file\""
        fi
        echo "$file"
    done
    echo "========================================================="
    echo

    echo "========================================================="
    echo "ssort's output:"
    echo "========================================================="
    local files_to_sort=$(find src/op -type f -name "*.py" | eval grep -v $grep_pattern)
    local file_count=0
    while read -r file; do
        if [[ -n "$file" ]]; then
            ssort "$file" 2>&1 | grep "Sorting"
            ((file_count++))
        fi
    done < <(echo "$files_to_sort")
    echo "Processed $file_count files with ssort"
    echo "========================================================="
    echo

    echo "========================================================="
    echo "op_test's output:"
    echo "========================================================="
    _op_test_no_clear
    echo "========================================================="

}
##########################################################################################


##########################################################################################
function _op_check_test_naming()
{
    if [[ ($# -ne 0) ]]; then
        echo "No parameters should be given" >&2
        return 2
    fi

    local found_errors=0
    local exclude_search_dirs=(".venv" "node_modules" ".git" "__pycache__" ".pytest_cache" ".ruff_cache" "build" "dist")

    local find_exclude_args=""
    for exclude_dir in "${exclude_search_dirs[@]}"; do
        find_exclude_args="$find_exclude_args -path \"./$exclude_dir\" -prune -o"
    done

    while IFS= read -r file; do
        if [[ -n "$file" ]]; then
            echo "ERROR: $file - Test files should be named _test__*.py, not test_*.py" >&2
            ((found_errors++))
        fi
    done < <(eval "find . $find_exclude_args -type f -name 'test_*.py' -print")

    while IFS= read -r file; do
        if [[ -n "$file" && ! "$file" =~ /_test__.*\.py$ ]]; then
            echo "ERROR: $file - Test files should be named _test__*.py, not *_test.py" >&2
            ((found_errors++))
        fi
    done < <(eval "find . $find_exclude_args -type f -name '*_test.py' -print")

    if [[ $found_errors -eq 0 ]]; then
        return 0
    else
        echo "" >&2
        echo "Found $found_errors incorrectly named test file(s)" >&2
        return 1
    fi
}
##########################################################################################


##########################################################################################
function _op_open_presentation_pdf()
{
    local output_file="$1"
    local abs_pdf_path=$(realpath "$output_file")

    # Check if okular is available (preferred)
    if command -v okular &> /dev/null; then
        echo "Opening presentation in Okular..."
        # Try to open Okular in presentation mode
        # Use env -i to clear environment variables that might cause library conflicts
        env -i PATH="$PATH" HOME="$HOME" DISPLAY="$DISPLAY" okular --presentation "$abs_pdf_path" &>/dev/null &
        local okular_pid=$!

        # Check if Okular started successfully
        sleep 0.5
        if ps -p $okular_pid > /dev/null 2>&1; then
            echo "Opened in Okular presentation mode"
            echo "Navigation:"
            echo "  - Page Down/Up or Arrow keys: Navigate slides"
            echo "  - Space/Backspace: Next/Previous slide"
            echo "  - Home/End: First/Last slide"
            echo "  - ESC: Exit presentation mode"
            echo "  - F5: Restart presentation from beginning"
        else
            echo "Okular failed to start (library conflict). Trying alternative viewers..."

            # Try evince as an alternative PDF viewer with presentation mode
            if command -v evince &> /dev/null; then
                echo "Opening in Evince presentation mode..."
                evince --presentation "$abs_pdf_path" &>/dev/null &
                echo "Opened in Evince presentation mode"
                echo "Press F5 to start, F11 for fullscreen, ESC to exit"
            elif command -v google-chrome &> /dev/null; then
                echo "Opening in Chrome..."
                google-chrome --start-fullscreen "file://$abs_pdf_path" &>/dev/null &
                echo "Opened in Chrome presentation mode"
                echo "Press F11 to toggle full screen, ESC to exit"
            else
                xdg-open "$output_file" &>/dev/null &
                echo "Opened with default PDF viewer"
            fi
        fi
    elif command -v google-chrome &> /dev/null; then
        echo "Okular not found. Opening in Chrome..."
        google-chrome --start-fullscreen "file://$abs_pdf_path" &>/dev/null &
        echo "Opened in Chrome presentation mode"
        echo "Press F11 to toggle full screen, ESC to exit"
    elif command -v chromium-browser &> /dev/null; then
        echo "Opening in Chromium..."
        chromium-browser --start-fullscreen "file://$abs_pdf_path" &>/dev/null &
        echo "Opened in Chromium presentation mode"
        echo "Press F11 to toggle full screen, ESC to exit"
    elif command -v chromium &> /dev/null; then
        echo "Opening in Chromium..."
        chromium --start-fullscreen "file://$abs_pdf_path" &>/dev/null &
        echo "Opened in Chromium presentation mode"
        echo "Press F11 to toggle full screen, ESC to exit"
    else
        echo "Okular/Chrome not found. Opening with default PDF viewer..."
        xdg-open "$output_file" &>/dev/null &
    fi
}

function op_create_presentation()
{
    if [[ ($# -ne 0) ]]; then
        echo "No parameters should be given" >&2
        return 2
    fi

    local input_file="docs/presentation_with_images.md"
    local output_file="docs/presentation.pdf"

    # Check if cached presentation_with_images.md exists
    if [[ ! -f "$input_file" ]]; then
        echo "ERROR: Cached file '$input_file' not found" >&2
        echo "Run 'op_create_presentation_full' first to render diagrams" >&2
        return 1
    fi

    # Check if marp-cli is installed
    if ! command -v marp &> /dev/null; then
        echo "Installing marp-cli..." >&2
        npm install -g @marp-team/marp-cli
        if [[ $? -ne 0 ]]; then
            echo "ERROR: Failed to install marp-cli" >&2
            echo "You can try installing it manually with: npm install -g @marp-team/marp-cli" >&2
            return 1
        fi
    fi

    # Use cached presentation_with_images.md (no rendering)
    echo "Using cached presentation (no re-rendering)..."
    marp "$input_file" \
        --pdf \
        --allow-local-files \
        --theme presentation \
        --theme-set docs/presentation.css \
        --output "$output_file"

    if [[ $? -eq 0 ]]; then
        echo "Successfully generated: $output_file"
        _op_open_presentation_pdf "$output_file"
        return 0
    else
        echo "ERROR: Failed to generate presentation PDF" >&2
        return 1
    fi
}

function op_create_presentation_full()
{
    if [[ ($# -ne 0) ]]; then
        echo "No parameters should be given" >&2
        return 2
    fi

    local input_file="docs/presentation.md"
    local output_file="docs/presentation.pdf"

    if [[ ! -f "$input_file" ]]; then
        echo "ERROR: Input file '$input_file' not found" >&2
        return 1
    fi

    # Check if marp-cli is installed
    if ! command -v marp &> /dev/null; then
        echo "Installing marp-cli..." >&2
        npm install -g @marp-team/marp-cli
        if [[ $? -ne 0 ]]; then
            echo "ERROR: Failed to install marp-cli" >&2
            echo "You can try installing it manually with: npm install -g @marp-team/marp-cli" >&2
            return 1
        fi
    fi

    if ! command -v node &> /dev/null; then
        echo "ERROR: Node.js is required for Mermaid rendering" >&2
        return 1
    fi

    # Always render all diagrams (ignore git cache)
    echo "Rendering all mermaid diagrams (full render)..."
    node src/op/docs_create/render_mermaid.js --force-full

    if [[ $? -ne 0 ]]; then
        echo "ERROR: Failed to render Mermaid diagrams" >&2
        echo "Falling back to PDF without Mermaid diagrams..." >&2
        marp "$input_file" --pdf --allow-local-files --theme presentation --theme-set docs/presentation.css --output "$output_file"
    else
        # Generate PDF from the file with rendered images
        marp "docs/presentation_with_images.md" \
            --pdf \
            --allow-local-files \
            --theme presentation \
            --theme-set docs/presentation.css \
            --output "$output_file"

        if [[ $? -eq 0 ]]; then
            echo "Successfully generated: $output_file"
            _op_open_presentation_pdf "$output_file"

            echo ""
            uv run python src/op/docs_create/check_presentation_overflow.py "$input_file"

            return 0
        else
            echo "ERROR: Failed to generate presentation PDF" >&2
            return 1
        fi
    fi
}
##########################################################################################


##########################################################################################
function op_claude_linux_update()
{
    rm -rf /home/uriel/.npm-global/lib/node_modules/@anthropic-ai/claude-code
    npm i -g @anthropic-ai/claude-code
}
##########################################################################################