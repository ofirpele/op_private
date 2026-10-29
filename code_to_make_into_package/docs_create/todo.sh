function _py_open_presentation_pdf()
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

function py_create_presentation()
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
        echo "Run 'py_create_presentation_full' first to render diagrams" >&2
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
        _py_open_presentation_pdf "$output_file"
        return 0
    else
        echo "ERROR: Failed to generate presentation PDF" >&2
        return 1
    fi
}

function py_create_presentation_full()
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
            _py_open_presentation_pdf "$output_file"

            echo ""
            uv run python src/op/docs_create/check_presentation_overflow.py "$input_file"

            return 0
        else
            echo "ERROR: Failed to generate presentation PDF" >&2
            return 1
        fi
    fi
}
