
name: NW-111 Market Pulse

on:
  workflow_dispatch:
    inputs:
      mode:
        description: "Market Pulse update mode"
        required: true
        default: "live"
        type: choice
        options:
          - live
          - close

permissions:
  contents: write

concurrency:
  group: nw111-market-pulse
  cancel-in-progress: false

jobs:
  update-market-pulse:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          ref: main
          persist-credentials: true

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Run Market Pulse
        env:
          EODHD_TOKEN: ${{ secrets.EODHD_TOKEN }}
          MARKET_PULSE_MODE: ${{ inputs.mode }}
        run: |
          echo "Market Pulse mode: $MARKET_PULSE_MODE"
          python market_pulse.py

      - name: Commit updated Market Pulse JSON
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          git add market_pulse.json

          if git diff --cached --quiet; then
            echo "No Market Pulse changes"
            exit 0
          fi

          git commit -m "Update Market Pulse (${{ inputs.mode }})"

          git pull --rebase origin main
          git push origin HEAD:main
